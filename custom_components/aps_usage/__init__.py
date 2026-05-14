"""The APS Usage integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import APSAuthError, APSUsageAPI, APSUsageData
from .const import DAYS_OF_HISTORY, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up APS Usage from a config entry."""
    session = async_get_clientsession(hass)
    api = APSUsageAPI(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    coordinator = APSDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload APS Usage."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


class APSDataCoordinator(DataUpdateCoordinator):
    """Coordinator fetching both usage and financial data on a schedule."""

    def __init__(self, hass: HomeAssistant, api: APSUsageAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict:
        """Fetch usage + financial data and return combined dict."""
        try:
            usage: APSUsageData = await self.api.get_daily_usage(DAYS_OF_HISTORY)
            financial: dict = await self.api.get_financial_data()
            # Attach rate plan from usage data
            if usage.series:
                financial["rate_plan"] = usage.series[-1].get("effRateSchedule")
            return {"usage": usage, "financial": financial}
        except APSAuthError as err:
            raise UpdateFailed(f"APS authentication error: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"APS connection error: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"APS unexpected error: {err}") from err
