"""
Support for Xiaomi AirFryer.

"""
import enum
import re
from typing import Any, Dict
import logging
import click

from miio.click_common import command, format_output
from miio.device import DeviceStatus
from miio.miot_device import MiotDevice
from .const import (
    MODEL_FRYER_534,
    MODEL_FRYER_MAF01,
    MODEL_FRYER_MAF02,
    MODEL_FRYER_MAF03,
    MODEL_FRYER_MAF05A,
    MODEL_FRYER_MAF06,
    MODEL_FRYER_MAF06A,
    MODEL_FRYER_MAF06B,
    MODEL_FRYER_MAF07,
    MODEL_FRYER_MAF07C,
    MODEL_FRYER_MAF07D,
    MODEL_FRYER_MAF09A,
    MODEL_FRYER_MAF10,
    MODEL_FRYER_MAF10A,
    MODEL_FRYER_MAF14,
    MODEL_FRYER_MAF15,
    MODEL_FRYER_MAF16,
    MODEL_FRYER_MAF65,
    MODEL_FRYER_SCK501,
    MODEL_FRYER_SCK505,
    MODEL_FRYER_V3,
    MODEL_FRYER_YBAF01,
    MODEL_FRYER_YBAF02,
    MODEL_FRYER_YBAF03,
    MODEL_FRYER_YBAF04
)

_LOGGER = logging.getLogger(__name__)


def slugify_state(name):
    """Turn an enum member name into a valid Home Assistant state key.

    Translation keys have to match [a-z0-9-_]+, so "NotTurnPot" cannot be used
    as a state as it stands. The states are therefore reported in snake_case
    and the translations key off the same form.
    """
    if not isinstance(name, str) or not name:
        return name

    out = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return out.lower()


