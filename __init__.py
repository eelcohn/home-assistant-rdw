"""
RDW component version 2.9.2 Eelco Huininga 2019-2020
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

from homeassistant.const import (
    CONF_BINARY_SENSORS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import Throttle

from .const import (
    BINARY_SENSOR_DEFAULTS,
    BINARY_SENSOR_TYPES,
    CONF_BINARY_SENSOR,
    CONF_PLATE,
    CONF_DATEFORMAT,
    CONF_SENSOR,
    DATA_KEY,
    DATA_LISTENER,
    DEFAULT_ATTRIBUTION,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RDW_DATEFORMAT,
    RDW_ENDPOINTS,
    RESOURCE_RECALLINFO,
    SENSOR_DEFAULTS,
    SENSOR_TYPES,
    TOPIC_DATA_UPDATE,
)

from sodapy import Socrata

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_PLATE): cv.string,
                        vol.Optional(CONF_BINARY_SENSORS, default=BINARY_SENSOR_DEFAULTS): vol.All(cv.ensure_list, [vol.In(BINARY_SENSOR_TYPES)]),
                        vol.Optional(CONF_DATEFORMAT, default=None): vol.Any(cv.string, None),
                        vol.Optional(CONF_NAME, default=None): vol.Any(cv.string, None),
                        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
                        vol.Optional(CONF_SENSORS, default=SENSOR_DEFAULTS): vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the RDW component from configuration.yaml: redirect to config_flow.async_import_step"""

    _LOGGER.debug("__init__::async_setup config=%s", config)

    if DOMAIN not in config:
        return True

    # Initiate the config_flow::async_step_import() for each instance
    for rdw in config[DOMAIN]:
        _LOGGER.debug("__init__::async_setup rdw=%s", rdw)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=dict(rdw),
            )
        )

    return True

