"""Config flow to configure Mijia AirFryer component."""
import base64
import logging
from re import search

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import callback
from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import FileSelector, FileSelectorConfig
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_DEVICE,
    CONF_MAC,
    CONF_MODEL,
    MAJOR_VERSION,
    MINOR_VERSION
)

from homeassistant.components.xiaomi_miio.const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    CONF_FLOW_TYPE,
    CONF_MANUAL,
    DEFAULT_CLOUD_COUNTRY,
    SERVER_COUNTRY_CODES,
    AuthException,
    SetupException,
)
from homeassistant.components.xiaomi_miio.device import ConnectXiaomiDevice

from .token_backup import TokenBackupException, extract_devices
from .xiaomi_cloud import XiaomiCloud, XiaomiCloudException

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    MODELS_ALL_DEVICES
)

_LOGGER = logging.getLogger(__name__)

DEVICE_SETTINGS = {
    vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
}
DEVICE_CONFIG = vol.Schema({vol.Required(CONF_HOST): str}).extend(DEVICE_SETTINGS)
DEVICE_MODEL_CONFIG = vol.Schema({vol.Required(CONF_MODEL): vol.In(MODELS_ALL_DEVICES)})
DEVICE_CLOUD_CONFIG = vol.Schema(
    {
        vol.Optional(CONF_CLOUD_COUNTRY, default=DEFAULT_CLOUD_COUNTRY): vol.In(
            SERVER_COUNTRY_CODES
        ),
        vol.Optional(CONF_MANUAL, default=False): bool,
    }
)

CONF_BACKUP_FILE = "backup_file"
CONF_BACKUP_PASSWORD = "backup_password"