def _decode_device_string(value):
    """Undo the backslash-less unicode escapes some fryers return.

    A recipe name comes back as "u624bu52a8u6a21u5f0f" rather than
    "\\u624b\\u52a8\\u6a21\\u5f0f", so it reaches Home Assistant as
    unreadable ASCII. Only strings made up entirely of uXXXX groups are
    touched, so an ordinary name containing a "u" is left alone.
    """
    if not isinstance(value, str) or not value:
        return value

    if not re.fullmatch(r"(u[0-9a-fA-F]{4})+", value):
        return value

    return re.sub(r"u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)


# http://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf02:1
MIOT_MAPPING = {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:miot-534:1
    MODEL_FRYER_534: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "switch_status": {"siid": 2, "piid": 5},
        "mode": {"siid": 2, "piid": 6},
        "left_time": {"siid": 2, "piid": 7},
        "temperature": {"siid": 2, "piid": 8},
        "preheat": {"siid": 2, "piid": 10},
        "recipe_command": {"siid": 2, "piid": 11},
        "target_cooking_measure": {"siid": 2, "piid": 12},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_recipe_cook": {"siid": 2, "aiid": 4},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf01:1
    MODEL_FRYER_MAF01: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "recipe_id": {"siid": 3, "piid": 1},  # read, notify, write
        "recipe_name": {"siid": 3, "piid": 2},  # read, notify, write
        "work_time": {"siid": 3, "piid": 3},  # write
        "work_temp": {"siid": 3, "piid": 4},  # write
        "appoint_time": {"siid": 3, "piid": 5},  # read, notify, write
        "food_quanty": {"siid": 3, "piid": 6},  # read, notify, write
        "preheat_switch": {"siid": 3, "piid": 7},  # read, notify, write
        "appoint_time_left": {"siid": 3, "piid": 8},  # read, notify, write
        "recipe_sync": {"siid": 3, "piid": 9},  # read, notify, write
        "turn_pot": {"siid": 3, "piid": 10},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2}
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf02:1
    MODEL_FRYER_MAF02: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "recipe_id": {"siid": 3, "piid": 1},  # read, notify, write
        "work_time": {"siid": 3, "piid": 3},  # write
        "work_temp": {"siid": 3, "piid": 4},  # write
        "appoint_time": {"siid": 3, "piid": 5},  # read, notify, write
        "food_quanty": {"siid": 3, "piid": 6},  # read, notify, write
        "preheat_switch": {"siid": 3, "piid": 7},  # read, notify, write
        "appoint_time_left": {"siid": 3, "piid": 8},  # read, notify, write
        "turn_pot": {"siid": 3, "piid": 10},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2}
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf03:1
    MODEL_FRYER_MAF03: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "recipe_sync": {"siid": 3, "piid": 9},
        "turn_pot": {"siid": 3, "piid": 10},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf05a:1
    MODEL_FRYER_MAF05A: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "recipe_id": {"siid": 3, "piid": 1},  # read, notify, write
        "work_time": {"siid": 3, "piid": 3},  # write
        "work_temp": {"siid": 3, "piid": 4},  # write
        "appoint_time": {"siid": 3, "piid": 5},  # read, notify, write
        "food_quanty": {"siid": 3, "piid": 6},  # read, notify, write
        "preheat_switch": {"siid": 3, "piid": 7},  # read, notify, write
        "appoint_time_left": {"siid": 3, "piid": 8},  # read, notify, write
        "turn_pot": {"siid": 3, "piid": 10},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
        "recipe_name": {"siid": 3, "piid": 2},
        "turn_pot_config": {"siid": 3, "piid": 11},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf06:1
    MODEL_FRYER_MAF06: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "turn_pot": {"siid": 3, "piid": 10},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf06a:1
    MODEL_FRYER_MAF06A: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "recipe_sync": {"siid": 3, "piid": 9},
        "turn_pot": {"siid": 3, "piid": 10},
        "turn_pot_config": {"siid": 3, "piid": 11},  # MIOT: turn-pot-cfg
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf06b:1
    MODEL_FRYER_MAF06B: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "recipe_sync": {"siid": 3, "piid": 9},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf07:1
    MODEL_FRYER_MAF07: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "recipe_id": {"siid": 3, "piid": 1},  # read, notify, write
        "work_time": {"siid": 3, "piid": 3},  # write
        "work_temp": {"siid": 3, "piid": 4},  # write
        "appoint_time": {"siid": 3, "piid": 5},  # read, notify, write
        "food_quanty": {"siid": 3, "piid": 6},  # read, notify, write
        "preheat_switch": {"siid": 3, "piid": 7},  # read, notify, write
        "appoint_time_left": {"siid": 3, "piid": 8},  # read, notify, write
        "turn_pot": {"siid": 3, "piid": 10},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2}
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf07c:1
    MODEL_FRYER_MAF07C: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "auto_keep_warm": {"siid": 2, "piid": 6},
        "current_keep_warm": {"siid": 2, "piid": 7},
        "mode": {"siid": 2, "piid": 8},
        "recipe_id": {"siid": 2, "piid": 10},
        "recipe_name": {"siid": 2, "piid": 11},
        "recipe_sync": {"siid": 2, "piid": 12},
        "target_cooking_measure": {"siid": 2, "piid": 13},
        "turn_pot": {"siid": 2, "piid": 14},
        "turn_pot_config": {"siid": 2, "piid": 15},
        "texture": {"siid": 2, "piid": 16},
        "reservation_left_time": {"siid": 2, "piid": 17},
        "cooking_weight": {"siid": 2, "piid": 18},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "resume_cooking": {"siid": 2, "aiid": 4},
        "start_recipe_cook": {"siid": 2, "aiid": 5},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:xiaomi-maf07d:1
    MODEL_FRYER_MAF07D: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "auto_keep_warm": {"siid": 2, "piid": 6},
        "current_keep_warm": {"siid": 2, "piid": 7},
        "mode": {"siid": 2, "piid": 8},
        "recipe_id": {"siid": 2, "piid": 10},
        "recipe_name": {"siid": 2, "piid": 11},
        "recipe_sync": {"siid": 2, "piid": 12},
        "target_cooking_measure": {"siid": 2, "piid": 13},
        "turn_pot": {"siid": 2, "piid": 14},
        "turn_pot_config": {"siid": 2, "piid": 15},
        "texture": {"siid": 2, "piid": 16},
        "reservation_left_time": {"siid": 2, "piid": 17},
        "cooking_weight": {"siid": 2, "piid": 18},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "resume_cooking": {"siid": 2, "aiid": 4},
        "start_recipe_cook": {"siid": 2, "aiid": 5},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf09a:1
    MODEL_FRYER_MAF09A: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "auto_keep_warm": {"siid": 2, "piid": 6},
        "current_keep_warm": {"siid": 2, "piid": 7},
        "mode": {"siid": 2, "piid": 8},
        "recipe_id": {"siid": 2, "piid": 10},
        "recipe_name": {"siid": 2, "piid": 11},
        "recipe_sync": {"siid": 2, "piid": 12},
        "target_cooking_measure": {"siid": 2, "piid": 13},
        "turn_pot": {"siid": 2, "piid": 14},
        "turn_pot_config": {"siid": 2, "piid": 15},
        "texture": {"siid": 2, "piid": 16},
        "reservation_left_time": {"siid": 2, "piid": 17},
        "cooking_weight": {"siid": 2, "piid": 18},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "resume_cooking": {"siid": 2, "aiid": 4},
        "start_recipe_cook": {"siid": 2, "aiid": 5},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf10:1
    MODEL_FRYER_MAF10: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "turn_pot": {"siid": 3, "piid": 10},
        "turn_pot_config": {"siid": 3, "piid": 11},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:xiaomi-maf16:1:0000D043
    MODEL_FRYER_MAF16: {
        "status": {"siid": 2, "piid": 2},
        "device_fault": {"siid": 2, "piid": 3},
        "target_time": {"siid": 2, "piid": 5},
        "target_temperature": {"siid": 2, "piid": 7},
        "left_time": {"siid": 2, "piid": 22},
        "auto_keep_warm": {"siid": 2, "piid": 23},
        "current_keep_warm": {"siid": 2, "piid": 24},
        "mode": {"siid": 2, "piid": 25},
        "recipe_id": {"siid": 2, "piid": 26},
        "recipe_name": {"siid": 2, "piid": 27},
        "recipe_sync": {"siid": 2, "piid": 28},
        "target_cooking_measure": {"siid": 2, "piid": 29},
        "turn_pot": {"siid": 2, "piid": 30},
        "turn_pot_config": {"siid": 2, "piid": 31},
        "texture": {"siid": 2, "piid": 32},
        "reservation_left_time": {"siid": 2, "piid": 33},
        "cooking_weight": {"siid": 2, "piid": 34},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 6},
        "pause": {"siid": 2, "aiid": 7},
        "resume_cooking": {"siid": 2, "aiid": 8},
        "start_recipe_cook": {"siid": 2, "aiid": 9},
    },
    # http://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-maf10a:1
    MODEL_FRYER_MAF10A: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "auto_keep_warm": {"siid": 2, "piid": 6},  # read, notify, write
        "current_keep_warm": {"siid": 2, "piid": 7},  # read, notify, write
        "mode": {"siid": 2, "piid": 8},  # read, notify, write
        "preheat": {"siid": 2, "piid": 9},  # read, notify, write
        "recipe_id": {"siid": 2, "piid": 10},  # read, notify, write
        "recipe_name": {"siid": 2, "piid": 11},  # read, notify, write
        "recipe_sync": {"siid": 2, "piid": 12},  # read, notify, write
        "target_cooking_measure": {"siid": 2, "piid": 13},  # read, notify, write
        "turn_pot": {"siid": 2, "piid": 14},  # read, notify
        "turn_pot_config": {"siid": 2, "piid": 15},  # read, notify, write
        "texture": {"siid": 2, "piid": 16},  # read, notify, write
        "reservation_left_time": {"siid": 2, "piid": 17},  # read, notify, write
        "cooking_weight": {"siid": 2, "piid": 18},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "resume_cooking": {"siid": 2, "aiid": 4},
        "start_recipe_cook": {"siid": 2, "aiid": 5}
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:xiaomi-maf65:1
    MODEL_FRYER_MAF65: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "auto_keep_warm": {"siid": 2, "piid": 6},  # read, notify, write
        "current_keep_warm": {"siid": 2, "piid": 7},  # read, notify, write
        "mode": {"siid": 2, "piid": 8},  # read, notify, write
        "preheat": {"siid": 2, "piid": 9},  # read, notify, write
        "recipe_id": {"siid": 2, "piid": 10},  # read, notify, write
        "recipe_name": {"siid": 2, "piid": 11},  # read, notify, write
        "recipe_sync": {"siid": 2, "piid": 12},  # read, notify, write
        "target_cooking_measure": {"siid": 2, "piid": 13},  # read, notify, write
        "turn_pot": {"siid": 2, "piid": 14},  # read, notify
        "turn_pot_config": {"siid": 2, "piid": 15},  # read, notify, write
        "texture": {"siid": 2, "piid": 16},  # read, notify, write
        "reservation_left_time": {"siid": 2, "piid": 17},  # read, notify, write
        "cooking_weight": {"siid": 2, "piid": 18},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "resume_cooking": {"siid": 2, "aiid": 4},
        "start_recipe_cook": {"siid": 2, "aiid": 5}
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:xiaomi-maf14:1
    MODEL_FRYER_MAF14: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "mode": {"siid": 2, "piid": 5},  # read, notify, write
        "left_time": {"siid": 2, "piid": 6},  # read, notify
        "target_cooking_measure": {"siid": 2, "piid": 7},  # read, notify, write
        "recipe_id": {"siid": 2, "piid": 8},  # read, notify, write
        "recipe_name": {"siid": 2, "piid": 9},  # read, notify, write
        "recipe_sync": {"siid": 2, "piid": 10},  # read, notify, write
        "turn_pot_config": {"siid": 2, "piid": 11},  # read, notify, write
        "turn_pot": {"siid": 2, "piid": 12},  # read, notify
        "current_keep_warm": {"siid": 2, "piid": 13},  # read, notify, write
        "auto_keep_warm": {"siid": 2, "piid": 14},  # read, notify, write
        "reservation_left_time": {"siid": 2, "piid": 15},  # read, notify, write
        "cooking_weight": {"siid": 2, "piid": 16},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_recipe_cook": {"siid": 2, "aiid": 4},
        "resume_cooking": {"siid": 2, "aiid": 5},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:xiaomi-maf15:1:0000D043
    MODEL_FRYER_MAF15: {
        "status": {"siid": 2, "piid": 2},
        "device_fault": {"siid": 2, "piid": 3},
        "mode": {"siid": 2, "piid": 4},
        "target_time": {"siid": 2, "piid": 5},
        "left_time": {"siid": 2, "piid": 6},
        "target_temperature": {"siid": 2, "piid": 7},
        "target_cooking_measure": {"siid": 2, "piid": 10},
        "recipe_id": {"siid": 2, "piid": 12},
        "recipe_sync": {"siid": 2, "piid": 13},
        "recipe_name": {"siid": 2, "piid": 14},
        "turn_pot": {"siid": 2, "piid": 15},
        "turn_pot_config": {"siid": 2, "piid": 16},
        "current_keep_warm": {"siid": 2, "piid": 18},
        "auto_keep_warm": {"siid": 2, "piid": 19},
        "reservation_left_time": {"siid": 2, "piid": 20},
        "cooking_weight": {"siid": 2, "piid": 21},
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_recipe_cook": {"siid": 2, "aiid": 4},
        "resume_cooking": {"siid": 2, "aiid": 5},
    },
    # http://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:silen-sck501:1
    MODEL_FRYER_SCK501: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "switch_status": {"siid": 2, "piid": 5},  # read, notify, write
        "mode": {"siid": 2, "piid": 6},  # read, notify, write
        "left_time": {"siid": 2, "piid": 7},  # read, notify
        "start": {"siid": 3, "piid": 1},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
    },
    # http://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:silen-sck505:1
    MODEL_FRYER_SCK505: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "switch_status": {"siid": 2, "piid": 5},  # read, notify, write
        "mode": {"siid": 2, "piid": 6},  # read, notify, write
        "left_time": {"siid": 2, "piid": 7},  # read, notify
        "start": {"siid": 3, "piid": 1},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:viomi-v3:1
    MODEL_FRYER_V3: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "current_keep_warm": {"siid": 2, "piid": 5},  # read, notify, write
        "recipe_id": {"siid": 2, "piid": 6},  # read, notify, write
        "left_time": {"siid": 2, "piid": 7},  # read, notify
        "turn_pot_config": {"siid": 2, "piid": 9},  # read, notify, write
        "turn_pot": {"siid": 2, "piid": 10},  # read, notify
        "turn_pot_status": {"siid": 3, "piid": 1},  # read, notify
        "start_cook": {"siid": 2, "aiid": 1},
        "pause": {"siid": 2, "aiid": 2},
        "cancel_cooking": {"siid": 2, "aiid": 3},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-ybaf01:1
    MODEL_FRYER_YBAF01: {
        "status": {"siid": 2, "piid": 1},  # read, notify
        "device_fault": {"siid": 2, "piid": 2},  # read, notify
        "target_time": {"siid": 2, "piid": 3},  # read, notify, write
        "target_temperature": {"siid": 2, "piid": 4},  # read, notify, write
        "left_time": {"siid": 2, "piid": 5},  # read, notify
        "mode": {"siid": 2, "piid": 7},  # read, notify, write
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_recipe_cook": {"siid": 2, "aiid": 4},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-ybaf02:1
    MODEL_FRYER_YBAF02: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "recipe_sync": {"siid": 3, "piid": 9},
        "turn_pot": {"siid": 3, "piid": 10},
        "turn_pot_config": {"siid": 3, "piid": 11},  # MIOT: turn-pot-cfg
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-ybaf03:1
    MODEL_FRYER_YBAF03: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "recipe_sync": {"siid": 3, "piid": 9},
        "turn_pot": {"siid": 3, "piid": 10},
        "turn_pot_config": {"siid": 3, "piid": 11},  # MIOT: turn-pot-cfg
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-fryer:0000A0A4:careli-ybaf04:1
    MODEL_FRYER_YBAF04: {
        "status": {"siid": 2, "piid": 1},
        "device_fault": {"siid": 2, "piid": 2},
        "target_time": {"siid": 2, "piid": 3},
        "target_temperature": {"siid": 2, "piid": 4},
        "left_time": {"siid": 2, "piid": 5},
        "recipe_id": {"siid": 3, "piid": 1},
        "recipe_name": {"siid": 3, "piid": 2},
        "work_time": {"siid": 3, "piid": 3},
        "work_temp": {"siid": 3, "piid": 4},
        "appoint_time": {"siid": 3, "piid": 5},
        "food_quanty": {"siid": 3, "piid": 6},
        "preheat_switch": {"siid": 3, "piid": 7},
        "appoint_time_left": {"siid": 3, "piid": 8},
        "recipe_sync": {"siid": 3, "piid": 9},
        "turn_pot": {"siid": 3, "piid": 10},
        "turn_pot_config": {"siid": 3, "piid": 11},  # MIOT: turn-pot-cfg
        "start_cook": {"siid": 2, "aiid": 1},
        "cancel_cooking": {"siid": 2, "aiid": 2},
        "pause": {"siid": 2, "aiid": 3},
        "start_custom_cook": {"siid": 3, "aiid": 1},
        "resume_cooking": {"siid": 3, "aiid": 2},
    },
}


