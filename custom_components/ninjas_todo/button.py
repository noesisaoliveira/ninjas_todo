from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .coordinator import SupermarketCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: SupermarketCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ClearLocationCacheButton(coordinator, entry),
            RefreshLocationsButton(coordinator, entry),
        ]
    )


class _ControlButton(CoordinatorEntity, ButtonEntity):
    @property
    def available(self) -> bool:
        return True


class ClearLocationCacheButton(_ControlButton):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Clear location cache"
    _attr_icon = "mdi:delete-sweep"

    def __init__(self, coordinator: SupermarketCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_clear_location_cache"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Ninjas ToDo",
            "manufacturer": "Ninjas ToDo",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_clear_locations()


class RefreshLocationsButton(_ControlButton):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Refresh supermarket locations"
    _attr_icon = "mdi:map-marker-refresh"

    def __init__(self, coordinator: SupermarketCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh_locations"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Ninjas ToDo",
            "manufacturer": "Ninjas ToDo",
        }

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
        await self.coordinator.async_check_location(notify=True)
