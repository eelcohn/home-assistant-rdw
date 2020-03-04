"""Constants for the RDW component."""

from datetime import (
    timedelta,
)

CONF_BINARY_SENSOR = "binary_sensor"
CONF_DATEFORMAT = 'dateformat'
CONF_PLATE = 'plate'
CONF_SENSOR = "sensor"

DEFAULT_NAME = 'RDW'
DEFAULT_ATTRIBUTION = 'Data provided by RDW'
DEFAULT_SCAN_INTERVAL = timedelta(minutes=2)

DOMAIN = "rdw"
DATA_KEY = DOMAIN
DATA_LISTENER = "listener"

RDW_DATEFORMAT = '%Y%m%d'
RDW_ENDPOINTS = {
    'apk':                 {'endpoint': 'm9d7-ebf2', 'rdwfilter': 'kenteken'},
    'recall':              {'endpoint': 't49b-isb7', 'rdwfilter': 'kenteken'},
    'recall_inform_owner': {'endpoint': 'mh8w-8cup', 'rdwfilter': 'referentiecode_rdw'},
    'recall_risk':         {'endpoint': '9ihi-jgpf', 'rdwfilter': 'referentiecode_rdw'},
    'recall_details':      {'endpoint': 'j9yg-7rg9', 'rdwfilter': 'referentiecode_rdw'},
}

RESOURCE_RECALLINFO = 'https://terugroepregister.rdw.nl/Pages/Terugroepactie.aspx?mgpnummer={}'

TOPIC_DATA_UPDATE = f"{DOMAIN}_data_update"

BINARY_SENSOR_TYPES = {
    'insured': ['Insured', 'mdi:car',      'mdi:alert-outline'],
}

SENSOR_TYPES = {
    'expdate': ['Expdate', 'mdi:calendar', 'mdi:alert-outline'],
    'recall':  ['Recall',  'mdi:wrench',   'mdi:alert-outline'],
}

BINARY_SENSOR_DEFAULTS = [
    "insured",
]

SENSOR_DEFAULTS = [
    "expdate",
    "recall",
]

