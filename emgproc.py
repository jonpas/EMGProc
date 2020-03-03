#!/usr/bin/env python3

import sys
import itertools
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5 import QtWidgets


class MainWindow(QtWidgets.QWidget):
    sig_record_stop = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.signal = None
        self.plotbackground = None
        self.recording = False

        self.initUI()

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

        # Recording
        self.cb_sample_rate = QtWidgets.QComboBox()
        self.cb_sample_rate.setToolTip("Sampling rate")
        self.cb_sample_rate.addItems(["50 Hz", "200 Hz"])
        self.cb_sample_rate.setCurrentIndex(1)
        self.sampling_rates = [50, 200]  # Same indexes as text above
        self.btn_record = QtWidgets.QPushButton("Record")
        self.btn_record.setMinimumWidth(100)
        self.btn_record.clicked.connect(self.record)

        # Graph space
        self.figure = Figure()
        FigureCanvas(self.figure)
        self.figure.canvas.setMinimumHeight(400)
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

        hbox_bot = QtWidgets.QHBoxLayout()
        hbox_bot.addStretch()
        hbox_bot.addWidget(self.cb_sample_rate)
        hbox_bot.addWidget(self.btn_record)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox_top)
        vbox.addWidget(self.figure.canvas)
        vbox.addLayout(hbox_bot)

        # Window
        self.setLayout(vbox)
        self.setGeometry(300, 300, 1000, 500)
        self.setWindowTitle("Electromyography Processor")
        self.show()

    # Overriden resize event
    def resizeEvent(self, resizeEvent):
        if self.is_signal_loaded():
            self.on_plot_change(None)
        self.plotnav.move(self.width() - 55, 0)

    def update_ui(self):
        self.btn_save.setDisabled(not self.is_signal_loaded())
        self.btn_record.setText("Stop Recording" if self.recording else "Record")

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
        time = np.linspace(0, len(sig) / 200, num=len(sig))

        ax = self.figure.add_subplot(self.subplots, 1, 1)

        # Plot signal
        ax.plot(time, sig)
        ax.margins(0)

        ax.set_ylabel("Amplitude")
        self.subplots.append(ax)

        self.figure.subplots_adjust(hspace=0.0)
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

        if self.plotbackground is not None:
            self.plot_update()

    def plot_frame(self, x):
        # Update lines
        self.lframe_pos = x
        self.plot_update()

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

    def record(self):  # Toggle
        if self.recording:
            self.sig_record_stop.emit()
        else:
            self.recording = True
            rate = self.sampling_rates[self.cb_sample_rate.currentIndex()]
            self.record_thread = RecordThread(rate, 8)  # Always record all 8 EMG channels
            self.sig_record_stop.connect(self.record_thread.stop)
            self.record_thread.sig_return.connect(self.on_record_return)
            self.record_thread.start()
            self.update_ui()

    def on_record_return(self, data, rate, channels):
        self.load_emg(data, rate, channels)
        self.recording = False
        self.update_ui()


class RecordThread(QThread):
    sig_return = pyqtSignal(bytes, int, int)

    def __init__(self, rate, channels):
        QThread.__init__(self)

        self.rate = rate
        self.channels = channels

        self.running = True

    def __del__(self):
        self.wait()

    def run(self):
        # TODO EmgData

        data = []
        while self.running:
            pass

        # Return recording data
        self.sig_return.emit(b''.join(data), self.rate, self.channels)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    # Create Qt application with window
    app = QtWidgets.QApplication(sys.argv)
    main_win = MainWindow()

    # Execute application (blocking)
    app.exec_()

    sys.exit(0)
