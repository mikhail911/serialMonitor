import threading
import sys 
import os
from time import gmtime, strftime
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui, QtCore, QtWidgets
from sys import platform as _platform

class serialMonitor(QMainWindow):
    reader = pyqtSignal(str)
    arduino = serial.Serial()
    reading = False
    logging = False
    first_conn = True
    input_send_text = ''
    current_port = ''
    current_baud = 9600
    logging_dir = "serialMonitorLogs"
    filename = ''+logging_dir +'/' + strftime("%a-%d-%b-%Y-%H-%M-%S", gmtime()) + '.txt'
    baudrates = ["9600", "115200", "300", "1200", "2400", "4800", "14400", "19200", "31250", "38400", "57600"]

    def __init__(self):
        super(serialMonitor, self).__init__()
        if not os.path.exists(self.logging_dir):
            os.makedirs(self.logging_dir)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.startReadingPorts()
        self.portLabel = QtWidgets.QLabel()
        self.portLabel.setText('Serial port:')
        self.portLabel.move(10, 10)
        self.baudLabel = QtWidgets.QLabel()
        self.baudLabel.setText('Baud rate:')
        self.portBox = QtWidgets.QComboBox()

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

    def serial_ports(self):
        if _platform.startswith('linux'):
            ports = ['/dev/ttyS%s' % (i + 1) for i in range(256)]
        elif _platform.startswith('win32'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif _platform.startswith('darwin'):
            ports = ['/dev/cu.serial%s' % (i + 1) for i in range(256)]
        result = []
        while True:
            for port in ports:
                if port in result:
                    try:
                        s = serial.Serial(port)
                        s.close()
                    except(OSError, serial.SerialException):
                        if port != self.current_port:
                            result.remove(port)
                            self.portBox.removeItem(self.portBox.findText(port))
                else:
                    try:
                        s = serial.Serial(port)
                        s.close()
                        if (self.portBox.findText(port) == -1):
                            result.append(port)
                            self.portBox.addItem(str(port))
                    except (OSError, serial.SerialException):
                        pass
            time.sleep(2)

    def enableScroll(self, state):
        if state == Qt.Checked:
            self.textEdit.moveCursor(QtGui.QTextCursor.End)
        else:
            self.textEdit.moveCursor(QtGui.QTextCursor.Start)

    def startReading(self):
        if not self.reading:
            self.reading = True
            thread = threading.Thread(target=self.read)
            thread.start()

    def startReadingPorts(self):
        thread2 = threading.Thread(target=self.serial_ports)
        thread2.start()

    def read(self):
        self.current_port = str(self.portBox.currentText())
        self.current_baud = int(self.baudBox.currentText())
        if self.first_conn == True:
            self.arduino = serial.Serial(self.current_port, self.current_baud)
        else:
            self.statusbar.showMessage("Reconnecting. Waiting 20s before next connection.")
            time.sleep(20)
            self.arduino = serial.Serial(self.current_port, self.current_baud)
        self.statusbar.showMessage("Connected")
        while self.reading == True:
            try:
                data = self.arduino.readline()[:-1].decode("utf-8", "ignore")
                self.reader.emit(str(data))
            except serial.SerialException:
                self.reader.emit("Disconnect of USB->UART occured. \nRestart needed!")
                self.statusbar.showMessage("Disconnected")
                quit()
        self.arduino.close()

    def sendToSerial(self):
        if self.reading == True:
            self.arduino.write(self.input_send_text.encode())
            self.inputBox.setText('')
        else: 
            self.statusbar.showMessage("Can't send. Create a connection first!")

    def handleTextChange(self):
        self.input_send_text = self.inputBox.text()

    def stopReading(self):
        self.reading = False
        self.first_conn = False
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = serialMonitor()
    window.show()
    sys.exit(app.exec_())