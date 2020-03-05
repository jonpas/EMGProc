#!/usr/bin/env python3

import sys
import argparse
import time
import serial
import csv
import collections

import pygame
from myo_raw import MyoRaw, DataCategory, EMGMode


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLOT_SCROLL = 5  # higher is faster
SUBPLOTS = 8
FONT_SIZE = 25

VERBOSE = False
pygame.init()


class Plot():
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.font = pygame.font.Font(None, FONT_SIZE)

        self.last_vals = None

    def plot(self, vals, frequency=None, recording=False):
        if self.last_vals is None:
            self.last_vals = vals
            return

        self.screen.scroll(-PLOT_SCROLL)
        self.screen.fill(pygame.Color("black"), (WINDOW_WIDTH - PLOT_SCROLL, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        for i, (u, v) in enumerate(zip(self.last_vals, vals)):
            # Signal
            pygame.draw.line(self.screen, pygame.Color("green"),
                             (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i, u)),
                             (WINDOW_WIDTH, self.subplot_height(i, v)))

            base_height = self.subplot_height(i)
            # Subplot base
            pygame.draw.line(self.screen, pygame.Color("white"),
                             (WINDOW_WIDTH - PLOT_SCROLL, base_height),
                             (WINDOW_WIDTH, base_height))

            emg = self.font.render(f"EMG {i}", True, pygame.Color("blue"))
            self.screen.fill(pygame.Color("black"),  # Clear old subplot name
                             (0, base_height - FONT_SIZE // 2, 75, FONT_SIZE))
            self.screen.blit(emg, (0, base_height - FONT_SIZE // 2))

        # Clear old top row
        self.screen.fill(pygame.Color("black"), (0, 0, WINDOW_WIDTH, FONT_SIZE))

        # Control keybinds
        pause = self.font.render("P (pause)", True, pygame.Color("white"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))
        record = self.font.render("R (stop recording)" if recording else "R (record)",
                                  True, pygame.Color("white"))
        self.screen.blit(record, (WINDOW_WIDTH - 150, 0))

        if frequency:
            framerate = self.font.render(f"{frequency} Hz", True,
                                         pygame.Color("green") if frequency > 180 else pygame.Color("red"))
            self.screen.fill(pygame.Color("black"), (0, 0, 75, FONT_SIZE))  # Clear old framerate
            self.screen.blit(framerate, (0, 0))

        pygame.display.flip()
        self.last_vals = vals

    def subplot_height(self, i, value=0):
        return int(WINDOW_HEIGHT / (SUBPLOTS + 1) * (i + 1 - value))


class Myo():
    def __init__(self, tty, native, mac):
        # Instantiate
        self.myo = MyoRaw(tty, native, mac)
        self.plot = Plot()

        # Variables
        self.paused = False
        self.recording = False
        # Frequency measuring
        self.times = []
        self.frequency = 0
        # Recording
        self.emg_file = None
        self.emg_writer = None

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
            self.plot.plot([e / 500. for e in emg],
                           frequency=self.frequency,
                           recording=self.recording)

        if self.recording:
            self.emg_writer.writerow(self.flatten([timestamp, emg]))

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

    def record(self, state=False, toggle=False):
        if toggle:
            self.recording = not self.recording
        else:
            self.recording = state

        if self.recording:
            self.emg_file = open(f"recordings/{time.strftime('%Y%m%d-%H%M%S')}_emg.csv", "w", newline="")
            self.emg_writer = csv.writer(self.emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)
            self.emg_writer.writerow(["timestamp", "emg1", "emg2", "emg3", "emg4", "emg5", "emg6",
                                      "emg7", "emg8", "moving", "characteristic_num"])
        else:
            self.emg_file.close()
            self.emg_file = None
            self.emg_writer = None

    def flatten(self, l):
        for el in l:
            if isinstance(el, collections.Iterable) and not (
                    isinstance(el, (str, bytes))):
                yield from self.flatten(el)
            else:
                yield el


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
                try:
                    myo.myo.run(1)
                except serial.serialutil.SerialException:
                    print("Error! Myo exception! Rebooting ...")
                    myo.myo.disconnect()
                    myo = Myo(args.tty, args.native, args.mac)

                # Handle Pygame events
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        raise KeyboardInterrupt()
                    elif ev.type == pygame.KEYDOWN:
                        if ev.unicode == 'q':
                            raise KeyboardInterrupt()
                        elif ev.unicode == 'p':
                            myo.pause(toggle=True)
                        elif ev.unicode == 'r':
                            myo.record(toggle=True)
        except KeyboardInterrupt:
            pass
        finally:
            myo.myo.disconnect()

            if myo.emg_file is not None:
                myo.emg_file.close()


if __name__ == "__main__":
    sys.exit(main())