class DeviceException(Exception):
    """Exception wrapping any communication errors with the device."""


class StatusDefault(enum.Enum):
    """ Status """
    Unknown = -1
    Shutdown = 0
    Standby = 1
    Pause = 2
    Appointment = 3
    Cooking = 4
    Preheat = 5
    Cooked = 6
    PreheatFinish = 7
    PreheatPause = 8
    Pause2 = 9
    Keepwarm = 10
    KeepwarmPause = 11
    KeepwarmFinish = 12
    CrispyRoast = 13
    Degrease = 14


class StatusV3(enum.Enum):
    Unknown = -1
    Shutdown = 0
    Cooking = 2
    Keepwarm = 3
    Pause = 4


class StatusXiaomi(enum.Enum):
    Unknown = -1
    Shutdown = 0
    Standby = 1
    Delay = 2
    Cooking = 3
    Pause = 4
    PotPause = 5
    Keepwarm = 6
    KeepwarmFinish = 7
    Cooked = 8


class DeviceFault(enum.Enum):
    """ Device Fault """
    Unknown = -1
    NoFaults = 0
    E1 = 1
    E2 = 2
    E3 = 3


class FoodQuanty(enum.Enum):
    """ Food Quanty """
    Unknown = -1
    Null = 0
    Single = 1
    Double = 2
    Half = 3
    Full = 4


