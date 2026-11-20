from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import DEFAULT_DETECTION_RADIUS_METERS, DOMAIN, PLATFORMS
from .coordinator import SupermarketCoordinator

_LOGGER = logging.getLogger(__name__)


def _entry_value(entry: ConfigEntry, key: str):
    return entry.options.get(key, entry.data[key])


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SupermarketCoordinator(
        hass,
        entry,
        tracker_entity=_entry_value(entry, "tracker_entity"),
        notify_service=_entry_value(entry, "notify_service"),
        brands=_entry_value(entry, "brands"),
        detection_radius_m=entry.options.get(
            "detection_radius_m",
            entry.data.get("detection_radius_m", DEFAULT_DETECTION_RADIUS_METERS),
        ),
    )
    await coordinator.async_load()
    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def handle_tracker_change(event: Event) -> None:
        await coordinator.async_check_location(notify=True)

    unsubscribe = async_track_state_change_event(
        hass, [_entry_value(entry, "tracker_entity")], handle_tracker_change
    )
    entry.async_on_unload(unsubscribe)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await coordinator.async_check_location(notify=False)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
