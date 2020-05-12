"""
RDW config flow - Eelco Huininga 2019-2020
Retrieves information on cars registered in the Netherlands. Currently
implemented sensors are APK (general periodic check) insurance status
and recall information
"""


import logging
import voluptuous as vol
from datetime import (
    datetime,
    timedelta,
)
from urllib.parse import urlparse

from homeassistant import config_entries
from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    BINARY_SENSOR_DEFAULTS,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_DATEFORMAT,
    CONF_PLATE,
    DATA_KEY,
    DEFAULT_DATEFORMAT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SENSOR_DEFAULTS,
)
from . import RDWEntity

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("config_flow called")


@config_entries.HANDLERS.register(DOMAIN)
class RDWFlowHandler(config_entries.ConfigFlow):
    """Handle a RDW config flow."""

    _LOGGER.debug("RDWFlowHandler class initialized")

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    _hassio_discovery = None

    def __init__(self):
        """Initialize the config flow."""

        _LOGGER.debug("RDWFlowHandler::__init__ called")

        self.config = None

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""

        _LOGGER.debug("RDWFlowHandler::async_step_import called %s", import_config)

        # Check if already configured
        await self.async_set_unique_id(import_config[CONF_PLATE], raise_on_progress=False)
        self._abort_if_unique_id_configured()

        import_config.update({
            CONF_SCAN_INTERVAL: int(import_config[CONF_SCAN_INTERVAL].total_seconds()),
        })

        if not CONF_MANUFACTURER in import_config:
            import_config.update({
                CONF_MANUFACTURER: None,
            })

        if not CONF_MODEL in import_config:
            import_config.update({
                CONF_MODEL: None,
            })

        if import_config[CONF_NAME] is not None:
            title = '{} (configuration.yaml)'.format(import_config[CONF_NAME])
        else:
            title = '{} (configuration.yaml)'.format(import_config[CONF_PLATE])

        return self.async_create_entry(title=title, data=import_config)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        _LOGGER.debug("RDWFlowHandler::async_step_user called %s", user_input)

        errors = {}
        config_entry = {'data', user_input}

        if user_input is not None:

            user_input.update({CONF_PLATE: user_input[CONF_PLATE].upper().replace("-", "")})

            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_PLATE], raise_on_progress=False)
            self._abort_if_unique_id_configured()

            try:
                rdwdata = RDWEntity(self.hass, config_entry)
                await rdwdata.async_update()

            except RDWEntity.InvalidPlate:
                errors["base"] = "invalid_plate"

            except RDWEntity.NotRegistered:
                errors["base"] = "not_registered"

            except Exception as e:
                _LOGGER.debug("RDWFlowHandler::async_step_user update_about_data exception unknown_error: %s", str(e))
                errors["base"] = "unknown_error"

            else:
                _LOGGER.debug("RDWFlowHandler::async_step_user rdwdata.update() succesfull. rdwdata=%s", rdwdata)

                self.config = {
                    CONF_PLATE: user_input[CONF_PLATE],
                    CONF_NAME: rdwdata._name,
                    CONF_MANUFACTURER: rdwdata.manufacturer,
                    CONF_MODEL: rdwdata.model,
                    CONF_BINARY_SENSORS: BINARY_SENSOR_DEFAULTS,
                    CONF_SENSORS: SENSOR_DEFAULTS,
                    CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())),
                    CONF_DATEFORMAT: DEFAULT_DATEFORMAT,
                }
                _LOGGER.debug("config=%s", self.config)

                return await self.async_step_details(None)

        _LOGGER.debug("RDWFlowHandler::async_step_user show form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLATE): str,
                }
            ),
            errors=errors,
        )

    async def async_step_details(self, user_input=None):
        """Handle a flow initialized by the user."""

        _LOGGER.debug("RDWFlowHandler::async_step_details called %s", user_input)

        errors = {}

        if user_input is not None:

            _LOGGER.debug("RDWFlowHandler::async_step_details")

            if CONF_DATEFORMAT in user_input:
                if validate_dateformat(user_input[CONF_DATEFORMAT]) == False:
                    errors["details"] = "invalid_dateformat"
            else:
                user_input[CONF_DATEFORMAT] = DEFAULT_DATEFORMAT

            self.config.update({
                CONF_NAME: user_input[CONF_NAME],
            })

            return self.async_create_entry(title=user_input[CONF_NAME], data=self.config)

        _LOGGER.debug("RDWFlowHandler::async_step_details show form")
        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=self.config[CONF_NAME]): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    _LOGGER.debug("OptionsFlowHandler class initialized")

    def __init__(self, config_entry):
        """Initialize options flow."""
        _LOGGER.debug("OptionsFlowHandler::__init__")
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        _LOGGER.debug("OptionsFlowHandler::async_step_init")
        if user_input is not None:
            _LOGGER.debug("OptionsFlowHandler::async_step_init create entry %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        _LOGGER.debug("OptionsFlowHandler::async_step_init data=%s options=%s", self.config_entry.data, self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DATEFORMAT,
                        default=self.config_entry.options.get(
                            CONF_DATEFORMAT,
                            DEFAULT_DATEFORMAT,
                        ),
                    ): str,
                }
            ),
        )


def validate_dateformat(date_text):
    try:
        if date_text != datetime.strptime(date_text, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False