class TurnPot(enum.Enum):
    """ Turn Pot """
    Unknown = -1
    NotTurnPot = 0
    SwitchOff = 1
    TurnPot = 2


class TurnPotXiaomi(enum.Enum):
    """Turn Pot for Xiaomi-style air fryer layouts."""
    Unknown = -1
    NoNeedTurnOverPot = 1
    NeedTurnOverPot = 2


class TurnPotViomi(enum.Enum):
    """Turn Pot for Viomi air fryer layouts."""
    Unknown = -1
    NoNeedTurnOverPot = 0
    NeedTurnOverPot = 1


# The recipe slots a model ships with. The device only reports the slot
# ("M1"), never what it holds -- the Mi Home app keeps that mapping, and
# recipe_name stays on a placeholder like "demo". Mapping the slot to the
# same keys the cooking modes use means both get translated by the same
# entries. A slot that is not listed is reported unchanged.
RECIPE_SLOTS = {
    MODEL_FRYER_MAF05A: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "fish",
        "M4": "steak",
        "M5": "shrimp",
        "M6": "vegetables",
        "M7": "cake",
        "M8": "dried_fruit",
        "M9": "yogurt",
        "M10": "defrost",
    },
    MODEL_FRYER_MAF06A: {
        "M0": "favorites",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "egg_tart",
        "M4": "sweet_potato",
        "M5": "yogurt",
    },
    MODEL_FRYER_MAF06B: {
        "M0": "favorites",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "egg_tart",
        "M4": "sweet_potato",
        "M5": "yogurt",
    },
    MODEL_FRYER_MAF07C: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "lamb_chops",
        "M5": "pork_belly",
        "M6": "fish",
        "M7": "sweet_potato",
        "M8": "cake",
        "M9": "egg_tart",
        "M10": "defrost",
        "M11": "dried_fruit",
        "M12": "yogurt",
    },
    MODEL_FRYER_MAF07D: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "lamb_chops",
        "M5": "fish",
        "M6": "shrimp",
        "M7": "vegetables",
        "M8": "cake",
        "M9": "pizza",
        "M10": "defrost",
        "M11": "dried_fruit",
        "M12": "yogurt",
    },
    MODEL_FRYER_MAF09A: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "lamb_chops",
        "M5": "pork_belly",
        "M6": "fish",
        "M7": "sweet_potato",
        "M8": "cake",
        "M9": "egg_tart",
        "M10": "defrost",
        "M11": "dried_fruit",
        "M12": "yogurt",
    },
    MODEL_FRYER_MAF10A: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "lamb_chops",
        "M5": "fish",
        "M6": "shrimp",
        "M7": "vegetables",
        "M8": "cake",
        "M9": "pizza",
        "M10": "defrost",
        "M11": "dried_fruit",
        "M12": "yogurt",
    },
    MODEL_FRYER_MAF14: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "fish",
        "M5": "shrimp",
        "M6": "vegetables",
        "M7": "cake",
        "M8": "defrost",
        "M9": "dried_fruit",
        "M10": "yogurt",
    },
    MODEL_FRYER_MAF15: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "fish",
        "M5": "shrimp",
        "M6": "vegetables",
        "M7": "cake",
        "M8": "defrost",
        "M9": "dried_fruit",
        "M10": "yogurt",
    },
    MODEL_FRYER_MAF16: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "sweet_potato",
        "M4": "egg_tart",
        "M5": "steak",
        "M6": "pork_belly",
        "M7": "shrimp",
        "M8": "cake",
        "M9": "pizza",
        "M10": "dried_fruit",
        "M11": "defrost",
        "M12": "reheat",
    },
    MODEL_FRYER_MAF65: {
        "M0": "manual",
        "M1": "french_fries",
        "M2": "chicken_wing",
        "M3": "steak",
        "M4": "lamb_chops",
        "M5": "fish",
        "M6": "shrimp",
        "M7": "vegetables",
        "M8": "cake",
        "M9": "pizza",
        "M10": "defrost",
        "M11": "dried_fruit",
        "M12": "yogurt",
    },
    MODEL_FRYER_YBAF03: {
        "C1": "potato_wedges",
        "C2": "chicken_cutlet",
        "C3": "steak",
        "C4": "lamb_chops",
        "C5": "curry_beef",
        "C6": "popcorn_chicken",
        "C7": "sausage",
        "C8": "sweet_potato",
        "C9": "clams",
        "C10": "oysters",
        "C11": "scallops",
        "C12": "crab_sticks",
        "C13": "durian_pastry",
        "C14": "spring_rolls",
        "M0": "default_program",
        "M1": "chicken",
        "M2": "steak",
        "M3": "fish",
        "M4": "cake",
        "M5": "pizza",
        "M6": "hot_dog",
        "M7": "french_fries",
        "M8": "bacon",
    },
    MODEL_FRYER_YBAF04: {
        "C1": "potato_wedges",
        "C2": "chicken_cutlet",
        "C3": "steak",
        "C4": "lamb_chops",
        "C5": "curry_beef",
        "C6": "popcorn_chicken",
        "C7": "sausage",
        "C8": "sweet_potato",
        "C9": "clams",
        "C10": "oysters",
        "C11": "scallops",
        "C12": "crab_sticks",
        "C13": "durian_pastry",
        "C14": "spring_rolls",
        "M0": "default_program",
        "M1": "chicken",
        "M2": "steak",
        "M3": "fish",
        "M4": "cake",
        "M5": "pizza",
        "M6": "hot_dog",
        "M7": "french_fries",
        "M8": "bacon",
    },
}


