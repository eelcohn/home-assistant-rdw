"""
RDW config flow version 2.9.2 Eelco Huininga 2019-2020
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
    CONF_DATEFORMAT,
    CONF_PLATE,
    DATA_KEY,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SENSOR_DEFAULTS
)
from . import RDWEntity

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("config_flow called")


@callback
def configured_instances(hass):
    """Return a set of configured RDW instances."""

    if DATA_KEY in hass.data:
        result = set(entry for entry in hass.data[DATA_KEY])
        _LOGGER.debug("config_flow::configured_instances called - returned configured instances %s", result)
        return result
    else:
        _LOGGER.debug("config_flow::configured_instances called - no instances found")
        return {}


@config_entries.HANDLERS.register(DOMAIN)
class RDWFlowHandler(config_entries.ConfigFlow):
    """Handle a RDW config flow."""

    _LOGGER.debug("RDWFlowHandler class initialized")

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    _hassio_discovery = None

    def __init__(self):
        """Initialize the config flow."""

        _LOGGER.debug("RDWFlowHandler::__init__ called")

        self.config = None

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""

        _LOGGER.debug("RDWFlowHandler::async_step_import called %s", import_config)

#        if self._async_current_entries():
        if import_config[CONF_PLATE] in configured_instances(self.hass):
            _LOGGER.debug("RDWFlowHandler::async_step_import aborted for %s (already configured)", import_config[CONF_PLATE])
            return self.async_abort(reason="already_configured")

        import_config.update({
            CONF_SCAN_INTERVAL: int(import_config[CONF_SCAN_INTERVAL].total_seconds()),
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

        if user_input is not None:

            user_input.update({CONF_PLATE: user_input[CONF_PLATE].upper().replace("-", "")})

            if user_input[CONF_PLATE] in configured_instances(self.hass):
                return self.async_abort(reason="already_configured")

            try:
                rdwdata = RDWEntity(self.hass, user_input[CONF_PLATE])
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

                name = await rdwdata.create_name(rdwdata.brand, rdwdata.type)

                self.config = {
                    CONF_PLATE: user_input[CONF_PLATE],
                    CONF_NAME: name,
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

            if user_input[CONF_NAME] in configured_instances(self.hass):
                errors["details"] = "name_already_configured"

            if CONF_DATEFORMAT in user_input:
                if validate_dateformat(user_input[CONF_DATEFORMAT]) == False:
                    errors["details"] = "invalid_dateformat"
            else:
                user_input[CONF_DATEFORMAT] = None

            self.config.update({
                CONF_NAME: user_input[CONF_NAME],
                CONF_DATEFORMAT: user_input[CONF_DATEFORMAT],
                CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds())),
                CONF_BINARY_SENSORS: BINARY_SENSOR_DEFAULTS,
                CONF_SENSORS: SENSOR_DEFAULTS,
            })

            return self.async_create_entry(title=user_input[CONF_NAME], data=self.config)

        _LOGGER.debug("RDWFlowHandler::async_step_details show form")
        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=self.config[CONF_NAME]): str,
                    vol.Optional(CONF_DATEFORMAT): str,
                }
            ),
            errors=errors,
        )


def validate_dateformat(date_text):
    try:
        if date_text != datetime.strptime(date_text, "%Y-%m-%d").strftime('%Y-%m-%d'):
            raise ValueError
        return True
    except ValueError:
        return False

