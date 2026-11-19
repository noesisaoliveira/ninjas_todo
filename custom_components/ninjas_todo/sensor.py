from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRAND_LABELS, DOMAIN
from .coordinator import SupermarketCoordinator, distance_meters

QUERY_RADIUS_METERS = 1000


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: SupermarketCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Query1KmNowSensor(coordinator, entry)])


class Query1KmNowSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Query 1Km Now"
    _attr_icon = "mdi:map-search"

    def __init__(self, coordinator: SupermarketCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_query_1km_now"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Ninjas ToDo",
            "manufacturer": "Ninjas ToDo",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.coordinator.tracker_entity],
                self._handle_tracker_change,
            )
        )

    @callback
    def _handle_tracker_change(self, event: Event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | None:
        locations = self._nearby_locations()
        return None if locations is None else len(locations)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "radius_m": QUERY_RADIUS_METERS,
            "tracker_entity": self.coordinator.tracker_entity,
            "locations": self._nearby_locations() or [],
        }

    def _nearby_locations(self) -> list[dict[str, Any]] | None:
        state = self.hass.states.get(self.coordinator.tracker_entity)
        if state is None:
            return None

        try:
            latitude = float(state.attributes["latitude"])
            longitude = float(state.attributes["longitude"])
        except (KeyError, TypeError, ValueError):
            return None

        nearby = []
        for location in self.coordinator.locations:
            distance = distance_meters(
                latitude,
                longitude,
                location["latitude"],
                location["longitude"],
            )
            if distance <= QUERY_RADIUS_METERS:
                nearby.append(
                    {
                        "name": location["name"],
                        "brand": BRAND_LABELS.get(location["brand"], location["brand"]),
                        "distance_m": round(distance),
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                    }
                )

        return sorted(nearby, key=lambda location: location["distance_m"])