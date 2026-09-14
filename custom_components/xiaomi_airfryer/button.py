"""One-shot actions of the Xiaomi AirFryer."""
# pylint: disable=import-error
import logging

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import XiaomiAirFryerControl

_LOGGER = logging.getLogger(__name__)

# key: the action in the model's mapping, and the method that triggers it
BUTTONS = {
    "pause": ("pause", "pause"),
    "resume": ("resume_cooking", "resume_cooking"),
    # dual basket models: each basket starts, pauses and stops on its own
    "upper_start": ("upper_start_cook", "upper_start_cook"),
    "upper_pause": ("upper_pause", "upper_pause"),
    "upper_resume": ("upper_resume_cooking", "upper_resume_cooking"),
    "upper_stop": ("upper_cancel_cooking", "upper_cancel_cooking"),
    "lower_start": ("lower_start_cook", "lower_start_cook"),
    "lower_pause": ("lower_pause", "lower_pause"),
    "lower_resume": ("lower_resume_cooking", "lower_resume_cooking"),
    "lower_stop": ("lower_cancel_cooking", "lower_cancel_cooking"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the buttons this model supports."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mapping = getattr(coordinator.device, "mapping", {}) or {}

    async_add_entities(
        XiaomiAirFryerButton(coordinator, entry, key, method)
        for key, (action, method) in BUTTONS.items()
        if action in mapping
    )


class XiaomiAirFryerButton(XiaomiAirFryerControl, ButtonEntity):
    """A button that triggers one action on the fryer."""

    def __init__(self, coordinator, entry, key, method):
        """Initialize the button."""
        super().__init__(coordinator, entry, key)
        self._method_name = method

    async def async_press(self) -> None:
        """Trigger the action."""
        await self._async_write(getattr(self._device, self._method_name))
