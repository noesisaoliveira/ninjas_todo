"""Exercise the notification methods without requiring a Home Assistant install."""

import ast
import asyncio
import logging
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


def load_notification_methods():
    source_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components/ninjas_todo/coordinator.py"
    )
    source = ast.parse(source_path.read_text(encoding="utf-8"))
    coordinator = next(
        node for node in source.body
        if isinstance(node, ast.ClassDef) and node.name == "SupermarketCoordinator"
    )
    method_names = {
        "async_check_location", "_async_check_location", "_async_send_shopping_list"
    }
    coordinator.body = [
        node for node in coordinator.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name in method_names
    ]
    coordinator.bases = []
    distance = next(
        node for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name == "distance_meters"
    )
    namespace = {
        "datetime": datetime,
        "timezone": timezone,
        "NOTIFICATION_COOLDOWN": timedelta(minutes=30),
        "TODO_ENTITY": "todo.shopping_list",
        "HomeAssistantError": RuntimeError,
        "_LOGGER": Mock(spec=logging.Logger),
    }
    exec(
        compile(ast.Module(body=[distance, coordinator], type_ignores=[]), str(source_path), "exec"),
        namespace,
    )
    return namespace["SupermarketCoordinator"]


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = load_notification_methods()()
        self.coordinator.tracker_entity = "person.test"
        self.coordinator.notify_service = "notify.mobile_app_test"
        self.coordinator.detection_radius_m = 120
        self.coordinator.locations = [
            {"id": "node/1", "latitude": 38.72, "longitude": -9.14}
        ]
        self.coordinator._inside = set()
        self.coordinator._pending = set()
        self.coordinator._notification_lock = asyncio.Lock()
        self.coordinator._last_notified = None
        self.state = SimpleNamespace(
            state="not_home", attributes={"latitude": 38.72, "longitude": -9.14}
        )
        self.items = {"todo.shopping_list": {"items": [{"summary": "Milk"}]}}
        self.services = SimpleNamespace(
            has_service=Mock(return_value=True),
            async_call=AsyncMock(side_effect=[self.items, None]),
        )
        self.coordinator.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity: self.state),
            services=self.services,
        )

    async def check(self):
        await self.coordinator.async_check_location(notify=True)

    async def test_success_not_repeated(self):
        await self.check()
        await self.check()
        self.assertEqual(self.services.async_call.await_count, 2)
        self.assertFalse(self.coordinator._pending)
        self.assertIsNotNone(self.coordinator._last_notified)

    async def test_list_failure_retried(self):
        self.services.async_call.side_effect = [RuntimeError("read failed"), self.items, None]
        await self.check()
        self.assertEqual(self.coordinator._pending, {"node/1"})
        await self.check()
        self.assertFalse(self.coordinator._pending)
        self.assertEqual(self.services.async_call.await_count, 3)

    async def test_notification_failure_retried(self):
        self.services.async_call.side_effect = [self.items, RuntimeError("send failed"), self.items, None]
        await self.check()
        self.assertIsNone(self.coordinator._last_notified)
        await self.check()
        self.assertFalse(self.coordinator._pending)
        self.assertEqual(self.services.async_call.await_count, 4)

    async def test_cooldown_retried_after_expiry(self):
        self.coordinator._last_notified = datetime.now(timezone.utc)
        await self.check()
        self.services.async_call.assert_not_awaited()
        self.assertEqual(self.coordinator._pending, {"node/1"})
        self.coordinator._last_notified -= timedelta(minutes=31)
        await self.check()
        self.assertFalse(self.coordinator._pending)

    async def test_empty_list_retried_when_items_added(self):
        self.services.async_call.side_effect = [{"todo.shopping_list": {"items": []}}, self.items, None]
        await self.check()
        await self.check()
        self.assertFalse(self.coordinator._pending)
        self.assertEqual(self.services.async_call.await_count, 3)

    async def test_missing_service_retried(self):
        self.services.has_service.return_value = False
        await self.check()
        self.services.async_call.assert_not_awaited()
        self.services.has_service.return_value = True
        await self.check()
        self.assertFalse(self.coordinator._pending)

    async def test_leaving_cancels_pending_reminder(self):
        self.services.has_service.return_value = False
        await self.check()
        self.state.attributes["latitude"] = 39.0
        await self.check()
        self.assertFalse(self.coordinator._pending)
        self.assertFalse(self.coordinator._inside)

    async def test_missing_gps_does_not_create_reentry(self):
        await self.check()
        self.state.attributes = {}
        await self.check()
        self.state.attributes = {"latitude": 38.72, "longitude": -9.14}
        self.coordinator._last_notified -= timedelta(minutes=31)
        await self.check()
        self.assertEqual(self.services.async_call.await_count, 2)

    async def test_unavailable_tracker_does_not_send(self):
        self.state.state = "unavailable"
        await self.check()
        self.services.async_call.assert_not_awaited()

    async def test_startup_inside_leaves_reminder_pending(self):
        await self.coordinator.async_check_location(notify=False)
        self.services.async_call.assert_not_awaited()
        await self.check()
        self.assertEqual(self.services.async_call.await_count, 2)

    async def test_concurrent_checks_send_once(self):
        await asyncio.gather(self.check(), self.check(), self.check())
        self.assertEqual(self.services.async_call.await_count, 2)


class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_registers_rechecks_and_unload_cleanup(self):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "custom_components/ninjas_todo/__init__.py"
        )
        source = ast.parse(source_path.read_text(encoding="utf-8"))
        functions = [
            node for node in source.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in {"_entry_value", "async_setup_entry"}
        ]
        coordinator = SimpleNamespace(
            async_load=AsyncMock(),
            async_refresh=AsyncMock(),
            async_check_location=AsyncMock(),
        )
        state_subscription = Mock(return_value=Mock())
        timer_subscription = Mock(return_value=Mock())
        namespace = {
            "ConfigEntry": SimpleNamespace,
            "HomeAssistant": SimpleNamespace,
            "Event": SimpleNamespace,
            "datetime": datetime,
            "DOMAIN": "ninjas_todo",
            "PLATFORMS": ["button", "sensor"],
            "TODO_ENTITY": "todo.shopping_list",
            "DEFAULT_DETECTION_RADIUS_METERS": 120,
            "LOCATION_CHECK_INTERVAL": timedelta(minutes=1),
            "SupermarketCoordinator": Mock(return_value=coordinator),
            "async_track_state_change_event": state_subscription,
            "async_track_time_interval": timer_subscription,
            "async_reload_entry": AsyncMock(),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_path), "exec"), namespace)
        entry = SimpleNamespace(
            entry_id="test", options={},
            data={"tracker_entity": "person.test", "notify_service": "notify.mobile_app_test", "brands": ["lidl"]},
            async_on_unload=Mock(), add_update_listener=Mock(return_value=Mock()),
        )
        hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        self.assertTrue(await namespace["async_setup_entry"](hass, entry))
        self.assertEqual(state_subscription.call_args.args[1], ["person.test", "todo.shopping_list"])
        self.assertEqual(timer_subscription.call_args.args[2], timedelta(minutes=1))
        entry.async_on_unload.assert_any_call(state_subscription.return_value)
        entry.async_on_unload.assert_any_call(timer_subscription.return_value)
        coordinator.async_check_location.assert_awaited_once_with(notify=False)
        await timer_subscription.call_args.args[1](datetime.now(timezone.utc))
        await state_subscription.call_args.args[2](SimpleNamespace())
        self.assertEqual(coordinator.async_check_location.await_count, 3)
        coordinator.async_check_location.assert_awaited_with(notify=True)


if __name__ == "__main__":
    unittest.main()