"""Sensors of the Xiaomi AirFryer component."""
# pylint: disable=import-error
import logging
from enum import Enum

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_MAC,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from miio import DeviceException

from .fryer_miot import RECIPE_SLOTS, slugify_state

from .const import (
    CONF_MODEL,
    DOMAIN,
    MODEL_FRYER_YBAF01,
    MODEL_FRYER_MAF10A,
    MODELS_CARELI,
    MODELS_MIOT,
    MODELS_SILEN,
    MODELS_VIOMI,
    MODELS_XIAOMI, MODEL_FRYER_MAF07C, MODEL_FRYER_MAF09A, MODEL_FRYER_MAF65,
    MODEL_FRYER_ST701O
)

_LOGGER = logging.getLogger(__name__)

# Home Assistant only translates a sensor's state when the sensor declares
# the enum device class together with every value it can report, so these
# lists are the union across the models that share a sensor. A value that is
# missing here would raise, which is why recipe_id is handled separately: its
# values depend on the model's recipe slots and fall back to the raw slot.
SENSOR_OPTIONS = {
    "status": [
        "Unknown", "Shutdown", "Standby", "Pause", "Appointment", "Cooking",
        "Preheat", "Cooked", "PreheatFinish", "PreheatPause", "Pause2",
        "Keepwarm", "KeepwarmPause", "KeepwarmFinish", "CrispyRoast",
        "Degrease", "Delay", "PotPause",
        # the steam combi models add water-related states
        "WaterShortagePause", "WaterShortTimeout", "WaterShortPaused",
        "StandbyNetworking",
    ],
    "mode": [
        "Manual", "FrenchFries", "ChickenWing", "Steak", "LambChops", "Fish",
        "Shrimp", "Vegetables", "Cake", "Pizza", "Defrost", "DriedFruit",
        "Yogurt",
        # programmes of the steam combi models
        "NONE", "AirFryCustom", "AirFryFrozenFries", "AirFryPotato",
        "AirFryChickenLeg", "AirFryBeefSteak", "AirFryFish", "AirFryVegetables",
        "SteamCustom", "SteamRootVegetables", "SteamBroccoli", "SteamCorn",
        "SteamSalmon", "SteamRice", "SteamEgg", "SteamFryChickenLeg",
        "SteamFryFish", "SteamFryVegetables", "SteamFryPotato",
        "SteamFryDumplings", "SteamFryBread", "BakeCustom", "BakeCake",
        "BakePizza", "BakeBread", "SousVideCustom", "SousVideBeefSteak",
        "SousVideChickenSteak", "SousVideSalmon", "SousVideEgg", "Roast",
        "AirDry", "Ferment", "CareDry", "CareWaterCleaning", "CareDeodorize",
    ],
    "food_quanty": ["Unknown", "Null", "Single", "Double", "Half", "Full"],
    "turn_pot": [
        "Unknown", "NotTurnPot", "SwitchOff", "TurnPot",
        "NoNeedTurnOverPot", "NeedTurnOverPot",
    ],
    "turn_pot_status": ["Unknown", "NoNeedTurnOverPot", "NeedTurnOverPot"],
    "preheat_switch": ["Unknown", "Null", "Off", "On"],
    "texture": [
        "Unknown", "NONE", "CrispyRoast", "TenderRoast", "Degrease",
        # the steam combi models report which heat source is running
        "AirFryer", "SteamFrying", "Steam",
    ],
}


SENSOR_TYPES_MAF = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "target_time": ["Target Time", None, "target_time", UnitOfTime.MINUTES, "mdi:menu", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None,SensorDeviceClass.TEMPERATURE],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "recipe_id": ["Recipe Id", None, "recipe_id", None, "mdi:rice", None],
    "recipe_name": ["Recipe Name", None, "recipe_name", None, "mdi:chef-hat", None],
    "appoint_time": ["Appoint Time", None, "appoint_time", UnitOfTime.MINUTES, "mdi:timelapse", None],
    "food_quanty": ["Food Quanty", None, "food_quanty", None, "mdi:flash-outline", None],
    "preheat_switch": ["Preheat Phase", None, "preheat_switch", None, "mdi:pot-steam-outline", None],
    "appoint_time_left": ["Appoint Time Left", None, "appoint_time_left", UnitOfTime.MINUTES, "mdi:timer", None],
    "turn_pot": ["Turn Pot", None, "turn_pot", None, "mdi:rotate-3d-variant", None],
    "turn_pot_config": ["Turn Pot Config", None, "turn_pot_config", None, "mdi:rotate-3d-variant", None]
}

