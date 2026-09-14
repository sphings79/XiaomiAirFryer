"""Selectable settings of the Xiaomi AirFryer."""
# pylint: disable=import-error
import logging

from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .entity import XiaomiAirFryerControl
from .fryer_miot import FoodQuanty, RECIPE_SLOTS, slugify_state

_LOGGER = logging.getLogger(__name__)

# Food quantity is an enum on the device; Unknown is a read-only fallback and
# is deliberately not offered as something to pick.
FOOD_QUANTY_MEMBERS = ["Null", "Single", "Double", "Half", "Full"]
FOOD_QUANTY_CHOICES = [slugify_state(m) for m in FOOD_QUANTY_MEMBERS]
_BY_CHOICE = dict(zip(FOOD_QUANTY_CHOICES, FOOD_QUANTY_MEMBERS))


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the selects this model supports."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    mapping = getattr(coordinator.device, "mapping", {}) or {}
    model = coordinator.device._model  # noqa: SLF001 - the device exposes no getter

    entities = []

    if "food_quanty" in mapping:
        entities.append(XiaomiAirFryerFoodQuanty(coordinator, entry))

    # Only worth offering when the slots are known; otherwise there is nothing
    # readable to choose between.
    if "recipe_id" in mapping and RECIPE_SLOTS.get(model):
        entities.append(XiaomiAirFryerRecipe(coordinator, entry, model))

    async_add_entities(entities)


class XiaomiAirFryerFoodQuanty(XiaomiAirFryerControl, SelectEntity):
    """How much food is in the basket."""

    _attr_options = FOOD_QUANTY_CHOICES

    def __init__(self, coordinator, entry):
        """Initialize the select."""
        super().__init__(coordinator, entry, "food_quanty")

    @property
    def current_option(self):
        """Return the quantity the fryer last reported."""
        value = self._status_value("food_quanty")
        name = getattr(value, "name", None)
        choice = slugify_state(name) if name else None
        return choice if choice in FOOD_QUANTY_CHOICES else None

    async def async_select_option(self, option: str) -> None:
        """Send a new quantity to the fryer."""
        await self._async_write(
            self._device.food_quanty, FoodQuanty[_BY_CHOICE[option]].value
        )


class XiaomiAirFryerRecipe(XiaomiAirFryerControl, SelectEntity):
    """Which of the built-in recipes is selected."""

    def __init__(self, coordinator, entry, model):
        """Initialize the select."""
        super().__init__(coordinator, entry, "recipe_id")
        self._slots = RECIPE_SLOTS[model]
        # name -> slot, so picking a name writes the slot the device expects
        self._by_name = {name: slot for slot, name in self._slots.items()}
        self._attr_options = sorted(self._by_name)

    @property
    def current_option(self):
        """Return the recipe the fryer last reported."""
        value = self._status_value("recipe_id")
        return value if value in self._by_name else None

    async def async_select_option(self, option: str) -> None:
        """Send a new recipe to the fryer."""
        await self._async_write(self._device.recipe_id, self._by_name[option])
