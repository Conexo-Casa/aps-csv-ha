"""Config flow for APS Usage integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import APSAuthError, APSUsageAPI
from .const import CONF_ACCOUNT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_ACCOUNT_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_ID): str,
    }
)


class APSUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for APS Usage."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username: str = ""
        self._password: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            api = APSUsageAPI(session, username, password)

            try:
                await api.authenticate()
            except APSAuthError as err:
                _LOGGER.warning("APS login failed: %s", err)
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError as err:
                _LOGGER.error("APS connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected APS error: %s", err)
                errors["base"] = "unknown"
                errors["_error_detail"] = str(err)
            else:
                # Credentials validated — move on to account ID step
                self._username = username
                self._password = password

                # Try to auto-detect account ID
                account_id = await api.get_account_id()
                if account_id:
                    return self.async_create_entry(
                        title=username,
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_ACCOUNT_ID: account_id,
                        },
                    )
                # If we can't auto-detect, ask the user
                return await self.async_step_account()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the account ID step (shown only if auto-detect fails)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title=self._username,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_ACCOUNT_ID: user_input[CONF_ACCOUNT_ID],
                },
            )

        return self.async_show_form(
            step_id="account",
            data_schema=STEP_ACCOUNT_DATA_SCHEMA,
            description_placeholders={
                "info": (
                    "Enter your APS Account ID. You can find this on your "
                    "bill or in the APS account dashboard URL."
                )
            },
            errors=errors,
        )
