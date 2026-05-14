"""The APS Usage integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import APSAuthError, APSUsageAPI
from .const import CONF_ACCOUNT_ID, DAYS_OF_HISTORY, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up APS Usage from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    account_id: str = entry.data[CONF_ACCOUNT_ID]

    session = async_get_clientsession(hass)
    api = APSUsageAPI(session, username, password)

    coordinator = APSUsageDataUpdateCoordinator(hass, api=api, account_id=account_id)

    # Perform initial data refresh (raises ConfigEntryNotReady on failure)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload APS Usage config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


class APSUsageDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch APS usage data on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: APSUsageAPI,
        account_id: str,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.account_id = account_id

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from the APS API.

        Returns a dict with the raw API response, which sensor.py will parse.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DAYS_OF_HISTORY)

        start_str = start_date.strftime("%m/%d/%Y")
        end_str = end_date.strftime("%m/%d/%Y")

        _LOGGER.debug(
            "APS: Fetching usage for account %s from %s to %s",
            self.account_id,
            start_str,
            end_str,
        )

        try:
            return await self.api.get_usage_data(
                account_id=self.account_id,
                start_date=start_str,
                end_date=end_str,
            )
        except APSAuthError as err:
            raise UpdateFailed(f"APS authentication error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"APS connection error: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"APS unexpected error: {err}") from err
