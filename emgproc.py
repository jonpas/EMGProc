#!/usr/bin/env python3

import sys
import os
import argparse
import time
import serial
import csv
import math
import pickle
from collections import defaultdict

import numpy as np
from sklearn.decomposition import PCA, FastICA
from sklearn.svm import SVC


# Graph
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
PLOT_SCROLL = 3  # higher is faster
CHANNELS = 8
FONT_SIZE = 25
# Data
FREQUENCY = 200  # Hz
CSV_HEADER_EMG = ["timestamp", "emg1", "emg2", "emg3", "emg4", "emg5", "emg6", "emg7", "emg8"]
CSV_HEADER_CA = ["timestamp", "ca1", "ca2", "ca3", "ca4", "ca5", "ca6", "ca7", "ca8"]
# Processing
RMS_WINDOW_SIZE = 50
SVM_WINDOW_SIZE = 10  # higher is smoother but more delay
SVM_IDLE_WEIGHT_FACTOR = 100.0  # higher makes "idle" move more important

VERBOSE = False


# Plotting (Pygame) window interface
class Plotter():
    def __init__(self, live=False):
        if "pygame" not in sys.modules:
            print("Error! pygame not loaded! Plotter not available for library use.")
            return None

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Electromyography Processor")
        self.font = pygame.font.Font(None, FONT_SIZE)

        self.live = live

        self.last_values = None
        self.last_rms_values = None
        self.last_ca_values = None
        self.plots = 0

    def plot(self, values, rms_values=[], ca_values=[], ca="", gesture="", frequency=None, recording=False):
        if self.last_values is None:
            self.last_values = values
            self.last_rms_values = rms_values
            self.last_ca_values = ca_values
            self.plots = len(values) + len(ca_values)
            return

        self.screen.scroll(-PLOT_SCROLL)
        self.screen.fill(pygame.Color("black"), (WINDOW_WIDTH - PLOT_SCROLL, 0, WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen.fill(pygame.Color("black"), (0, 0, 60, WINDOW_HEIGHT))
        self.clear_info()

        # Subplot base
        for i in range(self.plots):
            base_height = self.subplot_height(i)
            pygame.draw.line(self.screen, pygame.Color("darkgrey"),
                             (WINDOW_WIDTH - PLOT_SCROLL, base_height),
                             (WINDOW_WIDTH, base_height))

            if i < 8 and self.plots >= 8:  # Raw / RMS
                plot_text = self.font.render(f"RAW {i}", True, pygame.Color("darkgrey"))
                rms_offset = 10 if rms_values else 0
                if rms_values:
                    plot_rms = self.font.render(f"RMS {i}", True, pygame.Color("blue"))
                    self.screen.blit(plot_rms, (0, base_height - rms_offset - FONT_SIZE // 2))
                self.screen.blit(plot_text, (0, base_height + rms_offset - FONT_SIZE // 2))
            else:  # PCA/ICA
                plot_text = self.font.render(f" {ca.upper()} {i - len(values)}", True, pygame.Color("green"))
                self.screen.blit(plot_text, (0, base_height - FONT_SIZE // 2))

        # Raw signal
        for i, (u, v) in enumerate(zip(self.last_values, values)):
            pygame.draw.line(self.screen, pygame.Color("darkslategrey"),
                             (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i, u)),
                             (WINDOW_WIDTH, self.subplot_height(i, v)))

        # Processed signals
        if rms_values:
            for i, (u, v) in enumerate(zip(self.last_rms_values, rms_values)):
                pygame.draw.line(self.screen, pygame.Color("blue"),
                                 (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i, u)),
                                 (WINDOW_WIDTH, self.subplot_height(i, v)))

        if ca_values:
            for i, (u, v) in enumerate(zip(self.last_ca_values, ca_values)):
                pygame.draw.line(self.screen, pygame.Color("green"),
                                 (WINDOW_WIDTH - PLOT_SCROLL, self.subplot_height(i + len(rms_values), u)),
                                 (WINDOW_WIDTH, self.subplot_height(i + len(rms_values), v)))

        # Information
        if frequency:
            self.render_frequency(frequency)
        self.render_mode()
        self.render_controls(recording)
        if gesture:
            self.render_classification(gesture)

        pygame.display.flip()

        self.last_values = values
        self.last_rms_values = rms_values
        self.last_ca_values = ca_values

    def subplot_height(self, i, value=0):
        scaled_value = value * 1.5
        return int(WINDOW_HEIGHT / (self.plots + 1) * (i + 1 - scaled_value))

    def clear_info(self):
        self.screen.fill(pygame.Color("black"), (0, 0, WINDOW_WIDTH, FONT_SIZE))
        self.screen.fill(pygame.Color("black"), (0, WINDOW_HEIGHT - FONT_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT))

    def render_mode(self):
        mode_text = "LIVE" if self.live else "PLAYBACK"
        mode = self.font.render("LIVE" if self.live else "PLAYBACK",
                                True, pygame.Color("green"))
        self.screen.blit(mode, (WINDOW_WIDTH // 2 - len(mode_text) * FONT_SIZE // 2, 0))

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

    def render_classification(self, gesture):
        plot_gesture = self.font.render(f"Classification: {gesture}", True, pygame.Color("green"))
        self.screen.blit(plot_gesture, (WINDOW_WIDTH // 2 - 225, WINDOW_HEIGHT - FONT_SIZE))

    def pause(self):
        self.clear_info()
        pause = self.font.render("P (resume)", True, pygame.Color("red"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))

        self.render_mode()
        pygame.display.flip()

    def end(self):
        self.clear_info()
        pause = self.font.render("END", True, pygame.Color("red"))
        self.screen.blit(pause, (WINDOW_WIDTH - 250, 0))

        self.render_mode()
        pygame.display.flip()


# Interface for data streaming from either live Myo device or recorded playback
class Stream():
    def __init__(self, do_rms=False, pca_train_set=[], ica_train_set=[], ca_components=3, svm_train_set=[]):
        self.plotter = None  # Late setup (display modes)
        self.reset()

        # Processing
        self.do_rms = do_rms
        self.ca_components = ca_components
        self.pca = self.init_pca(pca_train_set) if pca_train_set else None
        self.ica = self.init_ica(ica_train_set) if ica_train_set else None
        self.svm = self.init_svm(svm_train_set) if svm_train_set else None

    def create_plot(self, live=False):
        self.plotter = Plotter(live=live)

    def plot(self, data, ca=False, recording=False):
        if self.plotter is not None:
            self.calc_frequency()

        # Processing
        rms_data, ca_data, gesture = [], [], ""

        if ca:
            ca_data, data = data, []
        else:
            if self.do_rms or self.pca is not None or self.ica is not None:
                rms_data = self.calc_rms(data)

            ca_data = []
            if self.pca is not None:
                ca_data = self.calc_pca(rms_data)
            elif self.ica is not None:
                ca_data = self.calc_ica(rms_data)

        if self.svm is not None:
            gesture = self.class_svm(ca_data)

        if not self.paused and self.plotter is not None:
            self.plotter.plot([x / 500. for x in data],
                              rms_values=[x / 500. for x in rms_data],
                              ca_values=[x / 500. for x in ca_data],
                              ca=self.current_model()[1],
                              gesture=gesture,
                              frequency=self.frequency,
                              recording=recording)

        return rms_data, ca_data, gesture

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
        if self.plotter is not None:
            self.plotter.end()

    def reset(self):
        self.paused = False
        self.ended = False

        # Frequency measuring
        self.times = []
        self.frequency = 0

        # Processing
        self.rms_window = []
        self.svm_window = []

    # Processing
    def calc_rms(self, data):
        # Gather samples, up to RMS_WINDOW_SIZE
        self.rms_window.append(data)
        if len(self.rms_window) >= RMS_WINDOW_SIZE:
            self.rms_window.pop(0)

        # Calculate RMS for each channel
        rms_data = [0] * CHANNELS
        for channel in range(CHANNELS):
            samples = [item[channel] for item in self.rms_window]
            total = sum([sample ** 2 for sample in samples])
            rms_data[channel] = math.sqrt(1.0 / RMS_WINDOW_SIZE * total)

        if VERBOSE:
            print(f"rms: {rms_data}")

        return rms_data

    def read_ca_train_set(self, train_set, stype="?"):
        emg_data = []

        for file in train_set:
            print(f"Training {stype.upper()} with '{file}'...")

            emg_file = open(file, "r", newline="")
            emg_reader = csv.reader(emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)

            # Read file
            header = next(emg_reader)
            if header == CSV_HEADER_EMG:
                try:
                    while True:
                        data = next(emg_reader)
                        _, emg = data[0], list(map(int, data[1:]))

                        emg_data.append(self.calc_rms(emg))
                except StopIteration:
                    pass
            else:
                print("-> Error! Incorrect header! Expected 'RAW'.")

            self.rms_window.clear()
            emg_file.close()

        emg_data = np.array(emg_data)
        return emg_data

    def read_model(self, model, stype="?"):
        print(f"Reading {stype.upper()} model '{model}'...")
        with open(model, "rb") as f:
            return pickle.load(f)

    def init_pca(self, train_set):
        if isinstance(train_set, list):
            emg_data = self.read_ca_train_set(train_set, "pca")

            # Initialize and train
            pca = PCA(n_components=self.ca_components)
            pca.fit(emg_data)
        else:
            pca = self.read_model(train_set, "pca")

        return pca

    def calc_pca(self, rms_data):
        emg_data = np.array(rms_data).reshape(1, -1)  # Reshape to 1 sample, N features
        pca_data = self.pca.transform(emg_data)[0]  # Take 1 sample from array of samples (contains only one)

        if VERBOSE:
            print(f"pca: {pca_data}")

        return pca_data

    def init_ica(self, train_set):
        if isinstance(train_set, list):
            emg_data = self.read_ca_train_set(train_set, "ica")

            # Initialize and train
            ica = FastICA(n_components=self.ca_components, random_state=0)
            ica.fit(emg_data)
        else:
            ica = self.read_model(train_set, "ica")

        return ica

    def calc_ica(self, rms_data):
        emg_data = np.array(rms_data).reshape(1, -1)  # Reshape to 1 sample, N features
        ica_data = self.ica.transform(emg_data)[0]  # Take 1 sample from array of samples (contains only one)
        ica_data *= 5000  # Scale up

        if VERBOSE:
            print(f"ica: {ica_data}")

        return ica_data

    def read_class_train_set(self, train_set, stype="?"):
        emg_data = []
        classes = []

        for file in train_set:
            classification = os.path.basename(file).split("_")[0]
            print(f"Training {stype.upper()} '{classification}' with '{file}'...")

            emg_file = open(file, "r", newline="")
            emg_reader = csv.reader(emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)

            # Read file
            header = next(emg_reader)
            if header == CSV_HEADER_CA[:self.ca_components - 1]:
                try:
                    while True:
                        data = next(emg_reader)
                        _, emg = data[0], list(map(float, data[1:]))

                        emg_data.append(emg)
                        classes.append(classification)
                except StopIteration:
                    pass
            else:
                print("-> Error! Incorrect header! Expected 'PCA/ICA'.")

            emg_file.close()

        if "idle" not in classes:
            print("Warning! No 'idle' move trained!")

        emg_data, classes = np.array(emg_data), np.array(classes)
        return emg_data, classes

    def init_svm(self, train_set):
        if isinstance(train_set, list):
            emg_data, classes = self.read_class_train_set(train_set, "svm")

            svm = SVC(random_state=0, kernel="rbf", class_weight={"idle": SVM_IDLE_WEIGHT_FACTOR})
            svm.fit(emg_data, classes)
        else:
            svm = self.read_model(train_set, "svm")

        return svm

    def class_svm(self, ca_data):
        # Gather samples, up to SVM_WINDOW_SIZE to smooth classification
        self.svm_window.append(ca_data)
        if len(self.svm_window) > SVM_WINDOW_SIZE:
            self.svm_window.pop(0)

            window = np.array(self.svm_window)
            svm_classes = self.svm.predict(window)  # predict each sample in window

            # Take classification with most occurences in the window
            d = defaultdict(int)
            for svm_class in svm_classes:
                d[svm_class] += 1
            svm_class = max(d.items(), key=lambda x: x[1])[0]

            if VERBOSE:
                print(f"svm: {svm_class}")

            return svm_class
        return ""

    def current_model(self):
        if self.svm is not None:
            return self.svm, "svm"
        elif self.pca is not None:
            return self.pca, "pca"
        elif self.ica is not None:
            return self.ica, "ica"
        return None, ""


# Live Myo device interface
class Myo():
    def __init__(self, stream, tty, native, mac):
        # Instantiate
        self.myo = MyoRaw(tty, native, mac)
        self.stream = stream

        self.recording = False
        self.recording_type = self.init_recording()

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
        _, ca_data, _ = self.stream.plot(emg, recording=self.recording)

        record_data = ca_data if ca_data else emg

        if self.recording:
            csv_data = [timestamp]
            csv_data.extend(record_data)
            try:
                self.emg_writer.writerow(csv_data)
            except AttributeError:
                print("Error! Unable to write to CSV!")

        if VERBOSE:
            print(f"[myo] {self.recording_type}: {timestamp}, {record_data}")

    def handle_battery(self, timestamp, battery_level):
        if battery_level < 5:
            self.myo.set_leds([255, 0, 0], [255, 0, 0])  # red logo, red bar
        else:
            self.myo.set_leds([128, 128, 255], [128, 128, 255])  # purple logo, purple bar

        if VERBOSE:
            print(f"[myo] battery level: {timestamp}, {battery_level}")

    def init_recording(self):
        if self.stream.pca is not None:
            return "pca"
        elif self.stream.ica is not None:
            return "ica"
        return "raw"

    def record(self, state=False, toggle=False):
        if toggle:
            recording = not self.recording
        else:
            recording = state

        if recording:
            filename = f"recordings/{self.recording_type}/{time.strftime('%Y%m%d-%H%M%S')}.csv"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            self.emg_file = open(filename, "w", newline="")
            self.emg_writer = csv.writer(self.emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)
            if self.recording_type == "raw":
                self.emg_writer.writerow(CSV_HEADER_EMG)
            else:
                self.emg_writer.writerow(CSV_HEADER_CA[:self.stream.ca_components - 1])
        elif self.emg_file is not None:
            self.emg_file.close()
            self.emg_file = None
            self.emg_writer = None

        self.recording = recording


# Recorded Myo data playback interface
class Playback():
    def __init__(self, stream, filename):
        self.stream = stream

        self.valid = False
        self.type = ""
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
                self.type = "raw"
            if header[:2] == CSV_HEADER_CA[:2]:
                self.valid = True
                self.type = "ca"
        except StopIteration:
            pass

    def is_valid(self):
        return self.valid

    # Plays a frame from the recording and indicating end of recording on subsequent calls
    def play_frame(self):
        if not self.stream.paused:
            try:
                data = next(self.emg_reader)
                if self.type == "raw":
                    timestamp, emg = data[0], list(map(int, data[1:]))
                    rms_data, ca_data, gesture = self.stream.plot(emg)
                else:
                    timestamp, emg = data[0], list(map(float, data[1:]))
                    rms_data, ca_data, gesture = self.stream.plot(emg, ca=True)

                if VERBOSE:
                    print(f"[playback] emg: {timestamp}, {emg}")

                return timestamp, rms_data, ca_data, gesture
            except StopIteration:
                self.stream.end()
                return 0, [], [], ""


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Processor")

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("-r", "--recording", default=None, metavar="REC", help="playback recorded Myo data stream")
    group1.add_argument("-s", "--sleep", default=False, action="store_true", help="put Myo into deep sleep (turn off)")

    parser.add_argument("--rms", default=False, action="store_true", help="process stream using RMS smoothing")

    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument("--pca", nargs="+", metavar="REC", help="process stream using RAW training set or PCA model")
    group2.add_argument("--ica", nargs="+", metavar="REC", help="process stream using RAW training set or ICA model")
    parser.add_argument("--components", default=3, type=int, help="PCA/ICA components to use")

    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument("--svm", nargs="+", metavar="REC", help="classify using PCA/ICA training set or SVM model")

    group4 = parser.add_mutually_exclusive_group()
    group4.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group4.add_argument("--native", default=False, action="store_true", help="use a native Bluetooth stack")
    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="verbose output")

    args = parser.parse_args()

    if args.svm and not args.pca and not args.ica:
        parser.error("the following arguments are required for 'svm': 'pca' or 'ica'")

    # Model was given instead of trainining set
    if args.pca is not None and len(args.pca) == 1 and not args.pca[0].endswith(".csv"):
        args.pca = args.pca[0]
    if args.ica is not None and len(args.ica) == 1 and not args.ica[0].endswith(".csv"):
        args.ica = args.ica[0]
    if args.svm is not None and len(args.svm) == 1 and not args.svm[0].endswith(".csv"):
        args.svm = args.svm[0]

    if args.verbose:
        global VERBOSE
        VERBOSE = args.verbose

    live_myo = args.recording is None

    # Setup common stream interface for Myo or Playback
    stream = Stream(do_rms=args.rms, pca_train_set=args.pca, ica_train_set=args.ica, svm_train_set=args.svm,
                    ca_components=args.components)

    # Setup Myo or Playback
    if live_myo:
        try:
            myo = Myo(stream, args.tty, args.native, args.mac)
        except ValueError as e:
            print(f"Error! {e}")
            return 1
    else:
        playback = Playback(stream, args.recording)
        if not playback.is_valid():
            print("Error! Invalid CSV file!")
            return 2

    # Run main logic
    if args.sleep:
        myo.myo.deep_sleep()
    else:
        pygame.init()
        stream.create_plot(live=live_myo)

        # Run until terminated by user or recording ended
        try:
            starttime = time.time()
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

                    # Delay by (1 second / FREQUENCY Hz) including execution time
                    delay = 1 / FREQUENCY
                    diff = min(time.time() - starttime, 1 / FREQUENCY)
                    time.sleep(delay - diff)
                    starttime = time.time()

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
    import pygame
    from myo_raw import MyoRaw, DataCategory, EMGMode
    sys.exit(main())