async def async_setup_entry(hass, config_entry):
    """Set up the RDW component from the entity registry or the config_flow"""

    _LOGGER.debug("__init__::async_setup_entry config_entry.data=%s", config_entry.data)

    rdw = RDWEntity(hass, config_entry.data[CONF_PLATE])
    if not await rdw.async_update():
        raise PlatformNotReady

    if config_entry.data[CONF_NAME] is None:
        name = await rdw.create_name(rdw.brand, rdw.type)
        _LOGGER.debug("RDWEntity::async_setup_entry name: %s", name)
        config_entry.data.update({CONF_NAME: name})

    # Make sure there's a RDW entry in hass.data in case this is the first RDW entity
    if DOMAIN not in hass.data:
        hass.data.update({DOMAIN: {}})

    hass.data[DOMAIN].update({config_entry.data[CONF_PLATE]: {'entity': rdw}})

    for component in (CONF_BINARY_SENSOR, CONF_SENSOR):
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    async def async_track_time_interval_update(event_time):
        """Update the entity and all it's components."""

        _LOGGER.debug("RDWEntity::__init__::async_track_time_interval_update called")

        if not await rdw.async_update():
            _LOGGER.warning("Failed to update")
        else:
            async_dispatcher_send(hass, TOPIC_DATA_UPDATE)

    hass.data[DOMAIN][config_entry.data[CONF_PLATE]].update({
        DATA_LISTENER: {
            config_entry.entry_id: async_track_time_interval(
                hass,
                async_track_time_interval_update,
                timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL])
            )
        }
    })

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a RDW config entry."""

    _LOGGER.debug("__init__::async_unload_entry config=%s", config_entry)

    cancel = hass.data[DOMAIN][config_entry.data[CONF_PLATE]][DATA_LISTENER].pop(config_entry.entry_id)
    cancel()

    for component in ("binary_sensor", "sensor"):
        await hass.config_entries.async_forward_entry_unload(config_entry, component)

    return True


class RDWEntity(Entity):
    """Representation of a RDW entity"""

    _LOGGER.debug("RDWEntity class initialized")

    def __init__(self, hass, plate):

        _LOGGER.debug("RDWEntity::__init__ called plate=%s", plate)

        if not self.validate_plate(plate):
            raise(RDWEntity.InvalidPlate('The plate with ID %s is invalid.' % plate))

        self._hass = hass
        self._plate = plate
        self.brand = None
        self.expdate = None
        self.insured = None
        self.recall = None
        self.type = None
        self.attrs = {}

        self.apkdata = None
        self.recalldata = None

        self.client = Socrata("opendata.rdw.nl", "")

    async def async_setup(self):
        """Schedule initial and regular updates based on configured time interval."""

        _LOGGER.debug("RDWEntity::async_setup called")

        for domain in PLATFORMS:
            self._hass.async_create_task(
                self._hass.config_entries.async_forward_entry_setup(
                    self._config_entry, domain
                )
            )

    async def async_update(self):
        """Update RDW information from the RDW API."""

        _LOGGER.debug("RDWEntity::async_update called for %s", self._plate)

        self.attrs = {}

        # Get APK data from the RDW Open Data API
        try:
            self.apkdata = self.client.get(
                RDW_ENDPOINTS['apk']['endpoint'],
#                ('{}={}'.format(RDW_ENDPOINTS['apk']['rdwfilter'], self._plate)),
                kenteken=self._plate
            )
        except Exception as e:
            _LOGGER.warning("Unable to update data from endpoint %s for %s: %s", RDW_ENDPOINTS['apk']['endpoint'], self._plate, e)
#            raise RDWEntity.ConnectionError
            return False
        else:
            _LOGGER.debug("RDWEntity::async_update endpoint %s success for %s", RDW_ENDPOINTS['apk']['endpoint'], self._plate)

        # Get Recall data from the RDW Open Data API
        try:
            self.recalldata = self.client.get(
                RDW_ENDPOINTS['recall']['endpoint'],
#                ('{}={}'.format(RDW_ENDPOINTS['recall']['rdwfilter'], self._plate)),
                kenteken=self._plate
            )
        except Exception as e:
            _LOGGER.warning("Unable to update data from endpoint %s for %s: %s", RDW_ENDPOINTS['recall']['endpoint'], self._plate, e)
#            raise RDWEntity.ConnectionError
            return False
        else:
            _LOGGER.debug("RDWEntity::async_update endpoint %s success for %s", RDW_ENDPOINTS['recall']['endpoint'], self._plate)

        # Check if RDW returned any data
        if not self.apkdata:
            raise RDWEntity.NotRegistered

        # Brand (Merk)
        try:
            self.brand = self.apkdata[0]['merk']
        except:
            self.brand = None

        # Type (Handelsbenaming)
        try:
            self.type = self.apkdata[0]['handelsbenaming']
        except:
            self.type = None

        # Expire date (Vervaldatum APK)
        try:
            self.expdate = self.apkdata[0]['vervaldatum_apk']
        except:
            self.expdate = None

        # Insurance state (WAM Verzekerd)
        try:
            self.insured = self.apkdata[0]['wam_verzekerd']
        except:
            self.insured = None

        if self.recalldata is not None:
            for recall in self.recalldata:
                if recall['code_status'] != 'P':
                    self.attrs[recall['referentiecode_rdw'].lower()] = \
                        RESOURCE_RECALLINFO.format(recall['referentiecode_rdw'])

        self.recall = len(self.attrs)

        return True

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "model": self.type,
            "manufacturer": self.brand,
            "via_device": (DOMAIN),
        }

    def validate_plate(self, plate):
        """Check if the format of the user input is correct"""

        if len(plate) == 6:
            if plate.isalnum():
                return True

        return False

    async def create_name(self, car_brand, car_type):
        """Generate a name of this car"""

        # The RDW model field sometimes also contains the brand of the car. We need to check that so that we get the name for our integration right
        if car_type.startswith(car_brand):
            return car_type.title()
        else:
            return '{} {}'.format(car_brand, car_type).title()

    class ConnectionError(Exception):
        """Can't connect to the RDW OpenData API"""
        pass

    class InvalidPlate(Exception):
        """License plate ID format is invalid"""
        pass

    class NotRegistered(Exception):
        """License plate ID is not registered at RDW"""
        pass

