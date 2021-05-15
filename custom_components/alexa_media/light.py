"""
Alexa Devices Sensors.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""
import datetime
import logging
from math import sqrt
from typing import (  # noqa pylint: disable=unused-import
    Callable,
    List,
    Optional,
    Text,
    Tuple,
)

from alexapy import AlexaAPI, hide_serial
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
)

try:
    from homeassistant.components.light import (
        COLOR_MODE_BRIGHTNESS,
        COLOR_MODE_COLOR_TEMP,
        COLOR_MODE_HS,
        COLOR_MODE_ONOFF,
    )
except ImportError:
    # Continue to support HA < 2021.4.
    COLOR_MODE_BRIGHTNESS = "brightness"
    COLOR_MODE_COLOR_TEMP = "color_temp"
    COLOR_MODE_HS = "hs"
    COLOR_MODE_ONOFF = "onoff"

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.color import (
    color_hs_to_RGB,
    color_hsb_to_RGB,
    color_name_to_rgb,
    color_RGB_to_hs,
    color_temperature_kelvin_to_mired,
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
    devices: List[LightEntity] = []
    account = config[CONF_EMAIL] if config else discovery_info["config"][CONF_EMAIL]
    account_dict = hass.data[DATA_ALEXAMEDIA]["accounts"][account]
    include_filter = config.get(CONF_INCLUDE_DEVICES, [])
    exclude_filter = config.get(CONF_EXCLUDE_DEVICES, [])
    coordinator = account_dict["coordinator"]
    hue_emulated_enabled = "emulated_hue" in hass.config.as_dict().get(
        "components", set()
    )
    light_entities = account_dict.get("devices", {}).get("light", [])
    if light_entities and account_dict["options"].get(CONF_EXTENDED_ENTITY_DISCOVERY):
        for le in light_entities:
            if not (le["is_hue_v1"] and hue_emulated_enabled):
                _LOGGER.debug(
                    "Creating entity %s for a light with name %s",
                    hide_serial(le["id"]),
                    le["name"],
                )
                light = AlexaLight(coordinator, account_dict["login_obj"], le)
                account_dict["entities"]["light"].append(light)
                devices.append(light)
            else:
                _LOGGER.debug(
                    "Light '%s' has not been added because it may originate from emulated_hue",
                    le["name"],
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


def color_modes(details):
    if details["color"] and details["color_temperature"]:
        return [COLOR_MODE_HS, COLOR_MODE_COLOR_TEMP]
    elif details["color"]:
        return [COLOR_MODE_HS]
    elif details["color_temperature"]:
        return [COLOR_MODE_COLOR_TEMP]
    elif details["brightness"]:
        return [COLOR_MODE_BRIGHTNESS]
    else:
        return [COLOR_MODE_ONOFF]


class AlexaLight(CoordinatorEntity, LightEntity):
    """A light controlled by an Echo."""

    def __init__(self, coordinator, login, details):
        super().__init__(coordinator)
        self.alexa_entity_id = details["id"]
        self._name = details["name"]
        self._login = login
        self._color_modes = color_modes(details)

        # Store the requested state from the last call to _set_state
        # This is so that no new network call is needed just to get values that are already known
        # This is useful because refreshing the full state can take a bit when many lights are in play.
        # Especially since Alexa actually polls the lights and that appears to be error-prone with some Zigbee lights.
        # That delay(1-5s in practice) causes the UI controls to jump all over the place after _set_state
        self._requested_state_at = None  # When was state last set in UTC
        self._requested_power = None
        self._requested_ha_brightness = None
        self._requested_mired = None
        self._requested_hs = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self.alexa_entity_id

    @property
    def supported_features(self):
        # The HA documentation marks every single feature that Alexa lights can support as deprecated.
        # The new alternative is the supported_color_modes and color_mode properties(HA 2021.4)
        # This SHOULD just need to return 0 according to the light entity docs.
        # Actually doing that causes the UI to remove color controls even in HA 2021.4.
        # So, continue to provide a backwards compatible method here until HA is fixed and the min HA version is raised.
        if COLOR_MODE_BRIGHTNESS in self._color_modes:
            return SUPPORT_BRIGHTNESS
        elif (
            COLOR_MODE_HS in self._color_modes
            and COLOR_MODE_COLOR_TEMP in self._color_modes
        ):
            return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_COLOR_TEMP
        elif COLOR_MODE_HS in self._color_modes:
            return SUPPORT_BRIGHTNESS | SUPPORT_COLOR
        elif COLOR_MODE_COLOR_TEMP in self._color_modes:
            return SUPPORT_BRIGHTNESS | SUPPORT_COLOR_TEMP
        else:

            return 0

    @property
    def color_mode(self):
        if (
            COLOR_MODE_HS in self._color_modes
            and COLOR_MODE_COLOR_TEMP in self._color_modes
        ):
            hs = self.hs_color
            if hs is None or (hs[0] == 0 and hs[1] == 0):
                # (0,0) is white. When white, color temp is the better plan.
                return COLOR_MODE_COLOR_TEMP
            else:
                return COLOR_MODE_HS
        else:
            return self._color_modes[0]

    @property
    def supported_color_modes(self):
        return self._color_modes

    @property
    def is_on(self):
        power = parse_power_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if power is None:
            return self._requested_power if self._requested_power is not None else False
        else:
            return power == "ON"

    @property
    def brightness(self):
        bright = parse_brightness_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if bright is None:
            return self._requested_ha_brightness
        else:
            return alexa_brightness_to_ha(bright)

    @property
    def min_mireds(self):
        return 143

    @property
    def max_mireds(self):
        return 454

    @property
    def color_temp(self):
        kelvin = parse_color_temp_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if kelvin is None:
            return self._requested_mired
        else:
            return alexa_kelvin_to_mired(kelvin)

    @property
    def hs_color(self):
        hsb = parse_color_from_coordinator(
            self.coordinator, self.alexa_entity_id, self._requested_state_at
        )
        if hsb is None:
            return self._requested_hs
        else:
            adjusted_hs, color_name = hsb_to_alexa_color(hsb)
            return adjusted_hs

    @property
    def assumed_state(self) -> bool:
        last_refresh_success = (
            self.coordinator.data and self.alexa_entity_id in self.coordinator.data
        )
        return not last_refresh_success

    async def _set_state(self, power_on, brightness=None, mired=None, hs=None):
        # This is "rounding" on mired to the closest value Alexa is willing to acknowledge the existence of.
        # The alternative implementation would be to use effects instead.
        # That is far more non-standard, and would lock users out of things like the Flux integration.
        # The downsides to this approach is that the UI is giving the user a slider
        # When the user picks a slider value, the UI will "jump" to the closest possible value.
        # This trade-off doesn't feel as bad in practice as it sounds.
        adjusted_mired, color_temperature_name = mired_to_alexa(mired)
        if color_temperature_name is None:
            # This is "rounding" on HS color to closest value Alexa supports.
            # The alexa color list is short, but covers a pretty broad spectrum.
            # Like for mired above, this sounds bad but works ok in practice.
            adjusted_hs, color_name = hs_to_alexa_color(hs)
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
        self._requested_mired = (
            adjusted_mired if adjusted_mired is not None else self.color_temp
        )
        if adjusted_hs is not None:
            self._requested_hs = adjusted_hs
        elif adjusted_mired is not None:
            # If a mired value was set, it is critical that color is cleared out so that color mode is set properly
            self._requested_hs = None
        else:
            self._requested_hs = self.hs_color
        self._requested_state_at = (
            datetime.datetime.utcnow()
        )  # must be set last so that previous getters work properly
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        brightness = None
        mired = None
        hs = None
        if COLOR_MODE_ONOFF not in self._color_modes and ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        if COLOR_MODE_COLOR_TEMP in self._color_modes and ATTR_COLOR_TEMP in kwargs:
            mired = kwargs[ATTR_COLOR_TEMP]
        if COLOR_MODE_HS in self._color_modes and ATTR_HS_COLOR in kwargs:
            hs = kwargs[ATTR_HS_COLOR]
        await self._set_state(True, brightness, mired, hs)

    async def async_turn_off(self, **kwargs):
        await self._set_state(False)


def mired_to_alexa(mired: Optional[float]) -> Tuple[Optional[float], Optional[Text]]:
    """Convert a given color temperature in mired to the closest available value that Alexa has support for."""
    if mired is None:
        return None, None
    elif mired <= 162.5:
        return 143, "cool_white"
    elif mired <= 216:
        return 182, "daylight_white"
    elif mired <= 310:
        return 250, "white"
    elif mired <= 412:
        return 370, "soft_white"
    else:
        return 454, "warm_white"


def alexa_kelvin_to_mired(kelvin: float) -> float:
    """Convert a value in kelvin to the closest mired value that Alexa has support for."""
    raw_mired = color_temperature_kelvin_to_mired(kelvin)
    return mired_to_alexa(raw_mired)[0]


def ha_brightness_to_alexa(ha: Optional[float]) -> Optional[float]:
    return (ha / 255 * 100) if ha is not None else None


def alexa_brightness_to_ha(alexa: Optional[float]) -> Optional[float]:
    return (alexa / 100 * 255) if alexa is not None else None


# This is a fairly complete list of all the colors that Alexa will respond to.
# A couple weirder ones are skipped because the HA color utility don't know the RGB value
ALEXA_COLORS = [
    "crimson",
    "dark_red",
    "firebrick",
    "orange_red",
    "red",
    "deep_pink",
    "hot_pink",
    "light_pink",
    "maroon",
    "medium_violet_red",
    "pale_violet_red",
    "pink",
    "plum",
    "tomato",
    "chocolate",
    "dark_orange",
    "maroon",
    "coral",
    "light_coral",
    "light_salmon",
    "peru",
    "salmon",
    "sienna",
    "gold",
    "goldenrod",
    "lime",
    "olive",
    "yellow",
    "chartreuse",
    "dark_green",
    "dark_olive_green",
    "dark_sea_green",
    "forest_green",
    "green",
    "green_yellow",
    "lawn_green",
    "light_green",
    "lime_green",
    "medium_sea_green",
    "medium_spring_green",
    "olive_drab",
    "pale_green",
    "sea_green",
    "spring_green",
    "yellow_green",
    "blue",
    "cadet_blue",
    "cyan",
    "dark_blue",
    "dark_cyan",
    "dark_slate_blue",
    "dark_turquoise",
    "deep_sky_blue",
    "dodger_blue",
    "light_blue",
    "light_sea_green",
    "light_sky_blue",
    "medium_blue",
    "medium_turquoise",
    "midnight_blue",
    "navy_blue",
    "pale_turquoise",
    "powder_blue",
    "royal_blue",
    "sky_blue",
    "slate_blue",
    "steel_blue",
    "teal",
    "turquoise",
    "blue_violet",
    "dark_magenta",
    "dark_orchid",
    "dark_violet",
    "fuchsia",
    "indigo",
    "lavender",
    "magenta",
    "medium_orchid",
    "medium_purple",
    "orchid",
    "purple",
    "rosy_brown",
    "violet",
    "alice_blue",
    "antique_white",
    "blanched_almond",
    "cornsilk",
    "dark_khaki",
    "floral_white",
    "gainsboro",
    "ghost_white",
    "honeydew",
    "ivory",
    "khaki",
    "lavender_blush",
    "lemon_chiffon",
    "light_cyan",
    "light_steel_blue",
    "light_yellow",
    "linen",
    "mint_cream",
    "misty_rose",
    "moccasin",
    "old_lace",
    "pale_goldenrod",
    "papaya_whip",
    "peach_puff",
    "seashell",
    "silver",
    "snow",
    "tan",
    "thistle",
    "wheat",
    "white",
    "white_smoke",
]


def red_mean(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
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


def alexa_color_name_to_rgb(color_name: Text) -> Tuple[int, int, int]:
    """Convert an alexa color name into RGB"""
    return color_name_to_rgb(color_name.replace("_", ""))


def rgb_to_alexa_color(
    rgb: Tuple[int, int, int]
) -> Tuple[Optional[Tuple[float, float]], Optional[Text]]:
    """Convert a given RGB value into the closest Alexa color."""
    name = min(
        ALEXA_COLORS,
        key=lambda color_name: red_mean(rgb, alexa_color_name_to_rgb(color_name)),
    )
    red, green, blue = alexa_color_name_to_rgb(name)
    return color_RGB_to_hs(red, green, blue), name


def hs_to_alexa_color(
    hs: Optional[Tuple[float, float]]
) -> Tuple[Optional[Tuple[float, float]], Optional[Text]]:
    """Convert a given hue/saturation value into the closest Alexa color."""
    if hs is None:
        return None, None
    hue, saturation = hs
    return rgb_to_alexa_color(color_hs_to_RGB(hue, saturation))


def hsb_to_alexa_color(
    hsb: Optional[Tuple[float, float, float]]
) -> Tuple[Optional[Tuple[float, float]], Optional[Text]]:
    """Convert a given hue/saturation/brightness value into the closest Alexa color."""
    if hsb is None:
        return None, None
    hue, saturation, brightness = hsb
    return rgb_to_alexa_color(color_hsb_to_RGB(hue, saturation, brightness))