SENSOR_TYPES_YBAF = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "target_time": ["Target Time", None, "target_time", None, "mdi:menu", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "mode": ["Recipe Id", None, "mode", None, "mdi:stairs", None]
}

SENSOR_TYPES_SCK = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "target_time": ["Target Time", None, "target_time", None, "mdi:menu", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "switch_status": ["Switch Status", None, "switch_status", None, "mdi:pot-steam-outline", None],
    "mode": ["Recipe Id", None, "mode", None, "mdi:stairs", None]
}

SENSOR_TYPES_MIOT = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "target_time": ["Target Time", None, "target_time", None, "mdi:menu", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "switch_status": ["Switch Status", None, "switch_status", None, "mdi:pot-steam-outline", None],
    "temperature": ["Temperature", None, "temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "preheat": ["Preheat Phase", None, "preheat", None, "mdi:pot-steam-outline", None],
    "recipe_command": ["Recipe Command", None, "recipe_command", None, "mdi:rice", None],
    "target_cooking_measure": ["Target Cooking Measure", None, "target_cooking_measure", None, "mdi:scale", None],
    "mode": ["Recipe Id", None, "mode", None, "mdi:stairs", None],
}

SENSOR_TYPES_VIOMI = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "target_time": ["Target Time", None, "target_time", None, "mdi:menu", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "recipe_id": ["Recipe Id", None, "recipe_id", None, "mdi:rice", None],
    "recipe_name": ["Recipe Name", None, "recipe_name", None, "mdi:chef-hat", None],
    "turn_pot_status": ["Turn Pot Status", None, "turn_pot_status", None, "mdi:rotate-3d-variant", None],
}

SENSOR_TYPES_XIAOMI = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "mode": ["Mode", None, "mode", None, "mdi:stairs", None],
    "target_time": ["Target Time", None, "target_time", UnitOfTime.MINUTES, "mdi:menu", None],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None,SensorDeviceClass.TEMPERATURE],
    "recipe_id": ["Recipe Id", None, "recipe_id", None, "mdi:rice", None],
    "recipe_name": ["Recipe Name", None, "recipe_name", None, "mdi:chef-hat", None],
    "turn_pot": ["Turn Pot", None, "turn_pot", None, "mdi:rotate-3d-variant", None],
}

SENSOR_TYPES_ST701O = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "mode": ["Mode", None, "mode", None, "mdi:stairs", None],
    "target_time": ["Target Time", None, "target_time", UnitOfTime.MINUTES, "mdi:menu", None],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "recipe_id": ["Recipe Id", None, "recipe_id", None, "mdi:rice", None],
    "turn_pot": ["Turn Pot", None, "turn_pot", None, "mdi:rotate-3d-variant", None],
    "turn_pot_config": ["Turn Pot Config", None, "turn_pot_config", None, "mdi:rotate-3d-variant", None],
    "texture": ["Texture", None, "texture", None, "mdi:pot-steam", None],
    "reservation_left_time": ["Reservation Left Time", None, "reservation_left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "cooking_weight": ["Cooking Weight", None, "cooking_weight", None, "mdi:scale", None],
}