# Models whose turn-pot property is 1 = no need, 2 = need, per their specs.
# Everything else counts from 0.
MODELS_TURN_POT_ONE_BASED = [
    MODEL_FRYER_MAF07C,
    MODEL_FRYER_MAF07D,
    MODEL_FRYER_MAF09A,
    MODEL_FRYER_MAF10A,
    MODEL_FRYER_MAF14,
    MODEL_FRYER_MAF15,
    MODEL_FRYER_MAF16,
    MODEL_FRYER_MAF65,
]


class PreheatSwitch(enum.Enum):
    """ Turn Pot """
    Unknown = -1
    Null = 0
    Off = 1
    On = 2


class CookingModeDefault(enum.Enum):
    Manual = 0
    FrenchFries = 1
    ChickenWing = 2
    Steak = 3
    LambChops = 4
    Fish = 5
    Shrimp = 6
    Vegetables = 7
    Cake = 8
    Pizza = 9
    Defrost = 10
    DriedFruit = 11
    Yogurt = 12


class CookingModeXiaomi(enum.Enum):
    Manual = 0
    ChickenWing = 1
    Steak = 2
    Fish = 3
    FrenchFries = 4
    Cake = 5
    Defrost = 6
    DriedFruit = 7
    Yogurt = 8
    Shrimp = 9
    Vegetables = 10


