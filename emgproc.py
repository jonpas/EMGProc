#!/usr/bin/env python3

import sys
import argparse

import pygame
from myo_raw import MyoRaw, DataCategory, EMGMode


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600


class Plot():
    def __init__(self):
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.last_vals = None

    def plot(self, scr, vals, draw_lines=True):
        if self.last_vals is None:
            self.last_vals = vals
            return

        D = 5
        scr.scroll(-D)
        scr.fill((0, 0, 0), (WINDOW_WIDTH - D, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        for i, (u, v) in enumerate(zip(self.last_vals, vals)):
            if draw_lines:
                pygame.draw.line(scr, (0, 255, 0),
                                 (WINDOW_WIDTH - D, int(WINDOW_HEIGHT / 9 * (i + 1 - u))),
                                 (WINDOW_WIDTH, int(WINDOW_HEIGHT / 9 * (i + 1 - v))))
                pygame.draw.line(scr, (255, 255, 255),
                                 (WINDOW_WIDTH - D, int(WINDOW_HEIGHT / 9 * (i+1))),
                                 (WINDOW_WIDTH, int(WINDOW_HEIGHT / 9 * (i+1))))
            else:
                c = int(255 * max(0, min(1, v)))
                scr.fill((c, c, c),
                         (WINDOW_WIDTH - D,
                          i * WINDOW_HEIGHT / 8,
                          D,
                          (i + 1) * WINDOW_HEIGHT / 8 - i * WINDOW_HEIGHT / 8))

        pygame.display.flip()
        self.last_vals = vals


class Myo():
    def __init__(self, tty, native, mac):
        self.myo = MyoRaw(tty, native, mac)

        # Add handles to process EMG and battery level data
        self.myo.add_handler(DataCategory.EMG, self.handle_emg)
        self.myo.add_handler(DataCategory.BATTERY, self.handle_battery)

        # Subscribe to all data services in full RAW mode (200 Hz)
        self.myo.subscribe(EMGMode.RAW)

        # Disable sleep to a void disconnects while retrieving data
        self.myo.set_sleep_mode(1)

        # Vibrate to signalise a successful setup
        # myo.vibrate(1)

    def handle_emg(self, timestamp, emg, moving, characteristic_num):
        print("emg:", timestamp, emg, moving, characteristic_num)

    def handle_battery(self, timestamp, battery_level):
        print("battery level:", timestamp, battery_level)
        if battery_level < 5:
            self.myo.set_leds([255, 0, 0], [255, 0, 0])  # red logo, red bar
        else:
            self.myo.set_leds([128, 128, 255], [128, 128, 255])  # purple logo, purple bar


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Processor")
    parser.add_argument("--sleep", default=None, action="store_true", help="Put Myo into deep sleep (turn off)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group.add_argument("--native", default=False, action="store_true", help="Use a native Bluetooth stack")
    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")
    args = parser.parse_args()

    # Myo setup
    myo = Myo(args.tty, args.native, args.mac)

    if args.sleep:
        myo.myo.deep_sleep()
    else:
        # Run until terminated by user
        try:
            while True:
                myo.myo.run(1)
        except KeyboardInterrupt:
            pass
        finally:
            myo.myo.disconnect()


if __name__ == "__main__":
    sys.exit(main())
