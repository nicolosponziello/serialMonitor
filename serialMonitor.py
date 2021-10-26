import threading
import sys 
import os
from time import gmtime, sleep, strftime
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui, QtCore, QtWidgets
from sys import platform as _platform
import atexit
import glob
from datetime import datetime

class serialMonitor(QMainWindow):
    reader = pyqtSignal(str)
    serial_port = None
    reading = False
    logging = False
    input_send_text = ''
    current_port = ''
    current_baud = 115200
    logging_dir = "serialMonitorLogs"
    filename = ''+logging_dir +'/' + strftime("%a-%d-%b-%Y-%H-%M-%S", gmtime()) + '.txt'
    baudrates = ["115200", "9600", "300", "1200", "2400", "4800", "14400", "19200", "31250", "38400", "57600"]
    reading_thread = None
    available_ports = []

    def __init__(self):
        super(serialMonitor, self).__init__()
        if not os.path.exists(self.logging_dir):
            os.makedirs(self.logging_dir)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.portLabel = QtWidgets.QLabel()
        self.portLabel.setText('Serial port:')
        self.portLabel.move(10, 10)
        self.baudLabel = QtWidgets.QLabel()
        self.baudLabel.setText('Baud rate:')
        self.portBox = QtWidgets.QComboBox()
        self.reset_btn = QPushButton()
        self.reset_btn.setText("Reboot")
        self.reset_btn.clicked.connect(self.reboot)
        self.clear_btn = QPushButton()
        self.clear_btn.setText("Clear")
        self.clear_btn.clicked.connect(self.clear_output)

        self.baudBox = QtWidgets.QComboBox()
        for i in self.baudrates:
            self.baudBox.addItem(i)
        self.buttonStart = QPushButton()
        self.buttonStart.setText('Start')
        self.buttonStart.clicked.connect(self.startReading)
        self.buttonStop = QPushButton()
        self.buttonStop.setText('Stop')
        self.buttonStop.clicked.connect(self.stopReading)

        self.scroll_button = QCheckBox('Autoscroll')
        self.scroll_button.setCheckState(Qt.Checked)
        self.scroll_button.stateChanged.connect(self.enableScroll)
        self.logging_button = QCheckBox('Enable logging')
        self.logging_button.stateChanged.connect(self.enableLogging)
        self.textEdit = QTextEdit(self)
        self.textEdit.setFontPointSize(10)
        self.reader.connect(self.textEdit.append)
        self.reader.connect(self.writeToFile)
        self.inputBox = QLineEdit(self)
        self.inputBox.textChanged.connect(self.handleTextChange)
        self.inputBox.returnPressed.connect(self.sendToSerial)
        self.sendButton = QPushButton(self)
        self.sendButton.setText('Send')
        self.sendButton.clicked.connect(self.sendToSerial)
        self.statusbar = QStatusBar()
        self.statusbar.showMessage(" ")
        self.setGeometry(100, 100, 860, 640)
        self.setWindowTitle('serialMonitor')
        self.layoutH = QHBoxLayout()
        self.layoutV = QVBoxLayout()
        self.layoutInput = QHBoxLayout()

        self.layoutH.addWidget(self.portLabel)
        self.layoutH.addWidget(self.portBox)
        self.layoutH.addWidget(self.baudLabel)
        self.layoutH.addWidget(self.baudBox)
        self.layoutH.addWidget(self.reset_btn)
        self.layoutH.addWidget(self.clear_btn)
        self.layoutH.addWidget(self.scroll_button)
        self.layoutH.addWidget(self.logging_button)
        self.layoutV.addLayout(self.layoutH)

        self.layoutV.addWidget(self.buttonStart)
        self.layoutV.addWidget(self.buttonStop)
        self.layoutV.addWidget(self.textEdit)
        self.layoutInput.addWidget(self.inputBox)
        self.layoutInput.addWidget(self.sendButton)
        self.layoutV.addLayout(self.layoutInput)
        self.setStatusBar(self.statusbar)
        self.widget = QWidget()
        self.widget.setLayout(self.layoutV)
        self.widget.setFont(font)
        self.setCentralWidget(self.widget)

        self.getAvailablePorts()

    
    def reboot(self):
        self.serial_port.setDTR(False)
        sleep(1)
        self.serial_port.setDTR(True)

    def clear_output(self):
        self.textEdit.clear()


    def getAvailablePorts(self):
        if _platform.startswith('linux'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif _platform.startswith('win32'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif _platform.startswith('darwin'):
            ports = ['/dev/cu.serial%s' % (i + 1) for i in range(256)]
        self.available_ports = []
        for port in ports:
            if port in self.available_ports:
                try:
                    s = serial.Serial(port)
                    s.close()
                except(OSError, serial.SerialException):
                    if port != self.current_port:
                        self.available_ports.remove(port)
                        self.portBox.removeItem(self.portBox.findText(port))
            else:
                try:
                    s = serial.Serial(port)
                    s.close()
                    if (self.portBox.findText(port) == -1):
                        self.available_ports.append(port)
                        self.portBox.addItem(str(port))
                except (OSError, serial.SerialException):
                    pass

    def enableScroll(self, state):
        if state == Qt.Checked:
            self.textEdit.moveCursor(QtGui.QTextCursor.End)
        else:
            self.textEdit.moveCursor(QtGui.QTextCursor.Start)

    def startReading(self):
        if not self.reading:
            self.reading = True
            self.reading_thread = threading.Thread(target=self.read)
            self.reading_thread.setDaemon(True)
            self.reading_thread.start()

    def read(self):
        self.current_port = str(self.portBox.currentText())
        self.current_baud = int(self.baudBox.currentText())
        if self.serial_port is not None:
            self.serial_port.close()
        self.serial_port = serial.Serial(self.current_port, self.current_baud)
        self.statusbar.showMessage("Connected")
        while self.reading == True:
            try:
                data = self.serial_port.readline()[:-1].decode("utf-8", "ignore")
                self.reader.emit(datetime.now().strftime("%H:%M:%S") + ": " + str(data))
            except serial.SerialException:
                self.reader.emit("Disconnect of USB->UART occured. \nRestart needed!")
                self.statusbar.showMessage("Disconnected")
                self.stopReading()
                quit()
        self.serial_port.close()

    def sendToSerial(self):
        if self.reading == True:
            self.serial_port.write(self.input_send_text.encode())
            self.inputBox.setText('')
        else: 
            self.statusbar.showMessage("Can't send. Create a connection first!")

    def handleTextChange(self):
        self.input_send_text = self.inputBox.text()

    def stopReading(self):
        self.reading = False
        self.reading_thread.join()
        self.statusbar.showMessage("Disconnected")

    def enableLogging(self, state):
        if state == Qt.Checked:
            self.logging = True
            file = open(str(self.filename), 'w')
            file.write("serialMonitor log file, created: " + strftime("%a %d %b %Y %H:%M:%S", gmtime()) + "\n")
            file.write("Selected port: " + self.current_port + ", baud rate: " + str(self.current_baud) + "\n")
            file.write("---------------------------------------------------------\n")
            file.close()

    def writeToFile(self, data):
        if self.logging == True:
            file = open(str(self.filename), 'a', encoding='utf-8')
            file.write("" + strftime("%a %d %b %Y %H:%M:%S", gmtime()) + " : ")
            file.write(str(data))
            file.write("\n")
            file.close()

    def cleanup(self):
        if(self.reading_thread is not None):
            self.reading_thread = None
        self.serial_port.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = serialMonitor()
    atexit.register(window.cleanup)
    window.show()
    sys.exit(app.exec_())