"""Track packages from postnord via api"""
from urllib.parse import urlparse
import json
import logging
from datetime import timedelta

import requests

import voluptuous as vol

#from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util.json import load_json, save_json
from homeassistant.util import Throttle
from homeassistant.helpers.entity_component import EntityComponent


_LOGGER = logging.getLogger(__name__)

DOMAIN = "postnord"

REGISTRATIONS_FILE = "postnord.conf"

SERVICE_REGISTER = "register"
SERVICE_UNREGISTER = "unregister"

# Get at https://developer.postnord.com/
ATTR_API_KEY = "api_key"

ICON = "mdi:package-variant-closed"
SCAN_INTERVAL = timedelta(seconds=1800)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_API_KEY): cv.string,
    }
)

ATTR_PACKAGE_ID = "package_id"

SUBSCRIPTION_SCHEMA = vol.All(
    {
        vol.Required(ATTR_PACKAGE_ID): cv.string,
    }
)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

POSTNORD_API_findByIdentifier_URL = "https://api2.postnord.com/rest/shipment/v2/trackandtrace/findByIdentifier.json?apikey={}&id={}"

GROUP_NAME_ALL_POSTNORD_PACKAGES = "all postnord packages"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the postnord sensor"""
    component = hass.data.get(DOMAIN)

    # Use the EntityComponent to track all packages, and create a group of them
    if component is None:
        component = hass.data[DOMAIN] = EntityComponent(_LOGGER, DOMAIN, hass,
                group_name=GROUP_NAME_ALL_POSTNORD_PACKAGES)

    update_interval = config.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL)

    json_path = hass.config.path(REGISTRATIONS_FILE)

    registrations = _load_config(json_path)

    api_key = config.get(ATTR_API_KEY)

    async def async_service_register(service):
        """Handle package registration."""
        package_id = service.data.get(ATTR_PACKAGE_ID).upper()

        if package_id in registrations:
            raise ValueError("Package allready tracked")

        registrations.append(package_id)

        await hass.async_add_job(save_json, json_path, registrations)

        return await component.async_add_entities([
            PostnordSensor(hass, package_id, api_key, update_interval)])

    hass.services.async_register(
        DOMAIN,
        SERVICE_REGISTER,
        async_service_register,
        schema=SUBSCRIPTION_SCHEMA,
    )

    async def async_service_unregister(service):
        """Handle package registration."""
        package_id = service.data.get(ATTR_PACKAGE_ID)

        registrations.remove(package_id)

        await hass.async_add_job(save_json, json_path, registrations)

        entity_id = ENTITY_ID_FORMAT.format(package_id.lower())

        return await component.async_remove_entity(entity_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_UNREGISTER,
        async_service_unregister,
        schema=SUBSCRIPTION_SCHEMA,
    )

    if registrations is None:
        return None

    return await component.async_add_entities([PostnordSensor(hass, package_id, api_key, update_interval) for package_id in registrations], False)


def _load_config(filename):
    """Load configuration."""
    try:
        return load_json(filename, [])
    except HomeAssistantError:
        pass
    return []


class PostnordSensor(RestoreEntity):
    """Postnord Sensor."""

    def __init__(self, hass, package_id, api_key, update_interval):
        """Initialize the sensor."""
        self.hass = hass
        self._package_id = package_id
        self._api_key = api_key
        self._attributes = None
        self._state = None
        self._data = None
        self.update = Throttle(update_interval)(self._update)

    @property
    def entity_id(self):
        """Return the entity_id of the sensor"""
        return ENTITY_ID_FORMAT.format(self._package_id.lower())

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Package {}".format(self._package_id)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON

    def _update(self):
        """Update sensor state."""
        response = requests.get(POSTNORD_API_findByIdentifier_URL.format(self._api_key,
            self._package_id), timeout=10)

        if response.status_code != 200:
            _LOGGER.error("API returned {}".format(response.status_code))
            return

        response = response.json()

        if "TrackingInformationResponse" not in response or "shipments" not in response["TrackingInformationResponse"]:
            _LOGGER.error("API returned unknown json structure")
            return

        for shipment in response["TrackingInformationResponse"]["shipments"]:
            if shipment["shipmentId"] == self._package_id:
                # Found the right shipment
                self._state = shipment.get("status", STATE_UNKNOWN)
                self._attributes = {}
                self._attributes["from"] = shipment.get("consignor", {}).get("name", STATE_UNKNOWN)
                self._attributes["status"] = shipment.get("statusText", {}).get("header", STATE_UNKNOWN)
                self._attributes["type"] = shipment.get("service", {}).get("name", STATE_UNKNOWN)

            else:
                _LOGGER.info("Found other shipmentId {}".format(shipment["shipmentId"]))

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        if self._state is not None:
            return

        state = await self.async_get_last_state()
        self._state = state and state.state
        self._attributes = state and state.attributes
