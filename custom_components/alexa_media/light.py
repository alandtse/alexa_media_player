"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import datetime
import logging
from math import sqrt
from typing import Optional

from alexapy import AlexaAPI, hide_serial
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.color import (
    color_hs_to_RGB,
    color_hsb_to_RGB,
    color_name_to_rgb,
    color_RGB_to_hs,
)

from . import (
    CONF_EMAIL,
    CONF_EXCLUDE_DEVICES,
    CONF_INCLUDE_DEVICES,
    DATA_ALEXAMEDIA,
    hide_email,
)
from .alexa_entity import (
    parse_brightness_from_coordinator,
    parse_color_from_coordinator,
    parse_color_temp_from_coordinator,
    parse_power_from_coordinator,
)
from .const import CONF_EXTENDED_ENTITY_DISCOVERY
from .helpers import add_devices

_LOGGER = logging.getLogger(__name__)

LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


async def async_setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Alexa sensor platform."""
    devices: list[LightEntity] = []
    account = None
    if config:
        account = config.get(CONF_EMAIL)
    if account is None and discovery_info:
        account = discovery_info.get("config", {}).get(CONF_EMAIL)
    if account is None:
        raise ConfigEntryNotReady
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    hue_emulated_enabled = "emulated_hue" in hass.config.as_dict().get(
        "components", set()
    )
    light_entities = account_dict.get("devices", {}).get("light", [])
    if light_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for light_entity in light_entities:
            if not (light_entity["is_hue_v1"] and hue_emulated_enabled):
                _LOGGER.debug(
                    "Creating entity %s for a light with name %s",
                    hide_serial(light_entity["id"]),
                    light_entity["name"],
                )
                light = AlexaLight(coordinator, account_dict["login_obj"], light_entity)
                account_dict["entities"]["light"].append(light)
                devices.append(light)
            else:
                _LOGGER.debug(
                    "Light '%s' has not been added because it may originate from emulated_hue",
                    light_entity["name"],
                )

    return await add_devices(
        hide_email(account),
        devices,
        add_devices_callback,
        include_filter,
        exclude_filter,
    )


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Alexa sensor platform by config_entry."""
    return await async_setup_platform(
        hass, config_entry.data, async_add_devices, discovery_info=None
    )


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""
    account = entry.data[CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    _LOGGER.debug("Attempting to unload lights")
    for light in account_dict["entities"]["light"]:
        await light.async_remove()
    return True


def color_modes(details) -> list:
    """Return list of color modes."""
    if details["color"] and details["color_temperature"]:
        return [ColorMode.HS, ColorMode.COLOR_TEMP]
    if details["color"]:
        return [ColorMode.HS]
    if details["color_temperature"]:
        return [ColorMode.COLOR_TEMP]
    if details["brightness"]:
        return [ColorMode.BRIGHTNESS]
    return [ColorMode.ONOFF]


class AlexaLight(CoordinatorEntity, LightEntity):
    """A light controlled by an Echo."""

    def __init__(self, coordinator, login, details):
        """Initialize alexa light entity."""
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]
        self._login = login
        self._attr_supported_color_modes = color_modes(details)
        self._attr_min_color_temp_kelvin = 2200
        self._attr_max_color_temp_kelvin = 6500

        # Store the requested state from the last call to _set_state
        # This is so that no new network call is needed just to get values that are already known
        # This is useful because refreshing the full state can take a bit when many lights are in play.
        # Especially since Alexa actually polls the lights and that appears to be error-prone with some Zigbee lights.
        # That delay(1-5s in practice) causes the UI controls to jump all over the place after _set_state
        self._requested_state_at = None  # When was state last set in UTC
        self._requested_power = None
        self._requested_ha_brightness = None
        self._requested_kelvin = None
        self._requested_hs = None

    @property
    def name(self):
        """Return name."""
        return self._name

    @property
    def unique_id(self):
        """Return unique id."""
        return self.alexa_entity_id

    @property
    def color_mode(self):
        """Return color mode."""
        if (
            ColorMode.HS in self._attr_supported_color_modes
            and ColorMode.COLOR_TEMP in self._attr_supported_color_modes
        ):
            hs_color = self.hs_color
            if hs_color is None or (hs_color[0] == 0 and hs_color[1] == 0):
                # (0,0) is white. When white, color temp is the better plan.
                return ColorMode.COLOR_TEMP
            return ColorMode.HS
        return self._attr_supported_color_modes[0]

    @property
    def is_on(self):
        """Return whether on."""
        power = parse_power_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if power is None:
            return self._requested_power if self._requested_power is not None else False
        return power == "ON"

    @property
    def brightness(self):
        """Return brightness."""
        bright = parse_brightness_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if bright is None:
            return self._requested_ha_brightness
        return alexa_brightness_to_ha(bright)

    @property
    def color_temp_kelvin(self):
        """Return color temperature."""
        kelvin = parse_color_temp_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if kelvin is None:
            return self._requested_kelvin
        return kelvin_to_alexa(kelvin)[0]

    @property
    def hs_color(self):
        """Return hs color."""
        hsb = parse_color_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if hsb is None:
            return self._requested_hs
        (
            adjusted_hs,
            color_name,  # pylint:disable=unused-variable
        ) = hsb_to_alexa_color(hsb)
        return adjusted_hs

    @property
    def assumed_state(self) -> bool:
        """Return whether state is assumed."""
        last_refresh_success = (
            self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        )
        return not last_refresh_success

    async def _set_state(self, power_on, brightness=None, kelvin=None, hs_color=None):
        # This is "rounding" on kelvin to the closest value Alexa is willing to acknowledge the existence of.
        # The alternative implementation would be to use effects instead.
        # That is far more non-standard, and would lock users out of things like the Flux integration.
        # The downsides to this approach is that the UI is giving the user a slider
        # When the user picks a slider value, the UI will "jump" to the closest possible value.
        # This trade-off doesn't feel as bad in practice as it sounds.
        adjusted_kelvin, color_temperature_name = kelvin_to_alexa(kelvin)
        if color_temperature_name is None:
            # This is "rounding" on HS color to closest value Alexa supports.
            # The alexa color list is short, but covers a pretty broad spectrum.
            # Like for kelvin above, this sounds bad but works ok in practice.
            adjusted_hs, color_name = hs_to_alexa_color(hs_color)
        else:
            # If a color temperature is being set, it is not possible to also adjust the color.
            adjusted_hs = None
            color_name = None

        response = await AlexaAPI.set_light_state(
            self._login,
            self.alexa_entity_id,
            power_on,
            brightness=ha_brightness_to_alexa(brightness),
            color_temperature_name=color_temperature_name,
            color_name=color_name,
        )
        control_responses = response.get("controlResponses", [])
        for response in control_responses:
            if not response.get("code") == "SUCCESS":
                # If something failed any state is possible, fallback to a full refresh
                return await self.coordinator.async_request_refresh()
        self._requested_power = power_on
        self._requested_ha_brightness = (
            brightness if brightness is not None else self.brightness
        )
        self._requested_kelvin = (
            adjusted_kelvin if adjusted_kelvin is not None else self.color_temp
        )
        if adjusted_hs is not None:
            self._requested_hs = adjusted_hs
        elif adjusted_kelvin is not None:
            # If a kelvin value was set, it is critical that color is cleared out so that color mode is set properly
            self._requested_hs = None
        else:
            self._requested_hs = self.hs_color
        self._requested_state_at = datetime.datetime.now(
            datetime.timezone.utc
        )  # must be set last so that previous getters work properly
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on."""
        brightness = None
        kelvin = None
        hs_color = None
        if (
            ColorMode.ONOFF not in self._attr_supported_color_modes
            and ATTR_BRIGHTNESS in kwargs
        ):
            brightness = kwargs[ATTR_BRIGHTNESS]
        if (
            ColorMode.COLOR_TEMP in self._attr_supported_color_modes
            and ATTR_COLOR_TEMP_KELVIN in kwargs
        ):
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
        if ColorMode.HS in self._attr_supported_color_modes and ATTR_HS_COLOR in kwargs:
            hs_color = kwargs[ATTR_HS_COLOR]
        await self._set_state(True, brightness, kelvin, hs_color)

    async def async_turn_off(self, **kwargs):  # pylint:disable=unused-argument
        """Turn off."""
        await self._set_state(False)


def kelvin_to_alexa(kelvin: Optional[float]) -> tuple[Optional[float], Optional[str]]:
    """Convert a given color temperature in kelvin to the closest available value that Alexa has support for."""
    if kelvin is None:
        return None, None
    if kelvin <= 2400:
        return 2200, "warm_white"
    if kelvin <= 3200:
        return 2700, "soft_white"
    if kelvin <= 4400:
        return 4000, "white"
    if kelvin <= 6000:
        return 5400, "daylight_white"
    return 6500, "cool_white"


def ha_brightness_to_alexa(ha_brightness: Optional[float]) -> Optional[float]:
    """Convert HA brightness to alexa brightness."""
    return (ha_brightness / 255 * 100) if ha_brightness is not None else None


def alexa_brightness_to_ha(alexa: Optional[float]) -> Optional[float]:
    """Convert Alexa brightness to HA brightness."""
    return (alexa / 100 * 255) if alexa is not None else None


# This is a fairly complete list of all the colors that Alexa will respond to and their associated RGB value.
ALEXA_COLORS = {
    "alice_blue": (240, 248, 255),
    "antique_white": (250, 235, 215),
    "aqua": (0, 255, 255),
    "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "black": (0, 0, 0),
    "blanched_almond": (255, 235, 205),
    "blue": (0, 0, 255),
    "blue_violet": (138, 43, 226),
    "brown": (165, 42, 42),
    "burlywood": (222, 184, 135),
    "cadet_blue": (95, 158, 160),
    "chartreuse": (127, 255, 0),
    "chocolate": (210, 105, 30),
    "coral": (255, 127, 80),
    "cornflower_blue": (100, 149, 237),
    "cornsilk": (255, 248, 220),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "dark_blue": (0, 0, 139),
    "dark_cyan": (0, 139, 139),
    "dark_goldenrod": (184, 134, 11),
    "dark_green": (0, 100, 0),
    "dark_grey": (169, 169, 169),
    "dark_khaki": (189, 183, 107),
    "dark_magenta": (139, 0, 139),
    "dark_olive_green": (85, 107, 47),
    "dark_orange": (255, 140, 0),
    "dark_orchid": (153, 50, 204),
    "dark_red": (139, 0, 0),
    "dark_salmon": (233, 150, 122),
    "dark_sea_green": (143, 188, 143),
    "dark_slate_blue": (72, 61, 139),
    "dark_slate_grey": (47, 79, 79),
    "dark_turquoise": (0, 206, 209),
    "dark_violet": (148, 0, 211),
    "deep_pink": (255, 20, 147),
    "deep_sky_blue": (0, 191, 255),
    "dim_grey": (105, 105, 105),
    "dodger_blue": (30, 144, 255),
    "firebrick": (178, 34, 34),
    "floral_white": (255, 250, 240),
    "forest_green": (34, 139, 34),
    "fuchsia": (255, 0, 255),
    "gainsboro": (220, 220, 220),
    "ghost_white": (248, 248, 255),
    "gold": (255, 215, 0),
    "goldenrod": (218, 165, 32),
    "green": (0, 128, 0),
    "green_yellow": (173, 255, 47),
    "grey": (128, 128, 128),
    "honey_dew": (240, 255, 240),
    "hot_pink": (255, 105, 180),
    "indian_red": (205, 92, 92),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lavender_blush": (255, 240, 245),
    "lawn_green": (124, 252, 0),
    "lemon_chiffon": (255, 250, 205),
    "light_blue": (173, 216, 230),
    "light_coral": (240, 128, 128),
    "light_cyan": (224, 255, 255),
    "light_goldenrod_yellow": (250, 250, 210),
    "light_green": (144, 238, 144),
    "light_grey": (211, 211, 211),
    "light_pink": (255, 182, 193),
    "light_salmon": (255, 160, 122),
    "light_sea_green": (32, 178, 170),
    "light_sky_blue": (135, 206, 250),
    "light_slate_grey": (119, 136, 153),
    "light_steel_blue": (176, 196, 222),
    "light_yellow": (255, 255, 224),
    "lime": (0, 255, 0),
    "lime_green": (50, 205, 50),
    "linen": (250, 240, 230),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "medium_aqua_marine": (102, 205, 170),
    "medium_blue": (0, 0, 205),
    "medium_orchid": (186, 85, 211),
    "medium_purple": (147, 112, 219),
    "medium_sea_green": (60, 179, 113),
    "medium_slate_blue": (123, 104, 238),
    "medium_spring_green": (0, 250, 154),
    "medium_turquoise": (72, 209, 204),
    "medium_violet_red": (199, 21, 133),
    "midnight_blue": (25, 25, 112),
    "mint_cream": (245, 255, 250),
    "misty_rose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajo_white": (255, 222, 173),
    "navy": (0, 0, 128),
    "old_lace": (253, 245, 230),
    "olive": (128, 128, 0),
    "olive_drab": (107, 142, 35),
    "orange": (255, 165, 0),
    "orange_red": (255, 69, 0),
    "orchid": (218, 112, 214),
    "pale_goldenrod": (238, 232, 170),
    "pale_green": (152, 251, 152),
    "pale_turquoise": (175, 238, 238),
    "pale_violet_red": (219, 112, 147),
    "papaya_whip": (255, 239, 213),
    "peach_puff": (255, 218, 185),
    "peru": (205, 133, 63),
    "pink": (255, 192, 203),
    "plum": (221, 160, 221),
    "powder_blue": (176, 224, 230),
    "purple": (128, 0, 128),
    "rebecca_purple": (102, 51, 153),
    "red": (255, 0, 0),
    "rosy_brown": (188, 143, 143),
    "royal_blue": (65, 105, 225),
    "saddle_brown": (139, 69, 19),
    "salmon": (250, 128, 114),
    "sandy_brown": (244, 164, 96),
    "sea_green": (46, 139, 87),
    "sea_shell": (255, 245, 238),
    "sienna": (160, 82, 45),
    "silver": (192, 192, 192),
    "sky_blue": (135, 206, 235),
    "slate_blue": (106, 90, 205),
    "slate_grey": (112, 128, 144),
    "snow": (255, 250, 250),
    "spring_green": (0, 255, 127),
    "steel_blue": (70, 130, 180),
    "tan": (210, 180, 140),
    "teal": (0, 128, 128),
    "thistle": (216, 191, 216),
    "tomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet": (238, 130, 238),
    "wheat": (245, 222, 179),
    "white": (255, 255, 255),
    "white_smoke": (245, 245, 245),
    "yellow": (255, 255, 0),
    "yellow_green": (154, 205, 50),
}


def red_mean(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """Get an approximate 'distance' between two colors using red mean.

    Wikipedia says this method is "one of the better low-cost approximations".
    """
    r_avg = (color2[0] + color1[0]) / 2
    r_delta = color2[0] - color1[0]
    g_delta = color2[1] - color1[1]
    b_delta = color2[2] - color1[2]
    r_term = (2 + r_avg / 256) * pow(r_delta, 2)
    g_term = 4 * pow(g_delta, 2)
    b_term = (2 + (255 - r_avg) / 256) * pow(b_delta, 2)
    return sqrt(r_term + g_term + b_term)


def alexa_color_name_to_rgb(color_name: str) -> tuple[int, int, int]:
    """Convert an alexa color name into RGB."""
    return color_name_to_rgb(color_name.replace("_", ""))


def rgb_to_alexa_color(
    rgb: tuple[int, int, int],
) -> tuple[Optional[tuple[float, float]], Optional[str]]:
    """Convert a given RGB value into the closest Alexa color."""
    (name, alexa_rgb) = min(
        ALEXA_COLORS.items(),
        key=lambda alexa_color: red_mean(alexa_color[1], rgb),
    )
    red, green, blue = alexa_rgb
    return color_RGB_to_hs(red, green, blue), name


def hs_to_alexa_color(
    hs_color: Optional[tuple[float, float]],
) -> tuple[Optional[tuple[float, float]], Optional[str]]:
    """Convert a given hue/saturation value into the closest Alexa color."""
    if hs_color is None:
        return None, None
    hue, saturation = hs_color
    return rgb_to_alexa_color(color_hs_to_RGB(hue, saturation))


def hsb_to_alexa_color(
    hsb: Optional[tuple[float, float, float]],
) -> tuple[Optional[tuple[float, float]], Optional[str]]:
    """Convert a given hue/saturation/brightness value into the closest Alexa color."""
    if hsb is None:
        return None, None
    hue, saturation, brightness = hsb
    return rgb_to_alexa_color(color_hsb_to_RGB(hue, saturation, brightness))
