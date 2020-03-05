#!/usr/bin/env python3

import sys
import os
import argparse
import time
import serial
import csv
import math

import pygame
from myo_raw import MyoRaw, DataCategory, EMGMode


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
PLOT_SCROLL = 5  # higher is faster
CHANNELS = 8
FONT_SIZE = 25
CSV_HEADER_EMG = ["timestamp", "emg1", "emg2", "emg3", "emg4", "emg5", "emg6", "emg7", "emg8"]
RMS_WINDOW_SIZE = 50

VERBOSE = False


# Plotting (Pygame) window interface
class Plotter():
    def __init__(self, live=False):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Electromyography Processor")
        self.font = pygame.font.Font(None, FONT_SIZE)

        self.live = live

        self.last_values = None
        self.last_rms_values = None

    def plot(self, values, rms_values=[], frequency=None, recording=False):
        if self.last_values is None:
            self.last_values = values
            self.last_rms_values = rms_values
            return

        self.screen.scroll(-PLOT_SCROLL)
        self.screen.fill(pygame.Color("black"), (WINDOW_WIDTH - PLOT_SCROLL, 0, WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen.fill(pygame.Color("black"), (0, 0, 60, WINDOW_HEIGHT))
        self.clear_top()

        # Subplot base
        for i in range(CHANNELS):
            base_height = self.subplot_height(i)
            pygame.draw.line(self.screen, pygame.Color("grey"),
                             (WINDOW_WIDTH - PLOT_SCROLL, base_height),
                             (WINDOW_WIDTH, base_height))

            emg = self.font.render(f"EMG {i}", True, pygame.Color("blue"))
            self.screen.blit(emg, (0, base_height - FONT_SIZE // 2))

        # Raw signal
        for i, (u, v) in enumerate(zip(self.last_values, values)):
            pygame.draw.line(self.screen, pygame.Color("white"),
                             (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i, u)),
                             (WINDOW_WIDTH, self.subplot_height(i, v)))

        # Processed signals
        if rms_values:
            for i, (u, v) in enumerate(zip(self.last_rms_values, rms_values)):
                pygame.draw.line(self.screen, pygame.Color("green"),
                                 (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i, u)),
                                 (WINDOW_WIDTH, self.subplot_height(i, v)))

        # Information
        if frequency:
            self.render_frequency(frequency)
        self.render_mode()
        self.render_controls(recording)

        pygame.display.flip()

        self.last_values = values
        self.last_rms_values = rms_values

    def subplot_height(self, i, value=0):
        scaled_value = value * 1.5
        return int(WINDOW_HEIGHT / (CHANNELS + 1) * (i + 1 - scaled_value))

    def clear_top(self):
        self.screen.fill(pygame.Color("black"), (0, 0, WINDOW_WIDTH, FONT_SIZE))

    def render_mode(self):
        mode_text = "LIVE" if self.live else "PLAYBACK"
        mode = self.font.render("LIVE" if self.live else "PLAYBACK",
                                True, pygame.Color("green"))
        self.screen.blit(mode, (WINDOW_WIDTH - WINDOW_WIDTH // 2 - len(mode_text) * FONT_SIZE // 2, 0))

    def render_frequency(self, frequency):
        framerate = self.font.render(f"{frequency} Hz", True,
                                     pygame.Color("green") if frequency > 180 else pygame.Color("red"))
        self.screen.fill(pygame.Color("black"), (0, 0, 75, FONT_SIZE))  # Clear old framerate
        self.screen.blit(framerate, (0, 0))

    def render_controls(self, recording):
        pause = self.font.render("P (pause)", True, pygame.Color("white"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))

        if self.live:  # Can only record live
            record = self.font.render("R (stop rec)" if recording else "R (record)", True,
                                      pygame.Color("red") if recording else pygame.Color("white"))
            self.screen.blit(record, (WINDOW_WIDTH - 150, 0))

    def pause(self):
        self.clear_top()
        pause = self.font.render("P (resume)", True, pygame.Color("red"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))

        self.render_mode()
        pygame.display.flip()

    def end(self):
        self.clear_top()
        pause = self.font.render("END", True, pygame.Color("red"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))

        self.render_mode()
        pygame.display.flip()


# Interface for data streaming from either live Myo device or recorded playback
class Stream():
    def __init__(self, do_rms=False):
        self.do_rms = do_rms
        self.plotter = None  # Late setup (display modes)

        self.paused = False
        self.ended = False

        # Frequency measuring
        self.times = []
        self.frequency = 0

        # RMS
        self.rms_window = []

    def create_plot(self, live=False):
        self.plotter = Plotter(live=live)

    def plot(self, data, recording=False):
        self.calc_frequency()

        # Processing
        rms_data = []
        if self.do_rms:
            rms_data = self.rms(data)

        if not self.paused:
            self.plotter.plot([x / 500. for x in data],
                              rms_values=[x / 500. for x in rms_data],
                              frequency=self.frequency,
                              recording=recording)

    def calc_frequency(self):
        self.times.append(time.time())
        if len(self.times) >= 100:
            self.frequency = int((len(self.times) - 1) / (self.times[-1] - self.times[0]))
            self.times.clear()

    def pause(self, state=False, toggle=False):
        if toggle:
            self.paused = not self.paused
        else:
            self.paused = state

        if self.paused and not self.ended:
            self.plotter.pause()

    def end(self):
        self.ended = True
        self.plotter.end()

    # Processing
    def rms(self, data):
        # Gather samples, up to RMS_WINDOW_SIZE
        self.rms_window.append(data)
        if len(self.rms_window) >= RMS_WINDOW_SIZE:
            self.rms_window.pop(0)

        # Calculate RMS for each channel
        rms_data = [0] * CHANNELS
        for channel in range(CHANNELS):
            data_channel = [item[channel] for item in self.rms_window]
            rms_data[channel] = self.calc_rms(data_channel)

        if VERBOSE:
            print("rms:", rms_data)

        return rms_data

    def calc_rms(self, samples):
        total = 0
        for sample in samples:
            total += sample**2

        return math.sqrt(1.0 / RMS_WINDOW_SIZE * total)


# Live Myo device interface
class Myo():
    def __init__(self, stream, tty, native, mac):
        # Instantiate
        self.myo = MyoRaw(tty, native, mac)
        self.stream = stream

        self.recording = False

        # Recording
        self.emg_file = None
        self.emg_writer = None

        # Setup
        self.setup_myo()

    def close(self):
        self.myo.disconnect()
        self.record(False)

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
        emg = list(emg)
        self.stream.plot(emg, recording=self.recording)

        if self.recording:
            data = [timestamp] + emg
            self.emg_writer.writerow(data)

        if VERBOSE:
            print("[myo] emg:", timestamp, emg)

    def handle_battery(self, timestamp, battery_level):
        if battery_level < 5:
            self.myo.set_leds([255, 0, 0], [255, 0, 0])  # red logo, red bar
        else:
            self.myo.set_leds([128, 128, 255], [128, 128, 255])  # purple logo, purple bar

        if VERBOSE:
            print("[myo] battery level:", timestamp, battery_level)

    def record(self, state=False, toggle=False):
        if toggle:
            self.recording = not self.recording
        else:
            self.recording = state

        if self.recording:
            filename = f"recordings/{time.strftime('%Y%m%d-%H%M%S')}_emg.csv"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.emg_file = open(filename, "w", newline="")
            self.emg_writer = csv.writer(self.emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)
            self.emg_writer.writerow(CSV_HEADER_EMG)
        elif self.emg_file is not None:
            self.emg_file.close()
            self.emg_file = None
            self.emg_writer = None


# Recorded Myo data playback interface
class Playback():
    def __init__(self, stream, filename):
        self.stream = stream

        self.valid = False
        try:
            self.emg_file = open(filename, "r", newline="")
            self.emg_reader = csv.reader(self.emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)
            self.read_header()
        except FileNotFoundError:
            self.emg_file = None

    def close(self):
        if self.emg_file:
            self.emg_file.close()

    def read_header(self):
        try:
            header = next(self.emg_reader)
            if header == CSV_HEADER_EMG:
                self.valid = True
        except StopIteration:
            pass

    def is_valid(self):
        return self.valid

    # Plays a frame from the recording and indicating end of recording on subsequent calls
    def play_frame(self):
        if not self.stream.paused:
            try:
                data = next(self.emg_reader)
                timestamp, emg = data[0], list(map(int, data[1:]))
                self.stream.plot(emg)

                if VERBOSE:
                    print("[playback] emg:", timestamp, emg)
            except StopIteration:
                self.stream.end()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Processor")

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("-r", "--recording", default=None, help="Playback recorded Myo data stream")
    group1.add_argument("-s", "--sleep", default=False, action="store_true", help="Put Myo into deep sleep (turn off)")

    parser.add_argument("--rms", default=False, action="store_true",
                        help="Preprocess data stream using root mean square smoothing")

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group2.add_argument("--native", default=False, action="store_true", help="Use a native Bluetooth stack")

    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        global VERBOSE
        VERBOSE = args.verbose

    live_myo = args.recording is None

    # Setup common stream interface for Myo or Playback
    stream = Stream(do_rms=args.rms)

    # Setup Myo or Playback
    if live_myo:
        myo = Myo(stream, args.tty, args.native, args.mac)
    else:
        playback = Playback(stream, args.recording)
        if not playback.is_valid():
            print("Error! Invalid CSV file!")
            return 1

    # Run main logic
    if args.sleep:
        myo.myo.deep_sleep()
    else:
        pygame.init()
        stream.create_plot(live=live_myo)

        # Run until terminated by user or recording ended
        try:
            while True:
                if live_myo:
                    try:
                        myo.myo.run(1)
                    except serial.serialutil.SerialException:
                        print("Error! Myo exception! Attempting reboot...")
                        myo.myo.disconnect()
                        myo = Myo(stream, args.tty, args.native, args.mac)
                else:
                    playback.play_frame()
                    time.sleep(0.0038)  # 1 second / 200 = 200 Hz + orchestration

                # Handle Pygame events
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        raise KeyboardInterrupt()
                    elif ev.type == pygame.KEYDOWN:
                        if ev.unicode == 'q':
                            raise KeyboardInterrupt()
                        elif ev.unicode == 'p':
                            stream.pause(toggle=True)
                        elif ev.unicode == 'r':
                            if live_myo:
                                myo.record(toggle=True)
        except KeyboardInterrupt:
            pass

    if live_myo:
        myo.close()
    else:
        playback.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
