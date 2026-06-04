# -*- coding: utf-8 -*-
"""
Moonboard LED Animations

Firework effects for special occasions (Silvester, parties).
Clean implementation using the MoonBoard class from moonboard.py.
"""

import time
import random
import string
import json

try:
    from colormap import hex2rgb
except ImportError:
    def hex2rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def clamp(n, minn, maxn):
    """Clamp value between min and max."""
    return max(min(maxn, n), minn)


COLS = string.ascii_uppercase[0:11]
ROWS = 18


def all_holds():
    """Generate all hold names A1-K18."""
    return [f"{c}{r}" for c in COLS for r in range(1, ROWS + 1)]


def column_holds(col):
    """Generate all holds in a column."""
    return [f"{col}{r}" for r in range(1, ROWS + 1)]


class FireworkAnimation:
    """Firework effect on a single column or all columns.
    
    Based on: http://www.anirama.com/1000leds/1d-fireworks/
    """

    GRAVITY = -0.04
    NUM_SPARKS = 9

    def __init__(self, moonboard):
        self.mb = moonboard

    def run_single_column(self, col="F", spread_to_neighbors=False):
        """Launch a firework in a single column."""
        self._launch_flare(col, spread_to_neighbors)

    def run_full_width(self):
        """Launch a firework across all columns simultaneously."""
        self._launch_flare_multi()

    def _launch_flare(self, col, spread=False):
        """Single-column firework: launch phase + explosion phase."""
        spark_pos = [0.0] * self.NUM_SPARKS
        spark_vel = [0.0] * self.NUM_SPARKS
        spark_col = [0.0] * self.NUM_SPARKS

        flare_pos = 0.0
        flare_vel = random.uniform(0.5, 0.9) * 1.55
        gravity = self.GRAVITY

        # Phase 1: Launch - sparks rise
        for i in range(3):
            spark_pos[i] = 0.0
            spark_vel[i] = flare_vel * random.uniform(0.8, 1.2)
            spark_col[i] = clamp(spark_vel[i] * 1000, 0, 255)

        self.mb.clear()
        while flare_vel >= -0.2:
            # Clear column
            for h in column_holds(col):
                self.mb.layout.set(self.mb.MAPPING[h], (0, 0, 0))

            # Draw sparks
            for i in range(3):
                spark_pos[i] += spark_vel[i]
                spark_pos[i] = clamp(spark_pos[i], 0.0, float(ROWS))
                spark_vel[i] += gravity
                spark_col[i] = clamp(spark_col[i] - 5.6, 0.0, 255.0)
                row = clamp(int(spark_pos[i]), 1, ROWS)
                color = (int(spark_col[i]), 0, 0)
                self.mb.layout.set(self.mb.MAPPING[f"{col}{row}"], color)

            # Draw flare tip
            flare_row = clamp(int(flare_pos), 1, ROWS)
            self.mb.layout.set(self.mb.MAPPING[f"{col}{flare_row}"], (255, 0, 0))
            self.mb.layout.push_to_driver()

            flare_pos += flare_vel
            flare_pos = clamp(flare_pos, 0, ROWS)
            flare_vel += gravity

        # Phase 2: Explosion
        n_sparks = max(2, int(flare_pos / 2))
        for i in range(n_sparks):
            spark_pos[i] = flare_pos
            spark_vel[i] = random.uniform(-1.0, 1.0)
            spark_col[i] = clamp(abs(spark_vel[i]) * 500, 0, 255)
            spark_vel[i] *= flare_pos / ROWS

        spark_col[0] = 255.0
        dying_gravity = gravity
        c1 = 180.0  # white-to-yellow threshold
        c2 = 135.0  # yellow-to-red threshold

        while spark_col[0] > c2 / 128:
            # Clear column
            for h in column_holds(col):
                self.mb.layout.set(self.mb.MAPPING[h], (0, 0, 0))

            # Draw exploding sparks
            for i in range(n_sparks):
                spark_pos[i] += spark_vel[i]
                spark_pos[i] = clamp(spark_pos[i], 0, ROWS)
                spark_vel[i] += dying_gravity
                spark_col[i] *= 0.9
                spark_col[i] = clamp(spark_col[i], 0, 255)

                # Color gradient: white → yellow → red → black
                if spark_col[i] > c1:
                    ratio = (spark_col[i] - c1) / (255 - c1)
                    color = (255, 255, int(255 * ratio))
                elif spark_col[i] < c2:
                    ratio = spark_col[i] / c2
                    color = (int(255 * ratio), 0, 0)
                else:
                    ratio = (spark_col[i] - c2) / (c1 - c2)
                    color = (255, int(255 * ratio), 0)

                row = clamp(int(spark_pos[i]), 1, ROWS)
                target_col = col
                if spread:
                    col_idx = ord(col) - 65
                    offset = int(spark_vel[i] * 2)
                    new_idx = clamp(col_idx + offset, 0, 10)
                    target_col = chr(new_idx + 65)
                self.mb.layout.set(self.mb.MAPPING[f"{target_col}{row}"], color)

            dying_gravity *= 0.995
            self.mb.layout.push_to_driver()

    def _launch_flare_multi(self):
        """Full-width firework: all columns launch simultaneously."""
        spark_pos = [0.0] * self.NUM_SPARKS
        spark_vel = [0.0] * self.NUM_SPARKS
        spark_col = [0.0] * self.NUM_SPARKS

        flare_pos = 0.0
        flare_vel = random.uniform(0.5, 0.9) * 1.55
        gravity = self.GRAVITY

        for i in range(3):
            spark_pos[i] = 0.0
            spark_vel[i] = flare_vel * random.uniform(0.8, 1.2)
            spark_col[i] = clamp(spark_vel[i] * 1000, 0, 255)

        self.mb.clear()
        while flare_vel >= -0.2:
            # Clear all
            for h in all_holds():
                self.mb.layout.set(self.mb.MAPPING[h], (0, 0, 0))

            for i in range(3):
                spark_pos[i] += spark_vel[i]
                spark_pos[i] = clamp(spark_pos[i], 0.0, float(ROWS))
                spark_vel[i] += gravity
                spark_col[i] = clamp(spark_col[i] - 5.6, 0.0, 255.0)
                row = clamp(int(spark_pos[i]), 1, ROWS)
                color = (int(spark_col[i]), 0, 0)
                for c in COLS:
                    self.mb.layout.set(self.mb.MAPPING[f"{c}{row}"], color)

            flare_row = clamp(int(flare_pos), 1, ROWS)
            for c in COLS:
                self.mb.layout.set(self.mb.MAPPING[f"{c}{flare_row}"], (255, 0, 0))

            self.mb.layout.push_to_driver()
            flare_pos += flare_vel
            flare_pos = clamp(flare_pos, 0, ROWS)
            flare_vel += gravity

        # Explosion phase (all columns)
        n_sparks = max(2, int(flare_pos / 2))
        for i in range(n_sparks):
            spark_pos[i] = flare_pos
            spark_vel[i] = random.uniform(-1.0, 1.0)
            spark_col[i] = clamp(abs(spark_vel[i]) * 500, 0, 255)
            spark_vel[i] *= flare_pos / ROWS

        spark_col[0] = 255.0
        dying_gravity = gravity
        c1, c2 = 180.0, 135.0

        while spark_col[0] > c2 / 128:
            for h in all_holds():
                self.mb.layout.set(self.mb.MAPPING[h], (0, 0, 0))

            for i in range(n_sparks):
                spark_pos[i] += spark_vel[i]
                spark_pos[i] = clamp(spark_pos[i], 0, ROWS)
                spark_vel[i] += dying_gravity
                spark_col[i] *= 0.9
                spark_col[i] = clamp(spark_col[i], 0, 255)

                if spark_col[i] > c1:
                    ratio = (spark_col[i] - c1) / (255 - c1)
                    color = (255, 255, int(255 * ratio))
                elif spark_col[i] < c2:
                    ratio = spark_col[i] / c2
                    color = (int(255 * ratio), 0, 0)
                else:
                    ratio = (spark_col[i] - c2) / (c1 - c2)
                    color = (255, int(255 * ratio), 0)

                row = clamp(int(spark_pos[i]), 1, ROWS)
                for c in COLS:
                    self.mb.layout.set(self.mb.MAPPING[f"{c}{row}"], color)

            dying_gravity *= 0.995
            self.mb.layout.push_to_driver()


