#!/usr/bin/env python3

import sys
import os
import argparse
import time
import pickle

import emgproc


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Electromyography Model Fitter")

    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("--pca", nargs="+", metavar="REC",
                        help="fit PCA model using given RAW training set")
    group1.add_argument("--ica", nargs="+", metavar="REC",
                        help="fit ICA model using given RAW training set")
    group1.add_argument("--svm", nargs="+", metavar="REC",
                        help="fit SVM model using given PCA/ICA training set")

    parser.add_argument("-c", "--components", default=3, type=int, help="PCA/ICA components to use")

    args = parser.parse_args()

    if not args.pca and not args.ica and not args.svm:
        parser.error("the following arguments are required: 'pca' or 'ica' or 'svm'")

    # Setup stream interface
    stream = emgproc.Stream(pca_train_set=args.pca, ica_train_set=args.ica, svm_train_set=args.svm,
                            ca_components=args.components)
    model, stype = stream.current_model()

    filename = f"training/{time.strftime('%Y%m%d-%H%M%S')}_model.{stype}"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    print(f"Writing to '{filename}'...")
    with open(filename, "wb") as f:
        pickle.dump(model, f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
