#!/usr/bin/env python3

import sys
import itertools
import enum
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5 import QtWidgets
from myo_raw import MyoRaw, DataCategory, EMGMode


class MyoStatus(enum.Enum):
    DISCONNECTED = 0
    CONNECTED = 1


class MainWindow(QtWidgets.QWidget):
    sig_myo_stop = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.signal = None
        self.plotbackground = None
        self.plottime = 5  # Seconds
        self.recording = False

        # Myo data
        self.channels = 8
        self.rate = 200

        self.plotsamples = self.plottime * self.rate

        self.initUI()

    # Overriden close event
    def closeEvent(self, event):
        self.sig_myo_stop.emit()

    # Overriden resize event
    def resizeEvent(self, resizeEvent):
        if self.is_signal_loaded():
            self.on_plot_change(None)
        self.plotnav.move(self.width() - 55, 0)

    # UI
    def initUI(self):
        # File selector
        lbl_file = QtWidgets.QLabel("File:")
        self.txt_file = QtWidgets.QLineEdit()
        self.txt_file.setPlaceholderText("Select file ...")
        btn_file = QtWidgets.QPushButton("Select")
        btn_file.clicked.connect(self.show_open_dialog)

        # Save
        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.setDisabled(True)
        self.btn_save.clicked.connect(self.show_save_dialog)

        # Myo status
        self.lbl_status = QtWidgets.QLabel("Myo disconnected")

        # Recording
        self.btn_record = QtWidgets.QPushButton("Record")
        self.btn_record.setMinimumWidth(100)
        self.btn_record.clicked.connect(self.record)

        # Graph space
        self.figure = Figure()
        FigureCanvas(self.figure)
        self.figure.canvas.setMinimumHeight(750)
        self.figure.canvas.mpl_connect("motion_notify_event", self.on_plot_over)

        # Graph toolbar
        self.plotnav = NavigationToolbar(self.figure.canvas, self.figure.canvas)
        self.plotnav.setStyleSheet("QToolBar { border: 0px }")
        self.plotnav.setOrientation(Qt.Vertical)

        # Layout
        hbox_top = QtWidgets.QHBoxLayout()
        hbox_top.addWidget(lbl_file)
        hbox_top.addWidget(self.txt_file)
        hbox_top.addWidget(btn_file)
        hbox_top.addWidget(self.btn_save)
        hbox_top.addStretch()
        hbox_top.addWidget(self.btn_record)

        hbox_bot = QtWidgets.QHBoxLayout()
        hbox_bot.addStretch()
        hbox_bot.addWidget(self.lbl_status)
        hbox_bot.addStretch()

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox_top)
        vbox.addWidget(self.figure.canvas)
        vbox.addLayout(hbox_bot)

        # Window
        self.setLayout(vbox)
        self.setGeometry(300, 300, 1000, 800)
        self.setWindowTitle("Electromyography Processor")
        self.show()

        # Run Myo thread
        self.myo_thread = MyoThread(self.rate, self.channels)
        self.sig_myo_stop.connect(self.myo_thread.stop)
        self.myo_thread.sig_status.connect(self.on_myo_status)
        self.myo_thread.sig_data.connect(self.on_myo_data)
        self.myo_thread.start()

        #self.plot([5, 2, -6, 1, -3, 1, 6 ,6])
        #for i in range(100):
        #    self.plot([])

    def update_ui(self):
        self.btn_save.setDisabled(not self.is_signal_loaded())
        self.btn_record.setText("Stop Recording" if self.recording else "Record")

    # Save / Load
    def show_open_dialog(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, "Open file", filter="CSV (*.csv)")
        if fname[0] and self.load_signal(fname[0]):
            self.txt_file.setText(fname[0])

    def show_save_dialog(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", filter="CSV (*.csv)")
        if fname[0] and self.is_signal_loaded():
            ext = fname[0].rsplit(".", 1)[-1]
            try:
                # TODO Save EmgData to CSV
                pass
            except:
                print("Failed to save signal!")
            else:
                self.txt_file.setText(fname[0])

    def load_emg(self, data, rate, channels):
        # TODO Load EMG into graph
        pass

    def load_signal(self, file):
        try:
            # TODO Load EmgData from CSV
            self.signal = np.array([])
        except:
            print("Failed to load signal!")
            self.signal = None
            return False
        else:
            self.update_ui()
            self.plot(self.signal)
            return True

    def is_signal_loaded(self):
        return self.signal is not None

    # Plotting
    def plot(self, sig):
        # TODO Graph
        self.figure.clear()
        self.subplots = []
        self.lclick = []
        self.lclick_pos = 0
        self.lover = []
        self.lover_pos = 0
        self.lframe = []
        self.lframe_pos = 0

        # X axis as time in seconds
        time = np.linspace(0, 5, num=len(sig))

        for i in range(0, self.channels):
            ax = self.figure.add_subplot(self.channels, 1, i + 1)

            # Plot signal
            ax.plot(time, sig)
            ax.margins(0)
            ax.set_ylim(-128, 128)

            # Hide X axis on all but last channel
            if i + 1 < self.channels:
                ax.get_xaxis().set_visible(False)
            # Display Y label somewhere in the middle
            if i == max(int(self.channels / 2) - 1, 0):
                ax.set_ylabel("Amplitude")

            self.subplots.append(ax)

        ax.set_xlabel("Time (s)")

        # Handle zoom/pan events
        for ax in self.subplots:
            ax.callbacks.connect("xlim_changed", self.on_plot_change)
            ax.callbacks.connect("ylim_changed", self.on_plot_change)

        self.figure.canvas.draw()

        # Save background for updating on the fly
        self.plotbackground = self.figure.canvas.copy_from_bbox(self.figure.bbox)

        # Create lines (for later use, hidden until first update)
        for ax in self.subplots:
            line = ax.axvline(0, linewidth=1, color="black")
            self.lclick.append(line)
            line = ax.axvline(0, linewidth=1, color="grey")
            self.lover.append(line)
            line = ax.axvline(0, linewidth=1, color="blue")
            self.lframe.append(line)

    def on_plot_change(self, axes):
        # Hide all lines to not save them as part of background
        for line in itertools.chain(self.lclick, self.lover, self.lframe):
            line.set_visible(False)

        # Redraw and resave new layout background
        self.figure.canvas.draw()
        self.plotbackground = self.figure.canvas.copy_from_bbox(self.figure.bbox)

        # Reshow all lines
        for line in itertools.chain(self.lclick, self.lover, self.lframe):
            line.set_visible(True)

    def is_plotnav_active(self):
        return self.plotnav._active is None

    def on_plot_over(self, event):
        if not self.is_plotnav_active():
            return

        # Update lines
        if event.xdata is not None and event.ydata is not None:
            self.lover_pos = event.xdata
        else:
            self.lover_pos = 0

        #if self.plotbackground is not None:
            #self.plot_update()

    def plot_update(self):
        self.figure.canvas.restore_region(self.plotbackground)
        for i, (lclick, lover, lframe) in enumerate(zip(self.lclick, self.lover, self.lframe)):
            lclick.set_xdata([self.lclick_pos])
            lover.set_xdata([self.lover_pos])
            lframe.set_xdata([self.lframe_pos])
            self.subplots[i].draw_artist(lclick)
            self.subplots[i].draw_artist(lover)
            self.subplots[i].draw_artist(lframe)
        self.figure.canvas.blit(self.figure.bbox)

    # Myo interface
    def on_myo_status(self, status):
        if status == MyoStatus.CONNECTED:
            self.lbl_status.setText(f"Myo connected")
            self.signal = [0]
        elif status == MyoStatus.DISCONNECTED:
            self.lbl_status.setText(f"Myo disconnected")
            self.signal = None

    def on_myo_data(self, timestamp, emg):
        print('emg:', timestamp, emg)
        if self.is_signal_loaded():
            if len(self.signal) > 5:  #self.plotsamples:
                self.signal.pop(0)
            self.signal.append(emg[0])
            # TODO Change to matplotlib FuncAnimation
            #self.plot(self.signal)

    def record(self):  # Toggle
        if self.recording:
            pass
            #self.sig_myo_stop.emit()
        else:
            self.recording = True
            self.update_ui()


class MyoThread(QThread):
    sig_data = pyqtSignal(float, tuple, object, int)
    sig_status = pyqtSignal(MyoStatus)

    def __init__(self, rate, channels):
        QThread.__init__(self)

        self.rate = rate
        self.channels = channels

        self.myo = None

        self.running = True

    def run(self):
        # DEBUG
        self.sig_data.emit(0.0, (-4, -5, 2, -128, -4, 1, 0, -7))
        pass

        # Setup the BLED112 dongle or a native Bluetooth stack with bluepy and connect to a Myo armband
        self.myo = MyoRaw()
        # Add handler to process EMG
        self.myo.add_handler(DataCategory.EMG, self.emg_handler)
        # Subscribe to all data services
        self.myo.subscribe(EMGMode.RAW)
        # Disable sleep to avoid disconnects while retrieving data
        self.myo.set_sleep_mode(1)
        # Vibrate and change colors (green logo, blue bar) to signalise a successfull setup
        #self.myo.vibrate(1)  # Temporarily disabled during development
        self.myo.set_leds([0, 255, 0], [0, 0, 255])

        self.sig_status.emit(MyoStatus.CONNECTED)

        while self.running:
            self.myo.run(1)

        self.myo.disconnect()
        self.sig_status.emit(MyoStatus.DISCONNECTED)

    def stop(self):
        self.running = False

    def emg_handler(self, timestamp, emg, moving, characteristic_num):
        #print('emg:', timestamp, emg, moving, characteristic_num)
        # Send data to main thread for processing
        self.sig_data.emit(timestamp, emg)


if __name__ == "__main__":
    # Create Qt application with window
    app = QtWidgets.QApplication(sys.argv)
    main_win = MainWindow()

    # Execute application (blocking)
    app.exec_()

    sys.exit(0)
