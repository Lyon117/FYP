from PyQt5 import QtCore, QtGui, QtWidgets
import sys


class SamplePopupGUI(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        # Setup window
        self.setObjectName('SamplePopupGUI')
        self.resize(220, 110)
        self.setMinimumSize(QtCore.QSize(220, 110))
        self.setMaximumSize(QtCore.QSize(220, 110))
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # Setup widgets
        font = QtGui.QFont()
        font.setFamily('Calibri')
        font.setPointSize(12)
        self.LockerLabel = QtWidgets.QLabel('You have selected Locker X', self)
        self.LockerLabel.setGeometry(QtCore.QRect(0, 0, 220, 30))
        self.LockerLabel.setFont(font)
        self.LockerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.LockerLabel.setObjectName('LockerLabel')
        self.TapCardLabel = QtWidgets.QLabel('Please tap your card', self)
        self.TapCardLabel.setGeometry(QtCore.QRect(0, 30, 220, 30))
        self.TapCardLabel.setFont(font)
        self.TapCardLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.TapCardLabel.setObjectName('TapCardLabel')
        self.Cancelbutton = QtWidgets.QPushButton('Cancel', self)
        self.Cancelbutton.setGeometry(QtCore.QRect(70, 70, 80, 30))
        self.Cancelbutton.setFont(font)
        self.Cancelbutton.setObjectName('Cancelbutton')
        # Functions
        self.Cancelbutton.clicked.connect(self.cancel_application)

    def cancel_application(self):
        self.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    samplepopupgui = SamplePopupGUI()
    samplepopupgui.show()
    sys.exit(app.exec_())
