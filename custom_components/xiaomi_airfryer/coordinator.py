"""Data update coordinator for the Xiaomi AirFryer component."""
# pylint: disable=import-error
import logging
from datetime import timedelta

from miio import DeviceException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DATA_KEY,
    DATA_STATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class XiaomiAirFryerCoordinator(DataUpdateCoordinator):
    """Poll the air fryer once per interval and share the result.

    Previously every entity polled on its own: the switch talked to the device
    and stashed the result in hass.data, while the sensors only read that copy
    and had no availability of their own. A failed poll therefore left stale
    values on display instead of marking the entities unavailable.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        device,
        host: str,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.device = device
        self.host = host

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Fetch the current state from the device."""
        try:
            state = await self.hass.async_add_executor_job(self.device.status)
        except DeviceException as ex:
            raise UpdateFailed(f"Could not reach the air fryer at {self.host}: {ex}") from ex
        except OSError as ex:
            # miio raises DeviceException for most failures, but a socket that
            # goes away mid-request can surface as a plain OSError.
            raise UpdateFailed(f"Network error talking to {self.host}: {ex}") from ex

        if state is None:
            raise UpdateFailed(f"The air fryer at {self.host} returned no state")

        # Mirror the state into hass.data so the service handlers keep working.
        self.hass.data.setdefault(DATA_KEY, {}).setdefault(self.host, {})
        self.hass.data[DATA_KEY][self.host][DATA_STATE] = state

        return state
