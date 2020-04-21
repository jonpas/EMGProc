# FERI-EMGProc

Electromyography Processing application at Neuro, Nano and Quantum Computing (slo. Nevro, Nano in Kvantno Računalništvo).

Includes PCA analysis script and helper applications for processing conversions and model fitment.


## Usage

_Following are most useful usage patterns and do not describe all patterns of the application. Run with `-h` to show all available arguments._

### Core

- `$ emgproc.py` to read raw data at 200 Hz from Myo device.
- `$ emgproc.py -r rec.csv` to playback a CSV recording at 200 Hz.
- _All arguments support recorded and raw data._
- `$ emgproc.py --rms` to smooth the data in real-time.
- `$ emgproc.py --s` to put Myo into deep sleep (shut down).

#### Visualizer Controls

- `R` to record to a CSV file (using selected processing).
- `P` to pause data reading.
- `Q` to quit the application.


### Processing

PCA, ICA and SVM fitting and processing is available in real-time (with visualizer) as well as separate command line mode for conversions and fitting. Example training data is located in `training/` folder.

Process data in real-time:
  - `$ emgproc.py --pca *_raw.csv` fit at start using given training data.
  - `$ emgproc.py --ica model.ica` given training model.

Fit and save model to a file:
  - `$ emgfit.py --pca *_raw.csv` creates `<timestamp>_model.pca`
  - `$ emgfit.py --ica model.ica` creates `<timestamp>_model.ica`

Convert recording to processed recording:
  - `$ emgconvert.py example_raw.csv --pca *_raw.csv` creates `example_pca.csv`


### Game

Small proof of concept game based on [wultes/snapy](https://github.com/wultes/snapy). It features Myo gesture recognition (`extension` and `flexion`) to control snake movement.

Run with `$ python emggame.py` _(using 2 PCA components `2comp` training models)_.

Best gesture recongition is achieved by performing `extension` and `flexion` quickly and slowly returning to the idle position to prevent triggering the opposite gesture on the way back.

![emggame](https://user-images.githubusercontent.com/7935003/79920612-c6649a80-8430-11ea-99a3-4a12f08eefa8.gif)


## Setup

_Targetted at Python 3.8._

- `$ python -m venv venv` (virtual environment)
- `$ source venv/bin/activate`
- `$ pip install -r requirements.txt` (`$ pip freeze > requirements.txt` to update dependencies)
  - _Installs all required packages._

**Dependencies:**
- [scikit-learn](https://scikit-learn.org/)
- [NumPy](https://numpy.org/)
- [myo-raw](https://github.com/jonpas/myo-raw) _(only `emgproc.py` and `emggame.py`)_
- [pySerial](https://pythonhosted.org/pyserial/) _(only `emgproc.py` and `emggame.py`)_
- [PyGame](https://www.pygame.org/) _(only `emgproc.py` and `emggame.py`)_
