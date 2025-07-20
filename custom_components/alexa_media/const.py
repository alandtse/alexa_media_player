"""
Support to interface with Alexa Devices.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

from datetime import timedelta

from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
)

__version__ = "5.7.5"
PROJECT_URL = "https://github.com/alandtse/alexa_media_player/"
ISSUE_URL = f"{PROJECT_URL}issues"
NOTIFY_URL = f"{PROJECT_URL}wiki/Configuration%3A-Notification-Component#use-the-notifyalexa_media-service"

DOMAIN = "alexa_media"
DATA_ALEXAMEDIA = "alexa_media"

PLAY_SCAN_INTERVAL = 20
SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = SCAN_INTERVAL
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

ALEXA_COMPONENTS = [
    "media_player",
]
DEPENDENT_ALEXA_COMPONENTS = [
    "notify",
    "switch",
    "sensor",
    "alarm_control_panel",
    "light",
    "binary_sensor",
]

HTTP_COOKIE_HEADER = "# HTTP Cookie File"
CONF_ACCOUNTS = "accounts"
CONF_DEBUG = "debug"
CONF_HASS_URL = "hass_url"
CONF_INCLUDE_DEVICES = "include_devices"
CONF_EXCLUDE_DEVICES = "exclude_devices"
CONF_QUEUE_DELAY = "queue_delay"
CONF_PUBLIC_URL = "public_url"
CONF_EXTENDED_ENTITY_DISCOVERY = "extended_entity_discovery"
CONF_SECURITYCODE = "securitycode"
CONF_OTPSECRET = "otp_secret"
CONF_PROXY = "proxy"
CONF_PROXY_WARNING = "proxy_warning"
CONF_TOTP_REGISTER = "registered"
CONF_OAUTH = "oauth"
DATA_LISTENER = "listener"

EXCEPTION_TEMPLATE = "An exception of type {0} occurred. Arguments:\n{1!r}"

DEFAULT_DEBUG = False
DEFAULT_EXTENDED_ENTITY_DISCOVERY = False
DEFAULT_HASS_URL = "http://homeassistant.local:8123"
DEFAULT_PUBLIC_URL = ""
DEFAULT_QUEUE_DELAY = 1.5
DEFAULT_SCAN_INTERVAL = 60

SERVICE_UPDATE_LAST_CALLED = "update_last_called"
SERVICE_RESTORE_VOLUME = "restore_volume"
SERVICE_GET_HISTORY_RECORDS = "get_history_records"
SERVICE_FORCE_LOGOUT = "force_logout"

RECURRING_PATTERN = {
    None: "Never Repeat",
    "P1D": "Every day",
    "P1M": "Every month",
    "XXXX-WE": "Weekends",
    "XXXX-WD": "Weekdays",
    "XXXX-WXX-1": "Every Monday",
    "XXXX-WXX-2": "Every Tuesday",
    "XXXX-WXX-3": "Every Wednesday",
    "XXXX-WXX-4": "Every Thursday",
    "XXXX-WXX-5": "Every Friday",
    "XXXX-WXX-6": "Every Saturday",
    "XXXX-WXX-7": "Every Sunday",
}

RECURRING_DAY = {
    "MO": 1,
    "TU": 2,
    "WE": 3,
    "TH": 4,
    "FR": 5,
    "SA": 6,
    "SU": 7,
}
RECURRING_PATTERN_ISO_SET = {
    None: {},
    "P1D": {1, 2, 3, 4, 5, 6, 7},
    "XXXX-WE": {6, 7},
    "XXXX-WD": {1, 2, 3, 4, 5},
    "XXXX-WXX-1": {1},
    "XXXX-WXX-2": {2},
    "XXXX-WXX-3": {3},
    "XXXX-WXX-4": {4},
    "XXXX-WXX-5": {5},
    "XXXX-WXX-6": {6},
    "XXXX-WXX-7": {7},
}

ATTR_MESSAGE = "message"
ATTR_EMAIL = "email"
ATTR_NUM_ENTRIES = "entries"
STREAMING_ERROR_MESSAGE = (
    "Sorry, direct music streaming isn't supported. "
    "This limitation is set by Amazon, and not by Alexa-Media-Player, Music-Assistant, nor Home-Assistant."
)
PUBLIC_URL_ERROR_MESSAGE = (
    "To send TTS, please set the public URL in integration configuration."
)
STARTUP = f"""
-------------------------------------------------------------------
{DOMAIN}
Version: {__version__}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