class ColorWipeAnimation:
    """Wipe colors across the board row by row."""

    def __init__(self, moonboard):
        self.mb = moonboard

    def run(self, colors=None, duration=0.01):
        """Run color wipe animation with given colors."""
        if colors is None:
            colors = [(128, 0, 128), (0, 0, 255), (255, 0, 0), (0, 255, 0)]

        for color in colors:
            for row in range(1, ROWS + 1):
                for col in COLS:
                    self.mb.layout.set(self.mb.MAPPING[f"{col}{row}"], color)
                self.mb.layout.push_to_driver()
                time.sleep(duration)
            time.sleep(1.0)
        self.mb.clear()


class SingleColorAnimation:
    """Fill the entire board with a single color."""

    def __init__(self, moonboard):
        self.mb = moonboard

    def run(self, color=(255, 0, 0), duration=5):
        """Display a solid color for duration seconds."""
        for h in all_holds():
            self.mb.layout.set(self.mb.MAPPING[h], color)
        self.mb.layout.push_to_driver()
        time.sleep(duration)
        self.mb.clear()


class PixelArtAnimation:
    """Display pixel art on the moonboard grid."""

    def __init__(self, moonboard):
        self.mb = moonboard

    def display(self, art_data, duration=10):
        """Display pixel art from a dict of {hold: color_tuple}."""
        self.mb.clear()
        for hold, color in art_data.items():
            if hold in self.mb.MAPPING:
                self.mb.layout.set(self.mb.MAPPING[hold], color)
        self.mb.layout.push_to_driver()
        time.sleep(duration)

    def display_watermelon(self, duration=10):
        """Display the watermelon pixel art."""
        red = (255, 0, 0)
        lila = hex2rgb("#ff99dd")
        green1 = hex2rgb("#118233")
        green2 = hex2rgb("#089c48")

        art = {}
        # Row 1 - green base
        for h in ["C1", "D1", "E1", "F1", "G1"]:
            art[h] = green2
        # Row 2
        for h in ["B2", "H2"]:
            art[h] = green2
        for h in ["C2", "D2", "E2", "F2", "G2"]:
            art[h] = green1
        # Row 3
        for h in ["A3", "I3"]:
            art[h] = green2
        art["H3"] = green1
        for h in ["B3", "C3", "D3", "E3", "F3", "G3"]:
            art[h] = lila
        # Row 4
        for h in ["A4", "C4", "D4", "E4", "F4", "G4"]:
            art[h] = red
        art["H4"] = lila
        art["I4"] = green1
        art["J4"] = green2
        # Row 5
        for h in ["A5", "B5", "C5", "E5", "G4"]:
            art[h] = red
        art["H5"] = lila
        art["I5"] = green1
        art["J5"] = green2
        # Row 6
        for h in ["B6", "C6", "D6", "E6", "F6", "G6"]:
            art[h] = red
        art["H6"] = lila
        art["I6"] = green1
        art["J6"] = green2
        # Row 7
        for h in ["C7", "D7", "F7", "G7"]:
            art[h] = red
        art["H7"] = lila
        art["I7"] = green1
        art["J7"] = green2
        # Row 8
        for h in ["D8", "E8", "F8"]:
            art[h] = red
        art["H8"] = lila
        art["I8"] = green1
        art["J8"] = green2
        # Row 9
        for h in ["E9", "F9"]:
            art[h] = red
        art["G9"] = lila
        art["H9"] = green1
        art["I9"] = green2
        # Row 10
        art["F10"] = lila
        art["G10"] = green1
        art["H10"] = green2

        self.display(art, duration)