class CookingTexture(enum.Enum):
    Unknown = -1
    NONE = 0
    CrispyRoast = 1
    TenderRoast = 2
    Degrease = 3

class FryerStatusMiot(DeviceStatus):
    """Container for status reports for Xiaomi FryerStatusMiot."""

    def __init__(self, model: str, data: Dict[str, Any]) -> None:
        """
        Response of a Fryer (careli.fryer.maf02):
        {
          'id': 1,
          'result': [
            {'did': 'status', 'siid': 2, 'piid': 1, 'code': 0, 'value': 0},
            {'did': 'device_fault', 'siid': 2, 'piid': 2, 'code': 0, 'value': 0},
            {'did': 'target_time', 'siid': 2, 'piid': 3, 'code': 0, 'value': 2},
            {'did': 'target_temperature', 'siid': 4, 'piid': 4, 'code': 0, 'value': 54},
            {'did': 'left_time', 'siid': 2, 'piid': 5, 'code': 0, 'value': 0},
            {'did': 'auto_keep_warm', 'siid': 2, 'piid': 6, 'code': 0, 'value': 0},
            {'did': 'current_keep_warm', 'siid': 2, 'piid': 7, 'code': 0, 'value': 0},
            {'did': 'mode', 'siid': 2, 'piid': 8, 'code': 0, 'value': 0},
            {'did': 'preheat', 'siid': 2, 'piid': 9, 'code': 0, 'value': 0},
            {'did': 'recipe_id', 'siid': 2, 'piid': 10, 'code': 0, 'value': 0},
            {'did': 'recipe_name', 'siid': 2, 'piid': 11, 'code': 0, 'value': 0},
            {'did': 'recipe_sync', 'siid': 2, 'piid': 12, 'code': 0, 'value': 0},
            {'did': 'target_cooking_measure, 'siid': 2, 'piid': 13, 'code': 0, 'value': 0},
            {'did': 'turn_pot', 'siid': 2, 'piid': 14, 'code': 0, 'value': 1},
            {'did': 'turn_pot_config', 'siid': 2, 'piid': 15, 'code': 0, 'value': 0},
            {'did': 'texture', 'siid': 2, 'piid': 16, 'code': 0, 'value': 0},
            {'did': 'reservation_left_time', 'siid': 2, 'piid': 17, 'code': 0, 'value': 1},
            {'did': 'cooking_weight', 'siid': 2, 'piid': 18, 'code': 0, 'value': 1}
          ],
          'exe_time': 280
        }
        """
        self.model = model
        self.data = data

    @property
    def is_on(self) -> bool:
        """True if device is currently on."""
        if self.model in [MODEL_FRYER_MAF14]:
            return False if self.data["status"] in [0, 1, 7, 8] else True
        else:
            return False if self.data["status"] in [0, 1, 6, 9] else True

    @property
    def mode(self) -> int:
        """Mode."""
        mode_raw = self.data["mode"]
        if self.model in [MODEL_FRYER_MAF14]:
            return CookingModeXiaomi(mode_raw)
        else:
            return CookingModeDefault(mode_raw)

    @property
    def status(self) -> int:
        """Operation status."""
        try:
            status_raw = self.data["status"]
            if self.model in [MODEL_FRYER_MAF14]:
                return StatusXiaomi(status_raw)
            elif self.model in [MODEL_FRYER_V3]:
                return StatusV3(status_raw)
            else:
                return StatusDefault(status_raw)
        except ValueError:
            _LOGGER.error("Unknown Status (%s)", self.data["status"])
            return StatusDefault.Unknown

    @property
    def device_fault(self) -> int:
        """Device Fault."""
        try:
            return DeviceFault(self.data["device_fault"])
        except ValueError:
            _LOGGER.error("Unknown Device Fault (%s)", self.data["device_fault"])
            return DeviceFault.Unknown

    @property
    def target_time(self) -> int:
        """Target Time."""
        return self.data["target_time"]

    @property
    def target_temperature(self) -> int:
        """Target Temperature."""
        return self.data["target_temperature"]

    @property
    def left_time(self) -> int:
        """Left Time."""
        return self.data["left_time"]

    @property
    def recipe_id(self) -> str:
        """The recipe the device is set to, named where the slot is known.

        Anything the model's slot table does not cover reports as Unknown
        rather than the raw value: the sensor declares its options up front,
        and Home Assistant drops an entity whose state is not among them.
        The raw value stays available as an attribute.
        """
        raw = self.data["recipe_id"]
        slots = RECIPE_SLOTS.get(self.model)

        if not slots:
            return raw

        return slots.get(raw, "unknown")

    @property
    def recipe_slot(self) -> str:
        """The raw slot the device reports, whatever it holds."""
        return self.data.get("recipe_id")

    @property
    def recipe_name(self) -> str:
        """Recipe name as shown in the app."""
        return _decode_device_string(self.data.get("recipe_name"))

    @property
    def work_time(self) -> int:
        """Work time."""
        return self.data["work_time"]

    @property
    def work_temp(self) -> int:
        """Work Temp."""
        return self.data["work_temp"]

    @property
    def appoint_time(self) -> int:
        """Appoint Time"""
        return self.data["appoint_time"]

    @property
    def left_percent(self) -> int:
        """Remaining cooking time as a percentage of the target time."""
        target_time = self.data.get("target_time")
        left_time = self.data.get("left_time")

        if not target_time or left_time is None:
            return None

        return round(left_time * 100 / target_time)

    @property
    def appoint_time_left(self) -> int:
        """Appoint Time Left"""
        # Read with .get(): the sensor is defined for every SENSOR_TYPES_MAF
        # model, but not every mapping requests this property, and a KeyError
        # here would surface as an entity error instead of an unknown state.
        return self.data.get("appoint_time_left")

    @property
    def food_quanty(self) -> FoodQuanty:
        """Food Quanty."""
        try:
            return FoodQuanty(self.data["food_quanty"])
        except ValueError:
            _LOGGER.error("Unknown FoodQuanty (%s)", self.data["food_quanty"])
            return FoodQuanty.Unknown

    @property
    def preheat_switch(self) -> int:
        """Preheat Switch"""
        try:
            return PreheatSwitch(self.data["preheat_switch"])
        except ValueError:
            _LOGGER.error("Unknown PreheatSwitch (%s)", self.data["preheat_switch"])
            return PreheatSwitch.Unknown

    @property
    def switch_status(self) -> int:
        """Switch Status."""
        return self.data.get("switch_status")

    @property
    def temperature(self) -> int:
        """Current Temperature."""
        return self.data.get("temperature")

    @property
    def recipe_command(self) -> str:
        """Recipe Command."""
        return self.data.get("recipe_command")

    @property
    def target_cooking_measure(self) -> int:
        """Target Cooking Measure."""
        return self.data.get("target_cooking_measure")

    @property
    def turn_pot_status(self) -> int:
        """Turn Pot Status."""
        # Returned raw on purpose: the V3 mapping carries turn_pot,
        # turn_pot_config and turn_pot_status side by side, and which of the
        # TurnPot enums applies to this one is not documented anywhere.
        return self.data.get("turn_pot_status")

    def _turn_pot_enum(self) -> type[enum.Enum]:
        """Return the correct Turn Pot enum for this device layout.

        Which values a model uses is a property of the model, taken from the
        published specs, not of whether it happens to report turn_pot_config:
        careli.fryer.maf05a reports both, yet counts from 0 like the default.
        """
        if self.model == MODEL_FRYER_V3:
            return TurnPotViomi

        if self.model in MODELS_TURN_POT_ONE_BASED:
            return TurnPotXiaomi

        return TurnPot

    @property
    def turn_pot(self) -> enum.Enum:
        """Turn Pot."""
        turn_pot_enum = self._turn_pot_enum()

        try:
            return turn_pot_enum(self.data["turn_pot"])
        except ValueError:
            _LOGGER.error("Unknown TurnPot (%s)", self.data["turn_pot"])
            return turn_pot_enum(-1)

    @property
    def preheat(self) -> bool:
        """Preheat phase."""
        return self.data["preheat"]

    @property
    def turn_pot_config(self) -> bool:
        """Turn Pot Config."""
        return self.data["turn_pot_config"]

    @property
    def texture(self) -> CookingTexture:
        """Texture."""
        try:
            return CookingTexture(self.data["texture"])
        except ValueError:
            _LOGGER.error("Unknown Texture (%s)", self.data["texture"])
            return CookingTexture.Unknown

    @property
    def reservation_left_time(self) -> int:
        """Reservation Left Time."""
        return self.data["reservation_left_time"]

    @property
    def cooking_weight(self) -> int:
        """Cooking Weight."""
        return self.data["cooking_weight"]