SENSOR_TYPES_MAF10A = {
    "status": ["Status", None, "status", None, "mdi:bowl", None],
    "mode": ["Mode", None, "mode", None, "mdi:stairs", None],
    "target_time": ["Target Time", None, "target_time", UnitOfTime.MINUTES, "mdi:menu", None],
    "left_time": ["Remaining", None, "left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "left_percent": ["Remaining Percent", None, "left_percent", PERCENTAGE, "mdi:timer-sand", None],
    "target_temperature": ["Target Temperature", None, "target_temperature", UnitOfTemperature.CELSIUS, None, SensorDeviceClass.TEMPERATURE],
    "recipe_id": ["Recipe Id", None, "recipe_id", None, "mdi:rice", None],
    "recipe_name": ["Recipe Name", None, "recipe_name", None, "mdi:chef-hat", None],
    "preheat": ["Preheat Phase", None, "preheat", None, "mdi:pot-steam-outline", None],
    "turn_pot": ["Turn Pot", None, "turn_pot", None, "mdi:rotate-3d-variant", None],
    "turn_pot_config": ["Turn Pot Config", None, "turn_pot_config", None, "mdi:rotate-3d-variant", None],
    "texture": ["Texture", None, "texture", None, "mdi:pot-steam", None],
    "reservation_left_time": ["Reservation Left Time", None, "reservation_left_time", UnitOfTime.MINUTES, "mdi:timer", None],
    "cooking_weight": ["Cooking Weight", None, "cooking_weight", None, "mdi:scale", None],
}

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import Mijia AirFryer configuration from YAML."""
    _LOGGER.warning(
        "Loading Mijia AirFryer via platform setup is deprecated;"
        " Please remove it from your configuration"
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )

async def async_setup_entry(hass, config, async_add_devices, discovery_info=None):
    """Set up the air fryer sensors from a config entry."""

    coordinator = hass.data[DOMAIN][config.entry_id]
    model = config.options.get(CONF_MODEL) or config.data.get(CONF_MODEL)

    if model is None:
        try:
            device_info = await hass.async_add_executor_job(coordinator.device.info)
            model = device_info.model
        except DeviceException as ex:
            raise PlatformNotReady from ex

    if model == MODEL_FRYER_ST701O:
        sensor_types = SENSOR_TYPES_ST701O
    elif model == MODEL_FRYER_YBAF01:
        sensor_types = SENSOR_TYPES_YBAF
    elif model in [MODEL_FRYER_MAF10A, MODEL_FRYER_MAF07C, MODEL_FRYER_MAF09A,
                   MODEL_FRYER_MAF65]:
        sensor_types = SENSOR_TYPES_MAF10A
    elif model in MODELS_CARELI:
        sensor_types = SENSOR_TYPES_MAF
    elif model in MODELS_SILEN:
        sensor_types = SENSOR_TYPES_SCK
    elif model in MODELS_MIOT:
        sensor_types = SENSOR_TYPES_MIOT
    elif model in MODELS_VIOMI:
        sensor_types = SENSOR_TYPES_VIOMI
    elif model in MODELS_XIAOMI:
        sensor_types = SENSOR_TYPES_XIAOMI
    else:
        _LOGGER.error(
            "Unsupported device found! Please create an issue at "
            "https://github.com/sphings79/XiaomiAirFryer/issues "
            "and provide the following data: %s",
            model,
        )
        return False

    async_add_devices(
        [
            XiaomiAirFryerSensor(coordinator, stype, config)
            for stype in sensor_types.values()
        ],
        update_before_add=False,
    )


class XiaomiAirFryerSensor(CoordinatorEntity, SensorEntity):
    """ Xiaomi AirFryer Sensor """

    _attr_has_entity_name = True

    def __init__(self, coordinator, config, entry):
        """Initialize sensor."""
        super().__init__(coordinator)
        self._host = coordinator.host
        self._model = entry.options.get(CONF_MODEL)
        self._mac = entry.options[CONF_MAC]
        self._device_id = entry.unique_id
        self._device_name = entry.title
        self._child = config[1]
        self._attr = config[2]
        self._attr_native_unit_of_measurement = config[3]
        self._attr_device_class = config[5]

        # The attribute name doubles as the translation key, so the display
        # name and the state values come from translations/*.json rather than
        # being hard-coded English. The unique_id still derives from the old
        # hard-coded label so existing entities keep their identity.
        self._attr_translation_key = config[2]
        self._attr_unique_id = "{}.{}-{}".format(
            DOMAIN, entry.unique_id, config[0].lower().replace(" ", "-"))

        options = SENSOR_OPTIONS.get(config[2])
        if options:
            options = [slugify_state(o) for o in options]
        if config[2] == "recipe_id":
            # Only the slots this model is known to have; without an entry the
            # sensor reports the raw slot and stays a plain string sensor.
            slots = RECIPE_SLOTS.get(self._model)
            options = sorted(set(slots.values()) | {"unknown"}) if slots else None
        if options:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = options

    @property
    def device_info(self):
        """Return the device info."""
        device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": (self._model or "Xiaomi").split(".", 1)[0].capitalize(),
            "name": self._device_name,
            "model": self._model,
            "sw_version": self.coordinator.firmware_version,
        }

        if self._mac is not None:
            device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac)}

        return device_info

    @property
    def extra_state_attributes(self):
        """Expose the raw slot behind a named recipe."""
        if self._attr != "recipe_id":
            return None
        state = self.coordinator.data
        slot = getattr(state, "recipe_slot", None) if state else None
        return {"slot": slot} if slot else None

    @property
    def native_value(self):
        """Return the state read from the last successful poll."""
        state = self.coordinator.data

        if state is None:
            return None

        if self._child is not None:
            state = getattr(state, self._child, None)
            if state is None:
                return None

        value = getattr(state, self._attr, None)

        if isinstance(value, Enum):
            return slugify_state(value.name)

        return value
