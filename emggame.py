#!/usr/bin/env python3

import sys
import os
import argparse

os.environ["EMGPROC_LOAD_MYO"] = str(True)
import emgproc

from game.game import MainGame

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="SnaPy Myo")
    parser.add_argument("--no-myo", default=False, action="store_true", help="use without Myo")
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group1.add_argument("--native", default=False, action="store_true", help="use a native Bluetooth stack")
    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")
    args = parser.parse_args()

    # Initialize EMGProc with real-time Myo input
    stream = emgproc.Stream(pca_train_set="training/model_2comp.pca",
                            svm_train_set="training/model_pca_2comp.svm",
                            ca_components=2)

    if not args.no_myo:
        try:
            print("Connecting to Myo...")
            myo = emgproc.Myo(stream, args.tty, args.native, args.mac)
        except (ValueError, KeyboardInterrupt) as e:
            print(f"Error! Unable to connect!\n{e}")
            return 1

    MainGame()
    return 0


if __name__ == "__main__":
    sys.exit(main())
