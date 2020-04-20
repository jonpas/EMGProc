#!/usr/bin/env python3

import sys
import os
import argparse
import csv

import emgproc


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Recording Converter")
    parser.add_argument("recordings", nargs="+", help="recordings to convert")

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("--pca", nargs="+", metavar="REC",
                        help="convert RAW to PCA using given RAW training set or PCA model")
    group1.add_argument("--ica", nargs="+", metavar="REC",
                        help="convert RAW to ICA using given RAW training set or ICA model")

    parser.add_argument("-c", "--components", default=3, type=int, help="PCA/ICA components to use")

    args = parser.parse_args()

    if not args.pca and not args.ica:
        parser.error("the following arguments are required: 'pca' or 'ica'")

    # Model was given instead of train set
    if args.pca is not None and len(args.pca) == 1 and not args.pca[0].endswith(".csv"):
        args.pca = args.pca[0]
    if args.ica is not None and len(args.ica) == 1 and not args.ica[0].endswith(".csv"):
        args.ica = args.ica[0]

    # Setup stream interface (training set)
    stream = emgproc.Stream(pca_train_set=args.pca, ica_train_set=args.ica, ca_components=args.components)
    model, stype = stream.current_model()

    for recording in args.recordings:
        filename = f"recordings/{stype}/{os.path.basename(recording)}"
        print(f"Converting '{recording}' -> '{filename}'...")

        # Setup playback
        playback = emgproc.Playback(stream, recording)
        if not playback.is_valid():
            print(f"-> Error! Invalid CSV file '{recording}'!")
            return 2

        # Write to file on the fly
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", newline="") as emg_file:
            emg_writer = csv.writer(emg_file, csv.unix_dialect, quoting=csv.QUOTE_MINIMAL)
            emg_writer.writerow(emgproc.CSV_HEADER_CA[:args.components + 1])

            # Virtual playback for conversion
            while not stream.ended:
                timestamp, _, ca_data, _ = playback.play_frame()
                if timestamp != 0:
                    csv_data = [timestamp]
                    csv_data.extend(ca_data)
                    emg_writer.writerow(csv_data)

        playback.close()
        stream.reset()

    return 0


if __name__ == "__main__":
    sys.exit(main())
