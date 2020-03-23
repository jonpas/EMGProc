#!/usr/bin/env python3

import os
import argparse
import csv

import numpy as np
from sklearn.decomposition import PCA


CHANNELS = 8
CSV_HEADER_EMG = ["timestamp", "emg1", "emg2", "emg3", "emg4", "emg5", "emg6", "emg7", "emg8"]


# Parse arguments
parser = argparse.ArgumentParser(description="PCA analysis of electromyography recordings")
parser.add_argument("files", help="Playback recorded Myo data streams", nargs="+")
args = parser.parse_args()

# Prepare
emg_data = []

# Read
for file in args.files:
    print(f"Reading '{os.path.basename(file)}'...")

    emg_file = open(file, "r", newline="")
    emg_reader = csv.reader(emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)

    # Read file
    header = next(emg_reader)
    if header == CSV_HEADER_EMG:
        try:
            while True:
                data = next(emg_reader)
                _, emg = data[0], list(map(int, data[1:]))
                emg_data.append(emg)
        except StopIteration:
            pass

    emg_file.close()

emg_data = np.array(emg_data)
print(f"-> {emg_data.shape[0]} samples")
print(f"-> {emg_data.shape[1]} features (channels)\n")

# Analyse
pca = PCA()
pca.fit(emg_data)

pca_cumsum = np.cumsum(pca.explained_variance_ratio_)  # Energies along axes
[print(f"{i + 1} channels => {int(round(cumprop * 100))} % energy") for i, cumprop in enumerate(pca_cumsum)]
