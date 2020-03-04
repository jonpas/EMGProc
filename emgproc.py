#!/usr/bin/env python3

import sys
import argparse
import time

import pygame
from myo_raw import MyoRaw, DataCategory, EMGMode


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
VERBOSE = False


pygame.init()


class Plot():
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.font = pygame.font.Font(None, 30)

        self.last_vals = None

    def plot(self, vals, frequency=None):
        if self.last_vals is None:
            self.last_vals = vals
            return

        D = 5
        self.screen.scroll(-D)
        self.screen.fill((0, 0, 0), (WINDOW_WIDTH - D, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        for i, (u, v) in enumerate(zip(self.last_vals, vals)):
            pygame.draw.line(self.screen, (0, 255, 0),
                             (WINDOW_WIDTH - D, int(WINDOW_HEIGHT / 9 * (i + 1 - u))),
                             (WINDOW_WIDTH, int(WINDOW_HEIGHT / 9 * (i + 1 - v))))
            pygame.draw.line(self.screen, (255, 255, 255),
                             (WINDOW_WIDTH - D, int(WINDOW_HEIGHT / 9 * (i+1))),
                             (WINDOW_WIDTH, int(WINDOW_HEIGHT / 9 * (i+1))))

        if frequency:
            framerate = self.font.render(f"{frequency} Hz", True, pygame.Color("red"))
            self.screen.fill((0, 0, 0), (0, 0, 100, 30))  # Clear old framerate
            self.screen.blit(framerate, (0, 0))

        pygame.display.flip()
        self.last_vals = vals


class Myo():
    def __init__(self, tty, native, mac):
        # Instantiate
        self.myo = MyoRaw(tty, native, mac)
        self.plot = Plot()

        # Variables
        self.paused = False
        # Frequency measuring
        self.times = []
        self.frequency = 0

        # Setup
        self.setup_myo()

    def setup_myo(self):
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
        # Track effective frequency (framerate)
        self.times.append(time.time())
        if len(self.times) >= 100:
            self.frequency = int((len(self.times) - 1) / (self.times[-1] - self.times[0]))
            self.times.clear()

        if not self.paused:
            self.plot.plot([e / 500. for e in emg], frequency=self.frequency)

        if VERBOSE:
            print("emg:", timestamp, emg, moving, characteristic_num)

    def handle_battery(self, timestamp, battery_level):
        if battery_level < 5:
            self.myo.set_leds([255, 0, 0], [255, 0, 0])  # red logo, red bar
        else:
            self.myo.set_leds([128, 128, 255], [128, 128, 255])  # purple logo, purple bar

        if VERBOSE:
            print("battery level:", timestamp, battery_level)

    def pause(self, state=False, toggle=False):
        if toggle:
            self.paused = not self.paused
        else:
            self.paused = state


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Processor")
    parser.add_argument("--sleep", default=False, action="store_true", help="Put Myo into deep sleep (turn off)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group.add_argument("--native", default=False, action="store_true", help="Use a native Bluetooth stack")
    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        global VERBOSE
        VERBOSE = args.verbose

    # Myo setup
    myo = Myo(args.tty, args.native, args.mac)

    if args.sleep:
        myo.myo.deep_sleep()
    else:
        # Run until terminated by user
        try:
            while True:
                myo.myo.run(1)

                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        raise KeyboardInterrupt()
                    elif ev.type == pygame.KEYDOWN:
                        if ev.unicode == 'q':
                            raise KeyboardInterrupt()
                        elif ev.unicode == 'p':
                            myo.pause(toggle=True)
        except KeyboardInterrupt:
            pass
        finally:
            myo.myo.disconnect()


if __name__ == "__main__":
    sys.exit(main())
