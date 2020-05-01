"""
RDW sensor version 2.9.3 Eelco Huininga 2019-2020
Retrieves information on cars registered in the Netherlands. Currently
implemented sensors are APK (general periodic check) insurance status
and recall information
"""

from datetime import datetime
import logging

from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_NAME,
    CONF_SENSORS,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity


from .const import (
    CONF_PLATE,
    CONF_DATEFORMAT,
    DEFAULT_ATTRIBUTION,
    DOMAIN,
    RDW_DATEFORMAT,
    SENSOR_TYPES,
    TOPIC_DATA_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the RDW Sensor based on a config entry."""

    _LOGGER.debug("async_setup_entry: called")

    dev = []
    for sensor_type in entry.data[CONF_SENSORS]:
        _LOGGER.debug("async_setup_entry: plate=%s setup for %s", entry.data[CONF_PLATE], sensor_type)
        dev.append(RDWSensor(
            hass.data[DOMAIN][entry.data[CONF_PLATE]]['entity'],
            sensor_type,
            entry.data[CONF_NAME],
            entry.data[CONF_PLATE],
            entry.data[CONF_DATEFORMAT],
        )
    )

    async_add_entities(dev, True)


class RDWSensor(Entity):
    """Representation of a RDW Sensor."""

    _LOGGER.debug("RDWSensor class initialized")

    def __init__(self, rdw, sensor_type, name, plate, dateformat):
        """Initialize the sensor."""

        _LOGGER.debug("RDWSensor::__init__ plate=%s sensor=%s", plate, sensor_type)

        self._available = True
        self._data = rdw
        self._sensor_type = sensor_type
        self._name = name
        self._plate = plate
        self._dateformat = dateformat
        self._icon = SENSOR_TYPES[sensor_type][1]
        self._state = None
        self._attributes = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._unit_of_measurement = None

    @property
    def available(self):
        """Return the availability of the sensor."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes    

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
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    async def async_update(self):
        """Fetch new state data for the sensor."""

        _LOGGER.debug("RDWSensor::async_update plate=%s sensor=%s", self._plate, self._sensor_type)

        self._state = STATE_UNKNOWN
        self._attributes = {}

        if self._sensor_type == 'expdate':
            if self._data.expdate is not None:
                self._state = datetime.strptime(self._data.expdate, RDW_DATEFORMAT)
                if self._dateformat is not None:
                    self._state = self.state.date().strftime(self._dateformat)
                else:
                    self._state = self.state.date().isoformat()
                if datetime.strptime(self._data.expdate, RDW_DATEFORMAT) < \
                    datetime.now():
                        self._icon = SENSOR_TYPES['expdate'][2]
        elif self._sensor_type == 'recall':
            if self._data.recall is not None:
                self._state = self._data.recall
                self._attributes = self._data.attrs
                if self.state > 0:
                    self._icon = SENSOR_TYPES['recall'][2]

    async def async_added_to_hass(self):
        """Register callbacks."""

        _LOGGER.debug("RDWSensor::async_added_to_hass plate=%s sensor=%s", self._plate, self._sensor_type)

        @callback
        def update():
            """Update the entity."""

            _LOGGER.debug("RDWSensor::async_added_to_hass::update plate=%s sensor=%s", self._plate, self._sensor_type)

            self.hass.async_create_task(self.async_update())
            self.async_schedule_update_ha_state(False)

        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self.hass,
            TOPIC_DATA_UPDATE,
            update
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""

        _LOGGER.debug("RDWSensor::async_will_remove_from_hass plate=%s sensor=%s", self._plate, self._sensor_type)

        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()

