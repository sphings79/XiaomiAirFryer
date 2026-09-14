"""Shared base for the air fryer's controls."""
# pylint: disable=import-error
import logging

from miio import DeviceException

from homeassistant.const import CONF_MAC, CONF_MODEL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class XiaomiAirFryerControl(CoordinatorEntity):
    """A control that writes back to the fryer.

    Unlike the sensors these stay available even when the appliance is
    unplugged, which it is most of the time. They keep showing the last known
    setting, and a write that cannot reach the device reports an error rather
    than failing silently -- an unavailable row of controls is noise in a
    dashboard when the device being off is the normal state.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        """Initialize the control."""
        super().__init__(coordinator)
        self._device = coordinator.device
        self._host = coordinator.host
        self._model = entry.options.get(CONF_MODEL)
        self._mac = entry.options.get(CONF_MAC)
        self._device_id = entry.unique_id
        self._device_name = entry.title

        self._attr_translation_key = key
        self._attr_unique_id = f"{DOMAIN}.{entry.unique_id}-{key}"

    @property
    def available(self) -> bool:
        """Controls stay usable so the last setting remains visible."""
        return True

    @property
    def device_info(self):
        """Return the device info."""
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": (self._model or "Xiaomi").split(".", 1)[0].capitalize(),
            "name": self._device_name,
            "model": self._model,
            "sw_version": self.coordinator.firmware_version,
        }

        if self._mac is not None:
            info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac)}

        return info

    def _status_value(self, attribute, default=None):
        """Read one attribute off the last poll, if there was one."""
        state = self.coordinator.data
        if state is None:
            return default
        return getattr(state, attribute, default)

    async def _async_write(self, method, *args):
        """Send a value to the device and refresh once it lands."""
        try:
            await self.hass.async_add_executor_job(method, *args)
        except DeviceException as ex:
            raise HomeAssistantError(
                f"Could not reach the air fryer at {self._host}: {ex}"
            ) from ex

        await self.coordinator.async_request_refresh()