class SilvesterShow:
    """Complete Silvester/New Year's Eve show combining multiple effects."""

    def __init__(self, moonboard):
        self.mb = moonboard
        self.firework = FireworkAnimation(moonboard)
        self.wipe = ColorWipeAnimation(moonboard)
        self.solid = SingleColorAnimation(moonboard)
        self.pixel_art = PixelArtAnimation(moonboard)

    def run(self, loops=None):
        """Run the complete Silvester show.
        
        Args:
            loops: Number of cycles (None = infinite)
        """
        count = 0
        while loops is None or count < loops:
            self.wipe.run()
            self.pixel_art.display_watermelon()
            self.firework.run_single_column(col=random.choice(list(COLS)))
            self.solid.run(color=(255, 1, 154), duration=3)
            self.solid.run(color=(255, 255, 0), duration=3)
            self.firework.run_full_width()
            count += 1


if __name__ == "__main__":
    import argparse
    from moonboard import MoonBoard

    parser = argparse.ArgumentParser(description='Moonboard LED Animations')
    parser.add_argument('--driver_type', type=str,
                        choices=['PiWS281x', 'WS2801', 'SimPixel'],
                        default="PiWS281x")
    parser.add_argument('--led_mapping', type=str, default='led_mapping.json')
    parser.add_argument('--mode', type=str, 
                        choices=['silvester', 'firework', 'wipe', 'solid', 'watermelon'],
                        default='silvester')
    parser.add_argument('--loops', type=int, default=None,
                        help='Number of animation loops (default: infinite)')
    parser.add_argument('--color', type=str, default='255,0,0',
                        help='Color as R,G,B for solid mode')
    args = parser.parse_args()

    mb = MoonBoard(args.driver_type, args.led_mapping)

    if args.mode == 'silvester':
        show = SilvesterShow(mb)
        show.run(loops=args.loops)
    elif args.mode == 'firework':
        fw = FireworkAnimation(mb)
        while True:
            col = random.choice(list(COLS))
            fw.run_single_column(col, spread_to_neighbors=True)
    elif args.mode == 'wipe':
        wipe = ColorWipeAnimation(mb)
        wipe.run()
    elif args.mode == 'solid':
        r, g, b = [int(x) for x in args.color.split(',')]
        solid = SingleColorAnimation(mb)
        solid.run(color=(r, g, b))
    elif args.mode == 'watermelon':
        art = PixelArtAnimation(mb)
        art.display_watermelon()

    mb.clear()
