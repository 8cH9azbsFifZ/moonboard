# -*- coding: utf-8 -*-
"""Free-colour frames for the wall as a pixel display (openspec/changes/add-pixel-display).

Topic moonboard/led/frame, payload {"pixels": {"A1": [r, g, b], ...}}; unlisted positions are off.
"""
import re

FRAME_TOPIC = "moonboard/led/frame"
POSITION = re.compile(r"^[A-K](?:[1-9]|1[0-8])$")
MAX_PIXELS = 198


class InvalidFrame(ValueError):
    pass


def parse_frame(msg):
    """Return {position: (r, g, b)} or raise InvalidFrame."""
    if not isinstance(msg, dict) or not isinstance(msg.get("pixels"), dict):
        raise InvalidFrame("frame needs an object 'pixels'")
    pixels = msg["pixels"]
    if len(pixels) > MAX_PIXELS:
        raise InvalidFrame("too many pixels")
    out = {}
    for pos, rgb in pixels.items():
        if not POSITION.match(pos):
            raise InvalidFrame("invalid position " + repr(pos))
        if (not isinstance(rgb, list) or len(rgb) != 3
                or not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in rgb)):
            raise InvalidFrame("invalid colour for " + pos)
        out[pos] = tuple(rgb)
    return out
