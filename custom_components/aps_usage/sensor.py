"""Sensor platform for APS Usage."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import APSUsageDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up APS Usage sensor platform."""
    coordinator: APSUsageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            APSUsageSensor(coordinator, entry),
            APSDailyUsageSensor(coordinator, entry),
        ],
        update_before_add=True,
    )


def _extract_total_kwh(data: dict[str, Any]) -> float | None:
    """Extract total kWh from the APS API response.

    The APS mobi API returns a nested structure. We walk it defensively
    and return the most recent total consumption value in kWh.

    Known response path (based on reverse engineering):
    data
      -> getSimpleUsageDataResponse
        -> getSimpleUsageDataRes
          -> usageList (list)
            -> each item: {date, kwhUsage, cost, ...}
    """
    try:
        res = data.get("getSimpleUsageDataResponse", {}).get(
            "getSimpleUsageDataRes", {}
        )
        usage_list = res.get("usageList") or res.get("UsageList") or []
        if not usage_list:
            _LOGGER.debug("APS: usageList is empty in response")
            return None
        total = sum(
            float(item.get("kwhUsage") or item.get("KwhUsage") or 0)
            for item in usage_list
        )
        return round(total, 3)
    except (TypeError, ValueError, AttributeError) as err:
        _LOGGER.warning("APS: Failed to extract total kWh: %s", err)
        return None


def _extract_latest_daily_kwh(data: dict[str, Any]) -> float | None:
    """Extract the most recent single-day kWh from the APS API response."""
    try:
        res = data.get("getSimpleUsageDataResponse", {}).get(
            "getSimpleUsageDataRes", {}
        )
        usage_list = res.get("usageList") or res.get("UsageList") or []
        if not usage_list:
            return None
        # The list is ordered oldest-first; last item is most recent
        latest = usage_list[-1]
        kwh = latest.get("kwhUsage") or latest.get("KwhUsage")
        return round(float(kwh), 3) if kwh is not None else None
    except (TypeError, ValueError, AttributeError) as err:
        _LOGGER.warning("APS: Failed to extract daily kWh: %s", err)
        return None


class APSUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting total kWh used over the configured history window."""

    _attr_name = "APS Energy Usage (30 Days)"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self,
        coordinator: APSUsageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_total_kwh"

    @property
    def native_value(self) -> float | None:
        """Return total kWh for the history window."""
        if self.coordinator.data is None:
            return None
        return _extract_total_kwh(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes from the API response."""
        if not self.coordinator.data:
            return {}
        try:
            res = self.coordinator.data.get("getSimpleUsageDataResponse", {}).get(
                "getSimpleUsageDataRes", {}
            )
            usage_list = res.get("usageList") or res.get("UsageList") or []
            return {
                "account_id": self.coordinator.account_id,
                "data_points": len(usage_list),
            }
        except AttributeError:
            return {}


class APSDailyUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the most recent single day's kWh usage.

    This sensor is suitable for the Home Assistant Energy panel when
    configured with state_class=MEASUREMENT.
    """

    _attr_name = "APS Daily Energy Usage"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:home-lightning-bolt"

    def __init__(
        self,
        coordinator: APSUsageDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_daily_kwh"

    @property
    def native_value(self) -> float | None:
        """Return the most recent day's kWh usage."""
        if self.coordinator.data is None:
            return None
        return _extract_latest_daily_kwh(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return date of the most recent data point."""
        if not self.coordinator.data:
            return {}
        try:
            res = self.coordinator.data.get("getSimpleUsageDataResponse", {}).get(
                "getSimpleUsageDataRes", {}
            )
            usage_list = res.get("usageList") or res.get("UsageList") or []
            if usage_list:
                latest = usage_list[-1]
                return {
                    "date": latest.get("date") or latest.get("Date"),
                    "account_id": self.coordinator.account_id,
                }
        except AttributeError:
            pass
        return {}
