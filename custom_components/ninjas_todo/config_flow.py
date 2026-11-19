from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import BRAND_LABELS, DOMAIN


def _notify_services(hass: HomeAssistant) -> list[dict[str, str]]:
    services = hass.services.async_services().get("notify", {})
    return [
        {"value": f"notify.{name}", "label": f"{name}"}
        for name in sorted(services)
        if name != "send_message"
    ]


def _schema(hass: HomeAssistant, defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    tracker_options = ["person", "device_tracker"]
    return vol.Schema(
        {
            vol.Required("tracker_entity", default=defaults.get("tracker_entity")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=tracker_options)
            ),
            vol.Required("notify_service", default=defaults.get("notify_service")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_notify_services(hass), mode=selector.SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Required("brands", default=defaults.get("brands", list(BRAND_LABELS))): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": key, "label": label}
                        for key, label in BRAND_LABELS.items()
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


class NinjasToDoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            if not _notify_services(self.hass):
                errors["base"] = "no_notify_services"
            elif not user_input["brands"]:
                errors["base"] = "no_brands"
            else:
                await self.async_set_unique_id(user_input["tracker_entity"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Ninjas ToDo", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_schema(self.hass, user_input), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return NinjasToDoOptionsFlow(config_entry)


class NinjasToDoOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            if user_input["brands"]:
                return self.async_create_entry(title="", data=user_input)
            return self.async_show_form(
                step_id="init", data_schema=_schema(self.hass, user_input), errors={"base": "no_brands"}
            )

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(self.hass, defaults))
