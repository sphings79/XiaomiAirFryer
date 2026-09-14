"""The Xiaomi AirFryer component."""
# pylint: disable=import-error
import logging

from homeassistant.const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import XiaomiAirFryerCoordinator
from .fryer_miot import (
    FryerMiot,
    FryerMiotSCK,
    FryerMiotMi,
    FryerMiotViomi,
    FryerMiotXiaomi,
)

from .const import (
    CONF_MODEL,
    DATA_KEY,
    DOMAIN,
    DOMAINS,
    DEFAULT_SCAN_INTERVAL,
    MODELS_CARELI,
    MODELS_SILEN,
    MODELS_MIOT,
    MODELS_VIOMI,
    MODELS_XIAOMI,
    MODELS_ALL_DEVICES
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, hass_config: dict):
    """Set up the Xiaomi AirFryer Component."""

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """ Update Optioins if available """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """ check unload integration """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, DOMAINS)

    if unload_ok:
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if coordinator is not None:
            hass.data[DOMAIN].pop(coordinator.host, None)
            hass.data.get(DATA_KEY, {}).pop(coordinator.host, None)

    return unload_ok


def _build_device(model, host, token):
    """Return the device class matching the model."""
    if model in MODELS_SILEN:
        return FryerMiotSCK(host, token, model=model)
    if model in MODELS_MIOT:
        return FryerMiotMi(host, token, model=model)
    if model in MODELS_VIOMI:
        return FryerMiotViomi(host, token, model=model)
    if model in MODELS_XIAOMI:
        return FryerMiotXiaomi(host, token, model=model)
    if model in MODELS_CARELI or model in MODELS_ALL_DEVICES:
        return FryerMiot(host, token, model=model)

    return FryerMiot(host, token, model=model)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Support Xiaomi AirFryer Component."""
    # migrate data (also after first setup) to options
    if entry.data:
        hass.config_entries.async_update_entry(entry, data={},
                                               options=entry.data)

    # add update handler
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    if entry.data.get(CONF_HOST, None):
        host = entry.data[CONF_HOST]
        token = entry.data[CONF_TOKEN]
        model = entry.data.get(CONF_MODEL)
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    else:
        host = entry.options[CONF_HOST]
        token = entry.options[CONF_TOKEN]
        model = entry.options.get(CONF_MODEL)
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hass.data.setdefault(DATA_KEY, {})
    hass.data[DATA_KEY].setdefault(host, {})
    hass.data.setdefault(DOMAIN, {})

    fryer = _build_device(model, host, token)
    hass.data[DOMAIN][host] = fryer

    coordinator = XiaomiAirFryerCoordinator(hass, fryer, host, scan_interval)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Deliberately not async_config_entry_first_refresh(): an air fryer is
    # usually unplugged between uses. Failing setup would remove the entities
    # entirely, so instead they are created and simply reported unavailable
    # until the device answers again.
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        _LOGGER.info(
            "The air fryer at %s did not answer during setup; "
            "entities start as unavailable and recover once it is reachable",
            host,
        )

    # init setup for each supported domains
    await hass.config_entries.async_forward_entry_setups(entry, DOMAINS)

    return True
