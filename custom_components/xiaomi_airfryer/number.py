"""Numeric settings of the Xiaomi AirFryer."""
# pylint: disable=import-error
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature, UnitOfTime

from .const import DOMAIN
from .entity import XiaomiAirFryerControl

_LOGGER = logging.getLogger(__name__)

# key: (mapping property, device method, unit, min, max, step)
NUMBERS = {
    "target_time": ("target_time", "target_time", UnitOfTime.MINUTES, 1, 1440, 1),
    "target_temperature": (
        "target_temperature", "target_temperature", UnitOfTemperature.CELSIUS, 40, 200, 1,
    ),
    "appoint_time": ("appoint_time", "appoint_time", UnitOfTime.MINUTES, 0, 1440, 1),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the numeric settings this model supports."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mapping = getattr(coordinator.device, "mapping", {}) or {}

    async_add_entities(
        XiaomiAirFryerNumber(coordinator, entry, key, spec)
        for key, spec in NUMBERS.items()
        if spec[0] in mapping
    )


class XiaomiAirFryerNumber(XiaomiAirFryerControl, NumberEntity):
    """A value that can be read back and written to the fryer."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry, key, spec):
        """Initialize the number."""
        super().__init__(coordinator, entry, key)
        self._attribute, method, unit, low, high, step = spec
        self._method_name = method
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = low
        self._attr_native_max_value = high
        self._attr_native_step = step

    @property
    def native_value(self):
        """Return the value the fryer last reported."""
        return self._status_value(self._attribute)

    async def async_set_native_value(self, value: float) -> None:
        """Send a new value to the fryer."""
        await self._async_write(getattr(self._device, self._method_name), int(value))
