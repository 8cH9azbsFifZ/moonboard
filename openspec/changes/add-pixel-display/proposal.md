# Use the wall as a pixel display

## Why

The 198 LEDs form an 11 x 18 pixel display. Gerolf wants to show symbols and animations
from his home automation (ki-skills skill `kletterwand-display`), in any colour. The LED
service only knows the fixed route colours.

## What Changes

- The LED service additionally subscribes to `moonboard/led/frame` with payload
  `{"pixels": {"A1": [r, g, b], ...}}`; unlisted positions are off. A route message
  afterwards replaces the frame as before.
- Validation in `led/frame.py`; frames are not logged one by one (animations).

## Capabilities

### New Capabilities
- `pixel-display`: show free-colour frames on the wall

### Modified Capabilities
- none

## Impact

- `led/moonboard_led_service.py`, new `led/frame.py`, tests. No new dependency.