DEVICE_BACKUP_CONFIG = vol.Schema(
    {
        vol.Required(CONF_BACKUP_FILE): FileSelector(
            FileSelectorConfig(accept=".ab,.db,.sqlite,.sqlite3")
        ),
        vol.Optional(CONF_BACKUP_PASSWORD): str,
    }
)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init object."""
        if (MAJOR_VERSION, MINOR_VERSION) < (2024, 11):
            self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        if user_input is not None:
            self.options.update(user_input)
            use_cloud = self.options.get(CONF_MANUAL, False)
            cloud_username = self.options.get(CONF_CLOUD_USERNAME)
            cloud_password = self.options.get(CONF_CLOUD_PASSWORD)
            cloud_country = self.options.get(CONF_CLOUD_COUNTRY)

            if use_cloud and (
                not cloud_username or not cloud_password or not cloud_country
            ):
                errors["base"] = "cloud_credentials_incomplete"
                # trigger re-auth flow
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": SOURCE_REAUTH},
                        data=self.options,
                    )
                )

            if not errors:
                return self.async_create_entry(title="", data=self.options)

        settings_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): int
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=settings_schema, errors=errors
        )


class XiaomiAirFryerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Xiaomi AirFryer config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self.host = None
        self.mac = None
        self.token = None
        self.model = None
        self.name = None
        self.cloud_username = None
        self.cloud_password = None
        self.cloud_country = None
        self.cloud_devices = {}
        self._cloud = None
        self._login_task = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlowHandler:
        """Get the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an authentication error or missing cloud credentials."""
        self.host = user_input[CONF_HOST]
        self.token = user_input[CONF_TOKEN]
        self.mac = user_input[CONF_MAC]
        self.model = user_input.get(CONF_MODEL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_cloud()
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({})
        )

    async def async_step_import(self, conf: dict):
        """Import a configuration from config.yaml."""
        self.host = conf[CONF_HOST]
        self.token = conf[CONF_TOKEN]
        self.name = conf.get(CONF_NAME)
        self.model = conf.get(CONF_MODEL)

        self.context.update(
            {"title_placeholders": {"name": f"YAML import {self.host}"}}
        )
        return await self.async_step_connect()

    async def async_step_user(self, user_input=None):
        """Let the user pick how the token should be obtained."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "backup", "manual"],
        )

    async def async_step_backup(self, user_input=None):
        """Read the token out of a Mi Home app backup, without the cloud."""
        errors = {}

        if user_input is not None:
            def _read():
                with process_uploaded_file(self.hass, user_input[CONF_BACKUP_FILE]) as path:
                    return extract_devices(str(path), user_input.get(CONF_BACKUP_PASSWORD))

            try:
                devices_raw = await self.hass.async_add_executor_job(_read)
            except TokenBackupException as ex:
                _LOGGER.error("Could not read the backup: %s", ex)
                errors["base"] = "backup_unreadable"
            else:
                self.cloud_devices = {
                    f"{device['name']} - {device['model']}": device
                    for device in devices_raw
                    if device.get("model") in MODELS_ALL_DEVICES
                }

                if not self.cloud_devices:
                    errors["base"] = "backup_no_devices"
                elif len(self.cloud_devices) == 1:
                    self.extract_cloud_info(list(self.cloud_devices.values())[0])
                    return await self.async_step_connect()
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="backup", data_schema=DEVICE_BACKUP_CONFIG, errors=errors
        )

    def _async_update_known_host(self, entry) -> bool:
        """Store a changed IP address on an entry that is already set up.

        _abort_if_unique_id_configured(updates=...) cannot be used here: it
        writes into entry.data, and async_setup_entry migrates a non-empty
        entry.data over the options wholesale. That migration would replace
        the options with just the host and drop the token, model and mac.
        So the host is updated where it actually lives.
        """
        if entry.options.get(CONF_HOST) is not None:
            if entry.options[CONF_HOST] == self.host:
                return False
            self.hass.config_entries.async_update_entry(
                entry, options={**entry.options, CONF_HOST: self.host}
            )
            return True

        if entry.data.get(CONF_HOST) is not None:
            if entry.data[CONF_HOST] == self.host:
                return False
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_HOST: self.host}
            )
            return True

        return False

    async def async_step_zeroconf(self, discovery_info):
        """Handle zeroconf discovery."""
        name = discovery_info.name
        self.host = str(discovery_info.ip_address)
        self.mac = discovery_info.properties.get("mac")
        if self.mac is None:
            poch = discovery_info.properties.get("poch", "")
            result = search(r"mac=\w+", poch)
            if result is not None:
                self.mac = result.group(0).split("=")[1]

        if not name or not self.host or not self.mac:
            return self.async_abort(reason="not_xiaomi_miio")

        self.mac = format_mac(self.mac)

        for device_model in MODELS_ALL_DEVICES:
            if name.startswith(device_model.replace(".", "-")):
                unique_id = self.mac
                existing_entry = await self.async_set_unique_id(unique_id)

                if existing_entry is not None:
                    if self._async_update_known_host(existing_entry):
                        _LOGGER.info(
                            "%s moved to %s, updating the configuration entry",
                            device_model,
                            self.host,
                        )
                    return self.async_abort(reason="already_configured")

                self.context.update(
                    {"title_placeholders": {"name": f"{device_model} {self.host}"}}
                )

                return await self.async_step_cloud()

        # Discovered device is not yet supported
        _LOGGER.debug(
            "Not yet supported Xiaomi Miio device '%s' discovered with host %s",
            name,
            self.host,
        )
        return self.async_abort(reason="not_xiaomi_miio")

    def extract_cloud_info(self, cloud_device_info):
        """Extract the cloud info."""
        if self.host is None:
            self.host = cloud_device_info["localip"]
        if self.mac is None:
            self.mac = format_mac(cloud_device_info["mac"])
        if self.model is None:
            self.model = cloud_device_info["model"]
        if self.name is None:
            self.name = cloud_device_info["name"]
        self.token = cloud_device_info["token"]

    async def async_step_cloud(self, user_input=None):
        """Pick a server and sign in to the Xiaomi cloud by scanning a QR code."""
        if user_input is not None:
            if user_input[CONF_MANUAL]:
                return await self.async_step_manual()

            self.cloud_country = user_input[CONF_CLOUD_COUNTRY]
            return await self.async_step_qr()

        return self.async_show_form(
            step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG, errors={}
        )

    async def async_step_qr(self, user_input=None):
        """Show a QR code and wait for the Mi Home app to scan it."""
        if self._login_task is None:
            self._cloud = XiaomiCloud(self.cloud_country)
            try:
                await self._cloud.async_open()
                await self._cloud.async_start_login()
            except XiaomiCloudException as ex:
                _LOGGER.error("Could not start the Xiaomi login: %s", ex)
                await self._async_close_cloud()
                return self.async_abort(reason="cloud_login_error")

            self._login_task = self.hass.async_create_task(
                self._cloud.async_wait_for_scan()
            )

        if not self._login_task.done():
            placeholders = {"url": self._cloud.login_url}
            if self._cloud.qr_image is not None:
                encoded = base64.b64encode(self._cloud.qr_image).decode()
                placeholders["qr"] = f"![QR](data:image/png;base64,{encoded})"
            else:
                placeholders["qr"] = ""

            return self.async_show_progress(
                step_id="qr",
                progress_action="scan_qr",
                description_placeholders=placeholders,
                progress_task=self._login_task,
            )

        try:
            self._login_task.result()
        except XiaomiCloudException as ex:
            _LOGGER.error("Xiaomi login failed: %s", ex)
            await self._async_close_cloud()
            self._login_task = None
            return self.async_show_progress_done(next_step_id="login_failed")
        finally:
            self._login_task = None

        return self.async_show_progress_done(next_step_id="cloud_devices")

    async def async_step_login_failed(self, user_input=None):
        """Report that the QR login did not complete."""
        return self.async_abort(reason="cloud_login_error")

    async def async_step_cloud_devices(self, user_input=None):
        """Pick the fryer out of the devices on the account."""
        try:
            devices_raw = await self._cloud.async_get_devices()
        except XiaomiCloudException as ex:
            _LOGGER.error("Could not list the devices on the account: %s", ex)
            return self.async_abort(reason="cloud_login_error")
        finally:
            await self._async_close_cloud()

        self.cloud_devices = {}
        for device in devices_raw:
            if device.get("model") in MODELS_ALL_DEVICES and not device.get("parent_id"):
                list_name = f"{device['name']} - {device['model']}"
                self.cloud_devices[list_name] = device

        if not self.cloud_devices:
            return self.async_abort(reason="cloud_no_devices")

        # Discovery already told us which address we are configuring.
        if self.host is not None:
            for device in self.cloud_devices.values():
                if device.get("localip") == self.host:
                    self.extract_cloud_info(device)
                    return await self.async_step_connect()

        if len(self.cloud_devices) == 1:
            self.extract_cloud_info(list(self.cloud_devices.values())[0])
            return await self.async_step_connect()

        return await self.async_step_select()

    async def _async_close_cloud(self):
        """Drop the cloud session once the token has been read out of it."""
        if self._cloud is not None:
            await self._cloud.async_close()
            self._cloud = None

    async def async_step_select(self, user_input=None):
        """Handle multiple cloud devices found."""
        errors = {}
        if user_input is not None:
            cloud_device = self.cloud_devices[user_input["select_device"]]
            self.extract_cloud_info(cloud_device)
            return await self.async_step_connect()

        select_schema = vol.Schema(
            {vol.Required("select_device"): vol.In(list(self.cloud_devices))}
        )

        return self.async_show_form(
            step_id="select", data_schema=select_schema, errors=errors
        )

    async def async_step_manual(self, user_input=None):
        """Configure a xiaomi miio device Manually."""
        errors = {}
        if user_input is not None:
            self.token = user_input[CONF_TOKEN]
            if user_input.get(CONF_HOST):
                self.host = user_input[CONF_HOST]

            return await self.async_step_connect()

        if self.host:
            schema = vol.Schema(DEVICE_SETTINGS)
        else:
            schema = DEVICE_CONFIG

        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    async def async_step_connect(self, user_input=None):
        """Connect to a xiaomi miio device."""
        errors = {}
        if self.host is None or self.token is None:
            return self.async_abort(reason="incomplete_info")

        if user_input is not None:
            self.model = user_input[CONF_MODEL]

        # Try to connect to a Xiaomi Device.
        connect_device_class = ConnectXiaomiDevice(self.hass)
        try:
            await connect_device_class.async_connect_device(self.host, self.token)
        except AuthException:
            if self.model is None:
                errors["base"] = "wrong_token"
        except SetupException:
            if self.model is None:
                errors["base"] = "cannot_connect"

        device_info = connect_device_class.device_info

        if self.model is None and device_info is not None:
            self.model = device_info.model

        if self.model is None and not errors:
            errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="connect", data_schema=DEVICE_MODEL_CONFIG, errors=errors
            )

        if self.mac is None and device_info is not None:
            self.mac = format_mac(device_info.mac_address)

        unique_id = self.mac
        existing_entry = await self.async_set_unique_id(
            unique_id, raise_on_progress=False
        )
        if existing_entry:
            # Merge into whichever of options/data the entry actually uses.
            # Copying entry.data and writing it back destroyed the entry once
            # async_setup_entry had migrated everything into options: data was
            # empty by then, so the write left only host and token behind, and
            # the next setup migrated those two over the options -- dropping
            # model, mac and flow_type and failing with "Invalid FryerMiot
            # model: None".
            updates = {CONF_HOST: self.host, CONF_TOKEN: self.token}
            if (
                self.cloud_username is not None
                and self.cloud_password is not None
                and self.cloud_country is not None
            ):
                updates[CONF_CLOUD_USERNAME] = self.cloud_username
                updates[CONF_CLOUD_PASSWORD] = self.cloud_password
                updates[CONF_CLOUD_COUNTRY] = self.cloud_country

            if existing_entry.options:
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    options={**existing_entry.options, **updates},
                )
            else:
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={**existing_entry.data, **updates},
                )

            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        if self.name is None:
            self.name = self.model

        flow_type = None
        if flow_type is None:
            for device_model in MODELS_ALL_DEVICES:
                if self.model.startswith(device_model):
                    flow_type = CONF_DEVICE

        if flow_type is not None:
            return self.async_create_entry(
                title=self.name,
                data={
                    CONF_FLOW_TYPE: flow_type,
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    CONF_MODEL: self.model,
                    CONF_MAC: self.mac,
                    CONF_CLOUD_USERNAME: self.cloud_username,
                    CONF_CLOUD_PASSWORD: self.cloud_password,
                    CONF_CLOUD_COUNTRY: self.cloud_country,
                },
            )

        errors["base"] = "unknown_device"
        return self.async_show_form(
            step_id="connect", data_schema=DEVICE_MODEL_CONFIG, errors=errors
        )
