from __future__ import annotations

import asyncio
import logging
import unicodedata
from datetime import datetime, timezone
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BRAND_ALIASES,
    DOMAIN,
    LOCATION_REFRESH_INTERVAL,
    NOTIFICATION_COOLDOWN,
    OVERPASS_URL,
    TODO_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _location_brand(tags: dict[str, Any], selected_brands: set[str]) -> str | None:
    searchable = _normalize(
        " ".join(str(tags.get(key, "")) for key in ("brand", "name", "operator"))
    )
    for brand in selected_brands:
        aliases = BRAND_ALIASES.get(brand, ())
        if any(_normalize(alias) in searchable for alias in aliases):
            return brand
    return None


class SupermarketCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        tracker_entity: str,
        notify_service: str,
        brands: list[str],
        detection_radius_m: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=LOCATION_REFRESH_INTERVAL,
        )
        self.entry = entry
        self.tracker_entity = tracker_entity
        self.notify_service = notify_service
        self.brands = set(brands)
        self.detection_radius_m = int(detection_radius_m)
        self.store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_locations")
        self.hass = hass
        self.locations: list[dict[str, Any]] = []
        self._inside: set[str] = set()
        self._pending: set[str] = set()
        self._notification_lock = asyncio.Lock()
        self._last_notified: datetime | None = None

    async def async_load(self) -> None:
        stored = await self.store.async_load()
        if (
            isinstance(stored, dict)
            and stored.get("brands") == sorted(self.brands)
            and isinstance(stored.get("locations"), list)
        ):
            self.locations = stored["locations"]
            self.data = self.locations

    async def _async_update_data(self) -> list[dict[str, Any]]:
        query = (
            '[out:json][timeout:60];'
            'area["ISO3166-1"="PT"][admin_level=2]->.portugal;'
            'nwr["shop"~"^(supermarket|hypermarket|wholesale)$"](area.portugal);'
            "out center tags;"
        )
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                OVERPASS_URL,
                data={"data": query},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "NinjasToDo-HomeAssistant (+https://github.com/noesisaoliveira/ninjas_todo)",
                },
                timeout=aiohttp.ClientTimeout(total=90),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            if self.locations:
                _LOGGER.warning("Overpass lookup failed; using cached locations: %s", err)
                return self.locations
            raise UpdateFailed(f"Could not retrieve Portugal supermarket locations: {err}") from err

        locations = []
        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            brand = _location_brand(tags, self.brands)
            if brand is None:
                continue
            center = element.get("center", element)
            latitude = center.get("lat")
            longitude = center.get("lon")
            if latitude is None or longitude is None:
                continue
            locations.append(
                {
                    "id": f"{element.get('type')}/{element.get('id')}",
                    "brand": brand,
                    "name": tags.get("name", tags.get("brand", brand)),
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                }
            )

        self.locations = locations
        await self.store.async_save(
            {"brands": sorted(self.brands), "locations": locations}
        )
        _LOGGER.info("Loaded %s matching supermarket locations from OpenStreetMap", len(locations))
        return locations

    async def async_check_location(self, *, notify: bool) -> None:
        async with self._notification_lock:
            await self._async_check_location(notify=notify)

    async def _async_check_location(self, *, notify: bool) -> None:
        state = self.hass.states.get(self.tracker_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return
        latitude = state.attributes.get("latitude")
        longitude = state.attributes.get("longitude")
        if latitude is None or longitude is None:
            return
        current = {
            location["id"]
            for location in self.locations
            if distance_meters(
                float(latitude),
                float(longitude),
                location["latitude"],
                location["longitude"],
            )
            <= self.detection_radius_m
        }

        entered = current - self._inside
        self._inside = current
        self._pending.intersection_update(current)
        self._pending.update(entered)
        if notify and self._pending:
            _LOGGER.debug(
                "Checking pending reminder for %s supermarket radius/radii (%s m)",
                len(self._pending),
                self.detection_radius_m,
            )
            if await self._async_send_shopping_list():
                self._pending.clear()

    async def _async_send_shopping_list(self) -> bool:
        now = datetime.now(timezone.utc)
        if self._last_notified and now - self._last_notified < NOTIFICATION_COOLDOWN:
            _LOGGER.debug("Skipping shopping reminder because the cooldown is active")
            return False
        if not self.hass.services.has_service("todo", "get_items"):
            _LOGGER.warning("The todo.get_items service is unavailable")
            return False

        try:
            response = await self.hass.services.async_call(
                "todo",
                "get_items",
                {"entity_id": TODO_ENTITY, "status": "needs_action"},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError:
            _LOGGER.exception("Unable to read the Home Assistant shopping list")
            return False

        items = response.get(TODO_ENTITY, {}).get("items", []) if response else []
        summaries = [item.get("summary", "") for item in items if item.get("summary")]
        if not summaries:
            _LOGGER.info("No open shopping-list items; no reminder was sent")
            return False

        domain, service = self.notify_service.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": "You're at the supermarket",
                    "message": f"{len(summaries)} item(s): {', '.join(summaries)}",
                    "data": {
                        "tag": "shopping-list",
                        "group": "shopping",
                        "push": {"interruption-level": "time-sensitive"},
                    },
                },
                blocking=True,
            )
        except HomeAssistantError:
            _LOGGER.exception(
                "Unable to send shopping reminder through %s", self.notify_service
            )
            return False

        self._last_notified = now
        _LOGGER.info("Sent shopping reminder through %s", self.notify_service)
        return True

    async def async_send_test_notification(self) -> None:
        domain, service = self.notify_service.split(".", 1)
        await self.hass.services.async_call(
            domain,
            service,
            {
                "title": "Ninjas ToDo test",
                "message": "Your phone notification service is working.",
                "data": {"push": {"interruption-level": "time-sensitive"}},
            },
            blocking=True,
        )
        _LOGGER.info("Sent test notification through %s", self.notify_service)

    async def async_clear_locations(self) -> None:
        self.locations = []
        self._inside.clear()
        self._pending.clear()
        await self.store.async_remove()
        self.async_set_updated_data([])


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 6_371_000 * 2 * asin(sqrt(haversine))
