#!/usr/bin/env python3

import os
import argparse
import csv
import math

import numpy as np
from sklearn.decomposition import PCA


CHANNELS = 8
CSV_HEADER_EMG = ["timestamp", "emg1", "emg2", "emg3", "emg4", "emg5", "emg6", "emg7", "emg8"]
RMS_WINDOW_SIZE = 50


# Parse arguments
parser = argparse.ArgumentParser(description="PCA analysis of electromyography recordings")
parser.add_argument("files", nargs="+", help="")
args = parser.parse_args()

# Prepare
emg_data = []

# Read
for file in args.files:
    print(f"Training with '{os.path.basename(file)}'...")

    emg_file = open(file, "r", newline="")
    emg_reader = csv.reader(emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)

    # Read file
    rms_window = []

    header = next(emg_reader)
    if header == CSV_HEADER_EMG:
        try:
            while True:
                data = next(emg_reader)
                _, emg = data[0], list(map(int, data[1:]))

                # Gather samples, up to RMS_WINDOW_SIZE
                rms_window.append(emg)
                if len(rms_window) >= RMS_WINDOW_SIZE:
                    rms_window.pop(0)

                # Calculate RMS for each channel
                rms_data = [0] * CHANNELS
                for channel in range(CHANNELS):
                    samples = [item[channel] for item in rms_window]
                    total = sum([sample ** 2 for sample in samples])
                    rms_data[channel] = math.sqrt(1.0 / RMS_WINDOW_SIZE * total)

                emg_data.append(rms_data)

        except StopIteration:
            pass

    emg_file.close()

emg_data = np.array(emg_data)
print(f"-> {emg_data.shape[0]} samples")
print(f"-> {emg_data.shape[1]} features (channels)\n")

# Analyse
pca = PCA()
pca.fit(emg_data)

cumsum = np.cumsum(pca.explained_variance_ratio_)  # Energies along axes
[print(f"{i + 1} channels => {int(round(cumprop * 100))} % energy") for i, cumprop in enumerate(cumsum)]
