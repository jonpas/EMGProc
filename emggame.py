#!/usr/bin/env python3

import sys
import os
import argparse
import serial
import threading

from game.game import MainGame

os.environ["EMGPROC_LOAD_MYO"] = str(True)
import emgproc  # noqa: E402


def myo_thread(stop, stream, tty=None, native=False, mac=None):
    try:
        print("Connecting to Myo...")
        myo = emgproc.Myo(stream, tty, native, mac)
        print("Connected to Myo!")
    except (ValueError, KeyboardInterrupt) as e:
        print(f"Error! Unable to connect!\n{e}")

    while not stop.is_set():
        try:
            myo.run()
        except serial.serialutil.SerialException:
            print("Error! Myo exception! Attempting reboot...")
            myo.disconnect()
            myo = emgproc.Myo(stream, tty, native, mac)

    myo.close()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="SnaPy Myo")
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("--tty", default=None, help="Myo dongle device (autodetected if omitted)")
    group1.add_argument("--native", default=False, action="store_true", help="use a native Bluetooth stack")
    parser.add_argument("--mac", default=None, help="Myo MAC address (arbitrarily detected if omitted)")

    args = parser.parse_args()

    stream = emgproc.Stream(pca_train_set="training/model_2comp.pca",
                            svm_train_set="training/model_pca_2comp.svm",
                            ca_components=2)

    myo_stop = threading.Event()
    myo_runner = threading.Thread(target=myo_thread,
                                  args=(myo_stop, stream, args.tty, args.native, args.mac),
                                  daemon=True)
    myo_runner.start()

    # Game with UI must run in main thread
    MainGame(stream)

    myo_stop.set()

    return 0


if __name__ == "__main__":
    sys.exit(main())
