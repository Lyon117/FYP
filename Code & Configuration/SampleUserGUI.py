from PyQt5 import QtCore, QtGui, QtWidgets
import sys


class SampleUserGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Setup window
        self.setObjectName('SampleUserGUI')
        self.resize(1024, 600)
        self.setMinimumSize(QtCore.QSize(1024, 600))
        self.setMaximumSize(QtCore.QSize(1024, 600))
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # Setup widgets
        font = QtGui.QFont()
        font.setFamily('Calibri')
        font.setPointSize(72)
        self.Locker1Button = QtWidgets.QPushButton('1', self)
        self.Locker1Button.setGeometry(QtCore.QRect(15, 15, 180, 180))
        self.Locker1Button.setFont(font)
        self.Locker1Button.setObjectName('Locker1Button')
        self.Locker2Button = QtWidgets.QPushButton('2', self)
        self.Locker2Button.setGeometry(QtCore.QRect(210, 15, 180, 180))
        self.Locker2Button.setFont(font)
        self.Locker2Button.setObjectName('Locker2Button')
        self.Locker3Button = QtWidgets.QPushButton('3', self)
        self.Locker3Button.setGeometry(QtCore.QRect(405, 15, 180, 180))
        self.Locker3Button.setFont(font)
        self.Locker3Button.setObjectName('Locker3Button')
        self.Locker4Button = QtWidgets.QPushButton('4', self)
        self.Locker4Button.setGeometry(QtCore.QRect(15, 210, 180, 180))
        self.Locker4Button.setFont(font)
        self.Locker4Button.setObjectName('Locker4Button')
        self.Locker5Button = QtWidgets.QPushButton('5', self)
        self.Locker5Button.setGeometry(QtCore.QRect(210, 210, 180, 180))
        self.Locker5Button.setFont(font)
        self.Locker5Button.setObjectName('Locker5Button')
        self.Locker6Button = QtWidgets.QPushButton('6', self)
        self.Locker6Button.setGeometry(QtCore.QRect(405, 210, 180, 180))
        self.Locker6Button.setFont(font)
        self.Locker6Button.setObjectName('Locker6Button')
        self.Locker7Button = QtWidgets.QPushButton('7', self)
        self.Locker7Button.setGeometry(QtCore.QRect(15, 405, 180, 180))
        self.Locker7Button.setFont(font)
        self.Locker7Button.setObjectName('Locker7Button')
        self.Locker8Button = QtWidgets.QPushButton('8', self)
        self.Locker8Button.setGeometry(QtCore.QRect(210, 405, 180, 180))
        self.Locker8Button.setFont(font)
        self.Locker8Button.setObjectName('Locker8Button')
        self.Locker9Button = QtWidgets.QPushButton('9', self)
        self.Locker9Button.setGeometry(QtCore.QRect(405, 405, 180, 180))
        self.Locker9Button.setFont(font)
        self.Locker9Button.setObjectName('Locker9Button')
        font.setPointSize(36)
        self.BorrowButton = QtWidgets.QPushButton('Borrow', self)
        self.BorrowButton.setGeometry(QtCore.QRect(600, 15, 180, 180))
        self.BorrowButton.setFont(font)
        self.BorrowButton.setObjectName('BorrowButton')
        self.ReturnButton = QtWidgets.QPushButton('Return', self)
        self.ReturnButton.setGeometry(QtCore.QRect(795, 15, 180, 180))
        self.ReturnButton.setFont(font)
        self.ReturnButton.setObjectName('ReturnButton')
        self.ExitButton = QtWidgets.QPushButton('Exit', self)
        self.ExitButton.setGeometry(QtCore.QRect(795, 405, 180, 180))
        self.ExitButton.setFont(font)
        self.ExitButton.setObjectName('ExitButton')
        # Functions
        self.Locker1Button.clicked.connect(self.locker1_function)
        self.Locker2Button.clicked.connect(self.locker2_function)
        self.Locker3Button.clicked.connect(self.locker3_function)
        self.Locker4Button.clicked.connect(self.locker4_function)
        self.Locker5Button.clicked.connect(self.locker5_function)
        self.Locker6Button.clicked.connect(self.locker6_function)
        self.Locker7Button.clicked.connect(self.locker7_function)
        self.Locker8Button.clicked.connect(self.locker8_function)
        self.Locker9Button.clicked.connect(self.locker9_function)
        self.BorrowButton.clicked.connect(self.borrow_function)
        self.ReturnButton.clicked.connect(self.return_function)
        self.ExitButton.clicked.connect(self.exit_application)
    
    def locker1_function(self):
        self.locker_function('1')
    
    def locker2_function(self):
        self.locker_function('2')
    
    def locker3_function(self):
        self.locker_function('3')
    
    def locker4_function(self):
        self.locker_function('4')
    
    def locker5_function(self):
        self.locker_function('5')
    
    def locker6_function(self):
        self.locker_function('6')
    
    def locker7_function(self):
        self.locker_function('7')
    
    def locker8_function(self):
        self.locker_function('8')
    
    def locker9_function(self):
        self.locker_function('9')

    def borrow_function(self):
        self.locker_function('borrow')
    
    def return_function(self):
        self.locker_function('return')

    def locker_function(self, user_selection):
        pass

    def exit_application(self):
        self.close()
    
    def locker_list(self):
        return self.Locker1Button, self.Locker2Button, self.Locker3Button, self.Locker4Button, self.Locker5Button, self.Locker6Button, self.Locker7Button, self.Locker8Button, self.Locker9Button


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    sampleusergui = SampleUserGUI()
    sampleusergui.show()
    sys.exit(app.exec_())