AUTH_CALLBACK_PATH = "/auth/alexamedia/callback"
AUTH_CALLBACK_NAME = "auth:alexamedia:callback"
AUTH_PROXY_PATH = "/auth/alexamedia/proxy"
AUTH_PROXY_NAME = "auth:alexamedia:proxy"

ALEXA_UNIT_CONVERSION = {
    "Alexa.Unit.Percent": PERCENTAGE,
    "Alexa.Unit.PartsPerMillion": CONCENTRATION_PARTS_PER_MILLION,
    "Alexa.Unit.Density.MicroGramsPerCubicMeter": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
}

ALEXA_ICON_CONVERSION = {
    "Alexa.AirQuality.CarbonMonoxide": "mdi:molecule-co",
    "Alexa.AirQuality.Humidity": "mdi:water-percent",
    "Alexa.AirQuality.IndoorAirQuality": "mdi:numeric",
}
ALEXA_ICON_DEFAULT = "mdi:molecule"

UPLOAD_PATH = "www/alexa_tts"

# Note: Some of these are likely wrong
MODEL_IDS = {
    "A10A33FOX2NUBK": "Echo Spot (Gen1)",
    "A10L5JEZTKKCZ8": "Vobot Bunny",
    "A11QM4H9HGV71H": "Echo Show 5 (Gen3)",
    "A12GXV8XMS007S": "Fire TV (Gen1)",
    "A12IZU8NMHSY5U": "Generic Device",
    "A132LT22WVG6X5": "Samsung Soundbar Q700A",
    "A13B2WB920IZ7X": "Samsung HW-Q70T Soundbar",
    "A13W6HQIHKEN3Z": "Echo Auto",
    "A14ZH95E6SE9Z1": "Bose Home Speaker 300",
    "A15996VY63BQ2D": "Echo Show 8 (Gen2)",
    "A15ERDAKK5HQQG": "Sonos",
    "A15QWUTQ6FSMYX": "Echo Buds (Gen2)",
    "A16MZVIFVHX6P6": "Generic Echo",
    "A17LGWINFBUTZZ": "Anker Roav Viva",
    "A18BI6KPKDOEI4": "Ecobee4",
    "A18O6U1UQFJ0XK": "Echo Plus (Gen2)",
    "A18TCD9FP10WJ9": "Orbi Voice",
    "A18X8OBWBCSLD8": "Samsung Soundbar",
    "A195TXHV1M5D4A": "Echo Auto",
    "A1C66CX2XD756O": "Fire Tablet HD",
    "A1EIANJ7PNB0Q7": "Echo Show 15 (Gen1)",
    "A1ENT81UXFMNNO": "Unknown",
    "A1ETW4IXK2PYBP": "Talk to Alexa",
    "A1F1F76XIW4DHQ": "Unknown TV",
    "A1F8D55J0FWDTN": "Fire TV (Toshiba)",
    "A1H0CMF1XM0ZP4": "Bose SoundTouch 30",
    "A1J16TEDOYCZTN": "Fire Tablet",
    "A1JJ0KFC4ZPNJ3": "Echo Input",
    "A1L4KDRIILU6N9": "Sony Speaker",
    "A1LOQ8ZHF4G510": "Samsung Soundbar Q990B",
    "A1M0A9L9HDBID3": "One-Link Safe and Sound",
    "A1MUORL8FP149X": "Unknown",
    "A1N9SW0I0LUX5Y": "Ford/Lincoln Alexa App",
    "A1NL4BVLQ4L3N3": "Echo Show (Gen1)",
    "A1NQ0LXWBGVQS9": "2021 Samsung QLED TV",
    "A1P31Q3MOWSHOD": "Zolo Halo Speaker",
    "A1P7E7V3FCZKU6": "Fire TV (Gen3)",
    "A1Q69AKRWLJC0F": "TV",
    "A1Q7QCGNMXAKYW": "Generic Tablet",
    "A1QKZ9D0IJY332": "Samsung TV 2020-U",
    "A1RABVCI4QCIKC": "Echo Dot (Gen3)",
    "A1RTAM01W29CUP": "Windows App",
    "A1SCI5MODUBAT1": "Pioneer DMH-W466NEX",
    "A1TD5Z1R8IWBHA": "Tablet",
    "A1VGB7MHSIEYFK": "Fire TV Cube Gen3",
    "A1W2YILXTG9HA7": "Nextbase 522GW Dashcam",
    "A1W46V57KES4B5": "Cable TV box Brazil",
    "A1WZKXFLI43K86": "Fire TV Stick MAX",
    "A1XWJRHALS1REP": "Echo Show 5 (Gen2)",
    "A1Z88NGR2BK6A2": "Echo Show 8 (Gen1)",
    "A25EC4GIHFOCSG": "Unrecognized Media Player",
    "A25OJWHZA1MWNB": "2021 Samsung QLED TV",
    "A265XOI9586NML": "Fire TV Stick",
    "A27VEYGQBW3YR5": "Echo Link",
    "A2A3XFQ1AVYLHZ": "SONY WF-1000XM5",
    "A2BRQDVMSZD13S": "SURE Universal Remote",
    "A2C8J6UHV0KFCV": "Alexa Gear",
    "A2DS1Q2TPDJ48U": "Echo Dot Clock (Gen5)",
    "A2E0SNTXJVT7WK": "Fire TV (Gen2)",
    "A2E5N6DMWCW8MZ": "Brilliant Smart Switch",
    "A2EZ3TS0L1S2KV": "Sonos Beam",
    "A2GFL5ZMWNE0PX": "Fire TV (Gen3)",
    "A2H4LV5GIZ1JFT": "Echo Dot Clock (Gen4)",
    "A2HZENIFNYTXZD": "Facebook Portal",
    "A2I0SCCU3561Y8": "Samsung Soundbar Q800A",
    "A2IS7199CJBT71": "TV",
    "A2IVLV5VM2W81": "Alexa Mobile Voice iOS",
    "A2J0R2SD7G9LPA": "Lenovo SmartTab M10",
    "A2JKHJ0PX4J3L3": "Fire TV Cube (Gen2)",
    "A2LH725P8DQR2A": "Fabriq Riff",
    "A2LWARUGJLBYEW": "Fire TV Stick (Gen2)",
    "A2M35JJZWCQOMZ": "Echo Plus (Gen1)",
    "A2M4YX06LWP8WI": "Fire Tablet",
    "A2N49KXGVA18AR": "Fire Tablet HD 10 Plus",
    "A2OSP3UA4VC85F": "Sonos",
    "A2R2GLZH1DFYQO": "Zolo Halo Speaker",
    "A2RU4B77X9R9NZ": "Echo Link Amp",
    "A2TF17PFR55MTB": "Alexa Mobile Voice Android",
    "A2TTLILJHVNI9X": "LG TV",
    "A2U21SRK4QGSE1": "Echo Dot Clock (Gen4)",
    "A2UONLFQW0PADH": "Echo Show 8 (Gen3)",
    "A2V9UEGZ82H4KZ": "Fire Tablet HD 10",
    "A2VAXZ7UNGY4ZH": "Wyze Headphones",
    "A2WFDCBDEXOXR8": "Bose Soundbar 700",
    "A2WJ2CM9ARLMRH": "Rivian Electric Vehicle",
    "A2WN1FJ2HG09UN": "Ultimate Alexa App",
    "A2X8WT9JELC577": "Ecobee5",
    "A2XPGY5LRKB9BE": "Fitbit Versa 2",
    "A2Y04QPFCANLPQ": "Bose QuietComfort 35 II",
    "A303PJF6ISQ7IC": "Echo Auto",
    "A30YDR2MK8HMRV": "Echo (Gen3)",
    "A31DTMEEVDDOIV": "Fire TV Stick Lite",
    "A324YMIUSWQDGE": "Samsung 8K TV",
    "A32DDESGESSHZA": "Echo Dot (Gen3)",
    "A32DOYMUN6DTXA": "Echo Dot (Gen3)",
    "A339L426Y220I4": "Teufel Radio",
    "A347G2JC8I4HC7": "Roav Car Charger Pro",
    "A37CFAHI1O0CXT": "Logitech Blast",
    "A37M7RU8Z6ZFB": "Garmin Speak",
    "A37SHHQ3NUL7B5": "Bose Home Speaker 500",
    "A38949IHXHRQ5P": "Echo Tap",
    "A38BPK7OW001EX": "Raspberry Alexa",
    "A38EHHIB10L47V": "Fire Tablet HD 8",
    "A39BU42XNMN516": "Generic Device",
    "A3B50IC5QPZPWP": "Polk Command Bar",
    "A3B5K1G3EITBIF": "Facebook Portal",
    "A3BRT6REMPQWA8": "Bose Home Speaker 450",
    "A3BW5ZVFHRCQPO": "BMW Alexa Integration",
    "A3C9PE6TNYLTCH": "Speaker Group",
    "A3CY98NH016S5F": "Facebook Portal Mini",
    "A3D4YURNTARP5K": "Facebook Portal TV",
    "A3EH2E0YZ30OD6": "Echo Spot (Gen2)",
    "A3EVMLQTU6WL1W": "Fire TV (GenX)",
    "A3F1S88NTZZXS9": "Dash Wand",
    "A3FX4UWTP28V1P": "Echo (Gen3)",
    "A3GFRGUNIGG1I5": "Samsung TV QN50Q60CAGXZD",
    "A3HF4YRA2L7XGC": "Fire TV Cube",
    "A3IYPH06PH1HRA": "Echo Frames",
    "A3K69RS3EIMXPI": "Hisense Smart TV",
    "A3KULB3NQN7Z1F": "Unknown TV",
    "A3L0T0VL9A921N": "Fire Tablet HD 8",
    "A3NPD82ABCPIDP": "Sonos Beam",
    "A3QPPX1R9W5RJV": "Fabriq Chorus",
    "A3QS1XP2U6UJX9": "SONY WF-1000XM4",
    "A3R9S4ZZECZ6YL": "Fire Tablet HD 10",
    "A3RBAYBE7VM004": "Echo Studio",
    "A3RCTOK2V0A4ZG": "LG TV",
    "A3RMGO6LYLH7YN": "Echo Dot (Gen4)",
    "A3S5BH2HU6VAYF": "Echo Dot (Gen2)",
    "A3SSG6GR8UU7SN": "Echo Sub",
    "A3SSWQ04XYPXBH": "Generic Tablet",
    "A3TCJ8RTT3NVI7": "Alexa Listens",
    "A3VRME03NAXFUB": "Echo Flex",
    "A4ZP7ZC4PI6TO": "Echo Show 5 (Gen1)",
    "A4ZXE0RM7LQ7A": "Echo Dot (Gen5)",
    "A52ARKF0HM2T4": "Facebook Portal+",
    "A6SIQKETF3L2E": "Unknown Device",
    "A7WXQPH584YP": "Echo (Gen2)",
    "A81PNL0A63P93": "Home Remote",
    "A8DM4FYR6D3HT": "TV",
    "AA1IN44SS3X6O": "Ecobee Thermostat Premium",
    "AB72C64C86AW2": "Echo (Gen1)",
    "ABJ2EHL7HQT4L": "Unknown Amplifier",
    "ADVBD696BHNV5": "Fire TV Stick (Gen1)",
    "AE7X7Z227NFNS": "HiMirror Mini",
    "AF473ZSOIRKFJ": "Onkyo VC-PX30",
    "AFF50AL5E3DIU": "Fire TV (Insignia)",
    "AFF5OAL5E3DIU": "Fire TV",
    "AGHZIK8D6X7QR": "Fire TV",
    "AHJYKVA63YCAQ": "Sonos",
    "AIPK7MM90V7TB": "Echo Show 10 (Gen3)",
    "AKKLQD9FZWWQS": "Jabra Elite",
    "AKNO1N0KSFN8L": "Echo Dot (Gen1)",
    "AKO51L5QAQKL2": "Alexa Jams",
    "AKPGW064GI9HE": "Fire TV Stick 4K (Gen3)",
    "ALCIV0P5M8TZ0": "Samsung Soundbar S800B",
    "ALT9P69K6LORD": "Echo Auto",
    "AMCZ48H33RCDF": "Samsung HW-Q910B 9.1.2 ch Soundbar",
    "AN630UQPG2CA4": "Fire TV (Toshiba)",
    "AO6HHP9UE6EOF": "Unknown Media Device",
    "AP1F6KUH00XPV": "Stereo/Subwoofer Pair",
    "AP4RS91ZQ0OOI": "Fire TV (Toshiba)",
    "APHEAY6LX7T13": "Samsung Smart Refrigerator",
    "AQCGW9PSYWRF": "TV",
    "AR6X0XNIME80V": "Unknown TV",
    "ASQZWP4GPYUT7": "Echo Pop",
    "ATNLRCEBX3W4P": "Generic Tablet",
    "AUPUQSVCVHXP0": "Ecobee Switch+",
    "AVD3HM0HOJAAL": "Sonos",
    "AVE5HX13UR5NO": "Logitech Zero Touch",
    "AVN2TMX8MU2YM": "Bose Home Speaker 500",
    "AVU7CPPF2ZRAS": "Fire Tablet HD 8",
    "AWZZ5CVHX2CD": "Echo Show (Gen2)",
}
