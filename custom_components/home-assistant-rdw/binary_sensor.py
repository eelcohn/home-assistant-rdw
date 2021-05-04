"""
RDW binary sensor - Eelco Huininga 2019-2020
Retrieves information on cars registered in the Netherlands. Currently
implemented sensors are APK (general periodic check) insurance status
and recall information
"""

import logging

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_ID,
    CONF_BINARY_SENSORS,
    CONF_NAME,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    ATTRIBUTION,
    BINARY_SENSOR_TYPES,
    CONF_PLATE,
    DEFAULT_ATTRIBUTION,
    DOMAIN,
    TOPIC_DATA_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the RDW Binary Sensor based on a config entry."""

    _LOGGER.debug("async_setup_entry: called")

    dev = []
    for sensor_type in entry.data[CONF_BINARY_SENSORS]:
        _LOGGER.debug("async_setup_entry: plate=%s setup for %s", entry.data[CONF_PLATE], sensor_type)
        dev.append(RDWBinarySensor(
            hass.data[DOMAIN][entry.data[CONF_PLATE]]['entity'],
            sensor_type,
            entry.data[CONF_NAME],
            entry.data[CONF_PLATE],
        )
    )

    async_add_entities(dev, True)


class RDWBinarySensor(Entity):
    """Representation of a RDW Sensor."""

    _LOGGER.debug("RDWBinarySensor class initialized")

    def __init__(self, rdw, sensor_type, name, plate):
        """Initialize the sensor."""

        _LOGGER.debug("RDWBinarySensor::__init__ plate=%s sensor=%s", plate, sensor_type)

        self._available = True
        self._data = rdw
        self._sensor_type = sensor_type
        self._name = name
        self._plate = plate
        self._icon = BINARY_SENSOR_TYPES[sensor_type][1]
        self._state = None
        self._unit_of_measurement = None
        self._unique_id = '{}_{}_{}'.format(DOMAIN, self._plate, self._sensor_type)

    @property
    def device_info(self):
        """Return the device info."""
        result = {
            "identifiers": {(DOMAIN, self._plate.lower())},
            "manufacturer": self._data.manufacturer,
            "model": self._data.model,
            "name": self._name,
            "via_device": (DOMAIN),
        }
        _LOGGER.debug("RDWBinarySensor::device_info result=%s", result)
        return result

    @property
    def available(self):
        """Return the availability of the sensor."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes."""

        # Set default attribution
        attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_ID: f"nl_{self._plate.lower()}",
        }

        return attributes

    @property
    def icon(self):
        """Return the mdi icon of the sensor."""
        return self._icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._name, self._sensor_type)

    @property
    def should_poll(self):
        """Return the polling requirement for this sensor."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return '{}_{}_{}'.format(DOMAIN, self._plate, self._sensor_type)

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    async def async_update(self):
        """Fetch new state data for the sensor."""

        _LOGGER.debug("RDWBinarySensor::async_update plate=%s sensor=%s", self._plate, self._sensor_type)

        self._state = STATE_UNKNOWN
        self._attributes = {}

        if self._sensor_type == 'insured':
            if self._data.insured is not None:
                if self._data.insured == 'Ja':
                    self._state = True
                elif self._data.insured == 'Nee':
                    self._state = False
                    self._icon = BINARY_SENSOR_TYPES['insured'][2]

    async def async_added_to_hass(self):
        """Register callbacks."""

        _LOGGER.debug("RDWBinarySensor::async_added_to_hass plate=%s sensor=%s", self._plate, self._sensor_type)

        @callback
        def update():
            """Update the entity."""

            _LOGGER.debug("RDWBinarySensor::async_added_to_hass::update plate=%s sensor=%s", self._plate, self._sensor_type)

            self.hass.async_create_task(self.async_update())
            self.async_schedule_update_ha_state(False)

        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self.hass,
            TOPIC_DATA_UPDATE,
            update
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""

        _LOGGER.debug("RDWBinarySensor::async_will_remove_from_hass plate=%s sensor=%s", self._plate, self._sensor_type)

        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()

