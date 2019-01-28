"""
RDW sensor version 1.0.2 Eelco Huininga 2019
Retrieves information on cars registered in the
Netherlands. Currently implemented sensors are APK
(general periodic check), recall information and
insurance status.
"""

VERSION = '1.0.2'

from datetime import datetime, timedelta
from requests import Session

import json
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (ATTR_ATTRIBUTION, CONF_NAME, STATE_UNKNOWN)
from homeassistant.util import Throttle

REQUIREMENTS = []

_RESOURCE = 'https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={}'
_LOGGER = logging.getLogger(__name__)

CONF_PLATE = 'plate'
CONF_SCAN_INTERVAL = 'scan_interval'
CONF_SENSORS = 'sensors'

DEFAULT_NAME = 'RDW'
DEFAULT_ATTRIBUTION = 'Data provided by RDW'
DEFAULT_SCAN_INTERVAL = timedelta(hours=24)

RDW_DATEFORMAT = '%d/%m/%Y'

SENSOR_TYPES = {
    'expdate': ['Expdate', 'mdi:calendar'],
    'insured': ['Insured', 'mdi:car'],
    'recall':  ['Recall',  'mdi:wrench'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PLATE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SENSORS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
        cv.time_period
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the RDW Sensor."""

    name = config.get(CONF_NAME)
    plate = config.get(CONF_PLATE)
    interval = config.get(CONF_SCAN_INTERVAL)

    data = RDWSensorData(hass, plate.upper(), interval)

    dev = []
    for sensor_type in config[CONF_SENSORS]:
        dev.append(RDWSensor(
            hass, data, sensor_type, name,
            plate.upper()))

    add_devices(dev, True)


class RDWSensor(Entity):
    """Representation of a RDW Sensor."""

    def __init__(self, hass, data, sensor_type, name, plate):
        """Initialize the sensor."""
        self._hass = hass
        self._data = data
        self._sensor_type = sensor_type
        self._name = name
        self._plate = plate
        self._icon = SENSOR_TYPES[sensor_type][1]
        self._state = None
        self._attributes = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._unit_of_measurement = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._name, self._sensor_type)

    @property
    def icon(self):
        """Return the mdi icon of the sensor."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes    

    def update(self):
        """Fetch new state data for the sensor."""
        self._data.update()

        if self._sensor_type == 'expdate':
            value = self._data.expdate
        elif self._sensor_type == 'insured':
            if self._data.insured == 'Ja':
                value = True
            elif self._data.insured == 'Nee':
                value = False
            else:
                value = None
        elif self._sensor_type == 'recall':
            if self._data.recall == 'Ja':
                value = True
            elif self._data.recall == 'Nee':
                value = False
            else:
                value = None
 
        if value is None:
            value = STATE_UNKNOWN
            self._attributes = {}
        else:
            self._state = value   
            self._attributes = self._data.attrs 

    

class RDWSensorData(object):
    """
    Get car data from the RDW API.
    """
    _current_status_code = None
    _interval = DEFAULT_SCAN_INTERVAL

    def __init__(self, hass, plate, interval):
        """
        Initiates the sensor data with default settings if none other are set.
        :param plate: license plate id
        """
        self._hass = hass
        self._plate = plate
        self._interval = interval
        self._session = Session()
        self.expdate = None
        self.insured = None
        self.recall = None
        self.attrs = {}

    def get_data_from_api(self):
        """
        Get data from the RDW API
        :return: A list containing the RDW data
        """

        try:
            result = self._session.get(_RESOURCE.format(self._plate), data="json={}")
        except:
            _LOGGER.error("RDW: Unable to connect to the RDW API")
            return None

        self._current_status_code = result.status_code

        if self._current_status_code != 200:
            _LOGGER.error("RDW: Got an invalid HTTP status code %s", self._current_status_code)
            return None

        _LOGGER.debug("RDW: raw data: %s", result)

        try:
            data = result.json()[0]
        except:
            _LOGGER.error("RDW: Got invalid response from RDW API. Is the license plate id %s correct?", self._plate)
            data = None

        return data


    @Throttle(_interval)
    def update(self):
        self.expdate = None
        self.insured = None
        self.recall = None
        self.attrs = {}

        rdw_data = (self.get_data_from_api())

        if rdw_data is not None:
            try:
                self.expdate = datetime.strptime(rdw_data['vervaldatum_apk'], RDW_DATEFORMAT).date()
            except:
                self.expdate = None
            try:
                self.insured = rdw_data['wam_verzekerd']
            except:
                self.insured = None
            try:
                self.recall = rdw_data['openstaande_terugroepactie_indicator']
            except:
                self.insured = None