class FryerMiot(MiotDevice):
    """Interface for AirFryer (careli.fryer.maf02)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_MAF02]

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        model: str = MODEL_FRYER_MAF02,
    ) -> None:
        if model not in MIOT_MAPPING:
            raise DeviceException("Invalid FryerMiot model: %s" % model)

        super().__init__(ip, token, start_id, debug, lazy_discover)
        self._model = model
        self.mapping = MIOT_MAPPING[model]

    @command(
        default_output=format_output(
            "",
            "Status: {result.status.name}\n"
            "Device Fault: {result.device_fault.name}\n"
            "Target Time: {result.target_time}\n"
            "Target Temperature: {result.target_temperature}\n"
            "Left Time: {result.left_time}\n"
            "Recipe ID: {result.recipe_id}\n"
            "Work Time: {result.work_time}\n"
            "Work Temperature: {result.work_temp}\n"
            "Appoint Time: {result.appoint_time}\n"
            "Food Quanty: {result.food_quanty.name}\n"
            "Preheat Switch: {result.preheat_switch.name}\n"
            "Appoint Time Left: {result.appoint_time_left}\n"
            "Turn Pot: {result.turn_pot.name}\n",
        )
    )
    def status(self) -> FryerStatusMiot:
        """Retrieve properties."""
        return FryerStatusMiot(
            self._model,
            {
                prop["did"]: prop["value"] if prop["code"] == 0 else None
                for prop in self.get_properties_for_mapping()
            },
        )

    @command(
        click.argument("hours", type=int),
        default_output=format_output("Setting appoint time to {hours} hours"),
    )
    def appoint_time(self, minutes: int):
        """Set the delay in minutes before cooking starts."""
        # The parameter used to be called hours while being validated and sent
        # as minutes, and the service selector offered a 1-24 range to match
        # the name -- so asking for "2" meant two minutes, not two hours.
        if minutes < 0 or minutes > 24 * 60:
            raise DeviceException("Invalid value for a appoint time: %s" % minutes)

        return self.set_property("appoint_time", minutes)

    @command(
        click.argument("turn_pot_config", type=bool),
        default_output=format_output("Setting turn pot reminder to {turn_pot_config}"),
    )
    def turn_pot_config(self, turn_pot_config: bool):
        """Turn the reminder to turn the food on or off."""
        if "turn_pot_config" not in self.mapping:
            raise DeviceException(
                "Turn pot reminder is not supported by %s" % self._model
            )

        return self.set_property("turn_pot_config", 1 if turn_pot_config else 0)

    @command(
        click.argument("preheat", type=bool),
        default_output=format_output("Setting preheat to {preheat}"),
    )
    def preheat(self, preheat: bool):
        """Turn the preheat phase on or off."""
        # Two spellings exist across the models: preheat_switch is an enum
        # (1 off, 2 on), preheat is a plain bool.
        if "preheat_switch" in self.mapping:
            return self.set_property("preheat_switch", 2 if preheat else 1)

        if "preheat" in self.mapping:
            return self.set_property("preheat", preheat)

        raise DeviceException(
            "Preheat is not supported by %s" % self._model
        )

    @command(
        click.argument("recipe_id", type=str),
        default_output=format_output("Setting recipe id to {recipe_id}"),
    )
    def recipe_id(self, recipe_id: str):
        """Set recipe id."""
        return self.set_property("recipe_id", recipe_id)

    @command(
        click.argument("food_quanty", type=int),
        default_output=format_output("Setting food quanty to {food_quanty}"),
    )
    def food_quanty(self, food_quanty: int):
        """Set recipe id."""
        if food_quanty < 0 or food_quanty > 5:
            raise DeviceException("Invalid value for food_quanty: %s" % food_quanty)
        return self.set_property("food_quanty", food_quanty)

    @command(
        click.argument("target_time", type=int),
        default_output=format_output("Setting target time to {target_time}"),
    )
    def target_time(self, target_time: int):
        """Set recipe id."""
        if target_time < 1 or target_time > 1440:
            raise DeviceException("Invalid value for target_time: %s" % target_time)
        return self.set_property("target_time", target_time)

    @command(
        click.argument("target_temperature", type=int),
        default_output=format_output("Setting target temperature to {target_temperature}"),
    )
    def target_temperature(self, target_temperature: int):
        """Set recipe id."""
        if target_temperature < 40 or target_temperature > 200:
            raise DeviceException("Invalid value for target_temperature: %s" % target_temperature)
        return self.set_property("target_temperature", target_temperature)

    @command()
    def start_cook(self) -> None:
        """Start cook"""
        return self.call_action("start_cook")

    @command()
    def cancel_cooking(self) -> None:
        """Cancel cooking."""
        return self.call_action("cancel_cooking")

    @command()
    def pause(self) -> None:
        """Pause cook"""
        return self.call_action("pause")

    @command()
    def start_custom_cook(self, mode) -> None:
        """Start custom cook"""
        if mode not in [1, 3, 4, 5, 6, 7]:
            raise DeviceException("Invalid value for a mode: %s" % mode)
        return self.call_action("start_custom_cook", mode)

    @command()
    def resume_cooking(self) -> None:
        """Resume cooking."""
        return self.call_action("resume_cooking")


class FryerMiotYBAF(FryerMiot):
    """Interface for AirFryer (careli.fryer.maf02)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_YBAF01]


class FryerMiotSCK(FryerMiot):
    """Interface for AirFryer (careli.fryer.maf02)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_SCK505]


class FryerMiotMi(FryerMiot):
    """Interface for AirFryer (careli.fryer.maf02)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_534]


class FryerMiotViomi(FryerMiot):
    """Interface for AirFryer (viomi.fryer.v3)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_V3]

class FryerMiotXiaomi(FryerMiot):
    """Interface for AirFryer (xiaomi.fryer.maf14)"""
    mapping = MIOT_MAPPING[MODEL_FRYER_MAF14]
