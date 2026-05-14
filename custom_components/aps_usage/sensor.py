"""Sensor platform for APS Usage — kWh and billing sensors."""

from __future__ import annotations

from datetime import datetime
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

from . import APSDataCoordinator
from .api import APSUsageData
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up APS Usage sensors."""
    coordinator: APSDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            APSYesterdayKwhSensor(coordinator, entry),
            APSCurrentCycleKwhSensor(coordinator, entry),
            APSThirtyDayKwhSensor(coordinator, entry),
            APSOnPeakYesterdaySensor(coordinator, entry),
            APSOffPeakYesterdaySensor(coordinator, entry),
            APSBalanceSensor(coordinator, entry),
            APSDueDateSensor(coordinator, entry),
            APSLastPaymentSensor(coordinator, entry),
        ],
        update_before_add=True,
    )


class _APSBase(CoordinatorEntity, SensorEntity):
    """Base class for APS sensors."""

    def __init__(
        self, coordinator: APSDataCoordinator, entry: ConfigEntry, key: str
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def _usage(self) -> APSUsageData | None:
        if self.coordinator.data:
            return self.coordinator.data.get("usage")
        return None

    @property
    def _financial(self) -> dict:
        if self.coordinator.data:
            return self.coordinator.data.get("financial", {})
        return {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fin = self._financial
        usage = self._usage
        attrs: dict[str, Any] = {
            "account_id": fin.get("account_id", ""),
            "premise_address": fin.get("premise_address", ""),
        }
        if usage:
            attrs["latest_data_date"] = usage.latest_date
            attrs["bill_cycle_start"] = usage.current_bill_cycle_start
        return attrs


class APSYesterdayKwhSensor(_APSBase):
    """Yesterday's total energy usage in kWh."""

    _attr_name = "APS Yesterday kWh"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "yesterday_kwh")

    @property
    def native_value(self) -> float | None:
        usage = self._usage
        return usage.yesterday_kwh if usage else None


class APSCurrentCycleKwhSensor(_APSBase):
    """Total energy usage since the current billing cycle started."""

    _attr_name = "APS Current Billing Cycle kWh"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:home-lightning-bolt"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current_cycle_kwh")

    @property
    def native_value(self) -> float | None:
        usage = self._usage
        return usage.current_cycle_kwh if usage else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        attrs["rate_plan"] = self._financial.get("rate_plan")
        return attrs


class APSThirtyDayKwhSensor(_APSBase):
    """Total energy usage over the last 30 days."""

    _attr_name = "APS 30-Day kWh"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-month"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "thirty_day_kwh")

    @property
    def native_value(self) -> float | None:
        usage = self._usage
        return usage.period_kwh(30) if usage else None


class APSOnPeakYesterdaySensor(_APSBase):
    """Yesterday's on-peak energy usage."""

    _attr_name = "APS Yesterday On-Peak kWh"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt-circle"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "on_peak_yesterday")

    @property
    def native_value(self) -> float | None:
        usage = self._usage
        return usage.on_peak_kwh_yesterday if usage else None


class APSOffPeakYesterdaySensor(_APSBase):
    """Yesterday's off-peak energy usage."""

    _attr_name = "APS Yesterday Off-Peak kWh"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt-outline"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "off_peak_yesterday")

    @property
    def native_value(self) -> float | None:
        usage = self._usage
        return usage.off_peak_kwh_yesterday if usage else None


class APSBalanceSensor(_APSBase):
    """Current outstanding bill balance."""

    _attr_name = "APS Current Balance"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-usd"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "balance")

    @property
    def native_value(self) -> float | None:
        val = self._financial.get("outstanding_balance")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fin = self._financial
        return {
            "account_id": fin.get("account_id", ""),
            "due_date": fin.get("due_date", ""),
            "new_charges": fin.get("new_charges"),
            "auto_pay": fin.get("auto_pay"),
            "budget_billing": fin.get("budget_billing"),
            "last_payment_amount": fin.get("last_payment_amount"),
            "last_payment_date": fin.get("last_payment_date"),
        }


class APSDueDateSensor(_APSBase):
    """Bill due date."""

    _attr_name = "APS Bill Due Date"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "due_date")

    @property
    def native_value(self):  # type: ignore[override]
        """Return due date as a date object."""
        val = self._financial.get("due_date", "")
        if not val:
            return None
        for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%y"):
            try:
                return datetime.strptime(val, fmt).date()  # noqa: DTZ007
            except ValueError:
                continue
        return None


class APSLastPaymentSensor(_APSBase):
    """Most recent payment amount."""

    _attr_name = "APS Last Payment"
    _attr_native_unit_of_measurement = "USD"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:check-circle"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: APSDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_payment")

    @property
    def native_value(self) -> float | None:
        val = self._financial.get("last_payment_amount")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_payment_date": self._financial.get("last_payment_date"),
            "account_id": self._financial.get("account_id", ""),
        }
