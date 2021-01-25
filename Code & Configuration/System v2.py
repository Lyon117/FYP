import Buzzerlib
from functools import partial, wraps
import MFRC522lib
from os.path import exists, join
from pickle import load
from pprint import pformat
from PyQt5 import QtCore, QtGui, QtWidgets
from re import search
import RPi.GPIO as GPIO
from sys import argv, exit
from time import sleep, time


# Constant
SYSTEM_CONFIGURATION_FILE_PATH = join('.', 'Config.data')
SYSTEM_STATUS_FILE_PATH = join('.', 'Status.data')
SYSTEM_LOG_FILE_PATH = join('.', 'Log.data')


class MFRC522libExtension(MFRC522lib.MFRC522lib):
    '''Contain all RFID related program and value'''
    DEFAULT_KEY = [0xFF] * 6

    def __init__(self):
        super().__init__()
        self.InterruptSignal = False

    def ChecksumAuth(self, uid):
        data = self.GetKey(uid)
        if checksum_algorithm(data[:4]) != data[4] or checksum_algorithm(data[:5]) != data[5]:
            raise self.AuthenticationError
    
    def GetKey(self, uid):
        self.MFRC522_Auth(uid, 1, self.DEFAULT_KEY)
        return self.MFRC522_Read(1)[:6]
    
    def StandardFrame(self, function):   
        @wraps(function)
        def StandardFrame(*args, **kwargs):
            result = None
            buzzer = Buzzerlib.Buzzerlib()
            while not self.InterruptSignal:
                status = self.MFRC522_Request()
                if status == self.OK:
                    try:
                        tap_card_gui.HintLabel.setText('Please hold your card until this window is close')
                        uid = self.MFRC522_Anticoll()
                        self.MFRC522_SelectTag(uid)
                        self.ChecksumAuth(uid)
                        buzzer.notification()
                        kwargs['uid'] = uid
                        kwargs['access_key'] = self.GetKey(uid)
                        result = function(*args, **kwargs)
                        self.MFRC522_StopCrypto1()
                        buzzer.finish()
                        GPIO.cleanup()
                        break
                    except (self.AuthenticationError, self.CommunicationError, self.IntegrityError):
                        tap_card_gui.HintLabel.setText('Please tap your card again')
                        self.MFRC522_StopCrypto1()
                sleep(0.1)
            return result
        return StandardFrame
    
    def Interrupt(self, signal: bool):
        self.InterruptSignal = signal


class Threading(QtCore.QThread):
    def __init__(self, main_program):
        super().__init__()
        self.MainProgram = main_program
        self.Result = None
    
    def run(self):
        self.Result = self.MainProgram()

# System window
class SystemGui(QtWidgets.QWidget):
    '''This is the View session of the system'''
    def __init__(self, frameless):
        super().__init__()
        self.ScreenWidth, self.ScreenHeight, center_point = get_screen_infomation()
        self.setFixedSize(self.ScreenWidth, self.ScreenHeight)
        self.setWindowTitle('System')
        if frameless:
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.CommonFont = QtGui.QFont()
        self.CommonFont.setFamily('Calibri')
        self.CommonFont.setPointSize(36)
        self.setFont(self.CommonFont)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        self.UserInterfaceSetup()
        self.AdminInterfaceSetup()

    def __interface__(self):
        '''Return a list which contain all interface'''
        return [self.UserInterface, self.AdminInterface]

    def UserInterfaceSetup(self):
        # Interface setting
        self.UserInterface = QtWidgets.QFrame(self)
        self.UserInterface.setFixedSize(self.ScreenWidth, self.ScreenHeight)
        self.UserInterfaceLayout = QtWidgets.QGridLayout()
        # First part
        self.SystemNameLabel = QtWidgets.QLabel(self.SystemSetting['system_greeting'])
        self.SystemNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.UserInterfaceLayout.addWidget(self.SystemNameLabel, 0, 0)
        # Second part
        self.LockerButtonFrame = QtWidgets.QFrame()
        self.LockerButtonLayout = QtWidgets.QGridLayout()
        for row in range(self.SystemSetting['locker_row']):
            for column in range(self.SystemSetting['locker_column']):
                index = row * self.SystemSetting['locker_column'] + column
                exec(f'self.LockerButton{index} = QtWidgets.QPushButton(\'{index}\')')
                exec(f'self.LockerButton{index}.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)')
                exec(f'self.LockerButtonLayout.addWidget(self.LockerButton{index}, {row}, {column})')
        self.LockerButtonFrame.setLayout(self.LockerButtonLayout)
        self.UserInterfaceLayout.addWidget(self.LockerButtonFrame, 1, 0, 7, 1)
        # Third part
        self.FunctionButtonFrame = QtWidgets.QFrame()
        self.FunctionButtonLayout = QtWidgets.QGridLayout()
        self.BorrowButton = QtWidgets.QPushButton('Borrow')
        self.BorrowButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.BorrowButton, 0, 0, 1, 2)
        self.ReturnButton = QtWidgets.QPushButton('Return')
        self.ReturnButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.ReturnButton, 0, 2, 1, 2)
        self.CardInfoButton = QtWidgets.QPushButton('CardInfo')
        self.CardInfoButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.CardInfoButton, 0, 4, 1, 2)
        self.AdminGuiButton = QtWidgets.QPushButton('Admin')
        self.AdminGuiButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.AdminGuiButton, 0, 14, 1, 2)
        for i in range(16):
            self.FunctionButtonLayout.setColumnStretch(i, 1)
        self.FunctionButtonFrame.setLayout(self.FunctionButtonLayout)
        self.UserInterfaceLayout.addWidget(self.FunctionButtonFrame, 8, 0)
        # Add widget to main layout
        self.UserInterface.setLayout(self.UserInterfaceLayout)
    
    def AdminInterfaceSetup(self):
        self.AdminInterface = QtWidgets.QFrame(self)
        self.AdminInterface.setFixedSize(self.ScreenWidth, self.ScreenHeight)
        self.AdminInterfaceLayout = QtWidgets.QGridLayout()
        # First part
        self.AdminFunctionFrame = QtWidgets.QFrame()
        self.AdminFunctionLayout = QtWidgets.QGridLayout()
        self.CardInitializationButton = QtWidgets.QPushButton('CardInitialization')
        self.CardInitializationButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.CardInitializationButton, 0, 0)
        self.CardResetButton = QtWidgets.QPushButton('CardReset')
        self.CardResetButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.CardResetButton, 0, 1)
        self.CardDataDumpButton = QtWidgets.QPushButton('CardDataDump')
        self.CardDataDumpButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.CardDataDumpButton, 1, 0)
        self.ExitButton = QtWidgets.QPushButton('Exit')
        self.ExitButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.ExitButton, 1, 1)
        self.AdminFunctionFrame.setLayout(self.AdminFunctionLayout)
        self.AdminInterfaceLayout.addWidget(self.AdminFunctionFrame, 0, 0, 8, 1)
        # Second part
        self.ReturnFrame = QtWidgets.QFrame()
        self.ReturnLayout = QtWidgets.QGridLayout()
        self.UserGuiButton = QtWidgets.QPushButton('User')
        self.UserGuiButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.ReturnLayout.addWidget(self.UserGuiButton, 0, 14, 1, 2)

        self.ReturnFrame.setLayout(self.ReturnLayout)
        self.AdminInterfaceLayout.addWidget(self.ReturnFrame, 8, 0)
        # Add widget to main layout
        self.AdminInterface.setLayout(self.AdminInterfaceLayout)
        self.AdminInterface.hide()


class SystemController(SystemGui):
    '''This is the Controller session of the system'''
    def __init__(self, frameless):
        super().__init__(frameless)
        self.UserFunctionConnection()
        self.AdminFunctionConnection()
    
    def UserFunctionConnection(self):
        self.AdminGuiButton.clicked.connect(partial(self.ShowInterface, 1))

    def AdminFunctionConnection(self):
        self.CardInitializationButton.clicked.connect(lambda: card_initialization_gui.show())
        self.CardResetButton.clicked.connect(lambda: card_reset_gui.show())
        self.CardDataDumpButton.clicked.connect(lambda: card_dump.Execute())
        self.ExitButton.clicked.connect(self.ExitSystem)
        self.UserGuiButton.clicked.connect(partial(self.ShowInterface, 0))
        
    def ShowInterface(self, interface_index):
        for index, interface in enumerate(self.__interface__()):
            if index == interface_index:
                interface.show()
            else:
                interface.hide()


class SystemProgram(SystemController):
    '''This is the Model session of the system'''
    def __init__(self, frameless=True):
        # Get the setting from the configuration file
        self.SystemSetting = self.GetSystemSetting()
        super().__init__(frameless)
    
    def GetSystemSetting(self):
        with open(SYSTEM_CONFIGURATION_FILE_PATH, 'rb') as system_configuration_file:
            system_configuration_data = load(system_configuration_file)
        return system_configuration_data
    
    def ExitSystem(self):
        self.close()


class TapCardGui(QtWidgets.QWidget):
    '''This is the View session of the Tap Card'''
    def __init__(self):
        super().__init__()
        screen_width, screen_height, center_point = get_screen_infomation()
        self.setFixedSize(screen_width // 4, screen_height // 4)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.CommonFont = QtGui.QFont()
        self.CommonFont.setFamily('Calibri')
        self.CommonFont.setPointSize(12)
        self.setFont(self.CommonFont)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle('TapCard')
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.TagCardLabel = QtWidgets.QLabel('Please tap your card')
        self.TagCardLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.HintLabel = QtWidgets.QLabel('')
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.TagCardLabel, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.HintLabel, 1, 0, 1, 3)
        self.MainLayout.addWidget(self.CancelButton, 2, 1, 1, 1)
        self.setLayout(self.MainLayout)


class TapCardController(TapCardGui):
    '''This is the Controller session of the Tap Card'''
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(lambda: mifare_reader.Interrupt(True))
    
    def closeEvent(self, event):
        self.HintLabel.setText('')
        mifare_reader.Interrupt(False)
        event.accept()


class DisplayGui(QtWidgets.QWidget):
    '''This is the View session of Display'''
    def __init__(self):
        super().__init__()
        screen_width, screen_height, center_point = get_screen_infomation()
        self.setFixedSize(screen_width // 2, screen_height // 2)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.CommonFont = QtGui.QFont()
        self.CommonFont.setFamily('Calibri')
        self.CommonFont.setPointSize(12)
        self.setFont(self.CommonFont)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle('Display')
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.TextEdit = QtWidgets.QTextEdit()
        self.MainLayout.addWidget(self.TextEdit, 0, 0, 2, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 1)
        self.setLayout(self.MainLayout)


class DisplayController(DisplayGui):
    '''This is the Controller session of Display'''
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
    
    def closeEvent(self, event):
        self.TextEdit.clear()
        event.accept()


# Function window
class CardInitializationGui(QtWidgets.QWidget):
    '''This is the View session of the Card Initialization'''
    def __init__(self):
        super().__init__()
        screen_width, screen_height, center_point = get_screen_infomation()
        self.setFixedSize(screen_width // 4, screen_height // 4)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.CommonFont = QtGui.QFont()
        self.CommonFont.setFamily('Calibri')
        self.CommonFont.setPointSize(12)
        self.setFont(self.CommonFont)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.HintLabel = QtWidgets.QLabel('Please input:')
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 0, 0, 1, 3)
        self.StudentIdLabel = QtWidgets.QLabel('Student ID:')
        self.StudentIdLabel.setAlignment(QtCore.Qt.AlignRight)
        self.StudentIdLabel.setAlignment(QtCore.Qt.AlignVCenter)
        self.MainLayout.addWidget(self.StudentIdLabel, 1, 0)
        self.StudentIdLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentIdLineEdit, 1, 1, 1, 2)
        self.StudentNameLabel = QtWidgets.QLabel('Student Name:')
        self.StudentNameLabel.setAlignment(QtCore.Qt.AlignRight)
        self.StudentNameLabel.setAlignment(QtCore.Qt.AlignVCenter)
        self.MainLayout.addWidget(self.StudentNameLabel, 2, 0)
        self.StudentNameLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentNameLineEdit, 2, 1, 1, 2)
        self.MainLayout.addWidget(QtWidgets.QLabel(), 3, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 4, 0)
        self.MainLayout.addWidget(QtWidgets.QLabel(), 4, 1)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ComfirmButton, 4, 2)
        self.setLayout(self.MainLayout)


class CardInitializationController(CardInitializationGui):
    '''This is the Controller session of the Card Initialization'''
    StudentIdOkSignal = QtCore.pyqtSignal(bool)
    StudentNameOkSignal = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.StudentIdOkFlag, self.StudentNameOkFlag = False, False
        self.ComfirmButton.setEnabled(False)
        self.CancelButton.clicked.connect(self.close)
        self.StudentIdLineEdit.setMaxLength(8)
        self.StudentIdLineEdit.textChanged.connect(self.StudentIdValidate)
        self.StudentNameLineEdit.setMaxLength(26)
        self.StudentNameLineEdit.textChanged.connect(self.StudentNameValidate)
        self.StudentIdOkSignal.connect(self.StudentIdOk)
        self.StudentNameOkSignal.connect(self.StudentNameOk)
        self.ComfirmButton.clicked.connect(self.CardInitializationPreparation)

    def StudentIdValidate(self, text):
        self.StudentIdOkSignal.emit(False)
        pattern = QtCore.QRegExp('^\d{8}$')
        validator = QtGui.QRegExpValidator(pattern)
        if validator.validate(text, 0)[0] == 2:
            self.StudentIdOkSignal.emit(True)
    
    def StudentNameValidate(self, text):
        self.StudentNameOkSignal.emit(False)
        pattern = QtCore.QRegExp('^[A-Z][a-z]+\s(?:[A-Z][a-z]+\s){0,2}[A-Z][a-z]+$')
        validator = QtGui.QRegExpValidator(pattern)
        if validator.validate(text, 0)[0] == 2:
            self.StudentNameOkSignal.emit(True)
    
    def StudentIdOk(self, value):
        self.StudentIdOkFlag = value
        if self.StudentIdOkFlag and self.StudentNameOkFlag:
            self.ComfirmButton.setEnabled(True)
        else:
            self.ComfirmButton.setEnabled(False)
    
    def StudentNameOk(self, value):
        self.StudentNameOkFlag = value
        if self.StudentIdOkFlag and self.StudentNameOkFlag:
            self.ComfirmButton.setEnabled(True)
        else:
            self.ComfirmButton.setEnabled(False)
    
    def closeEvent(self, event):
        self.StudentIdLineEdit.clear()
        self.StudentNameLineEdit.clear()
        event.accept()


class CardInitializationProgram(CardInitializationController):
    '''This is the Model session of Card Initialization'''
    def __init__(self):
        super().__init__()
    
    def CardInitializationPreparation(self):
        student_id = self.StudentIdLineEdit.text()
        student_id_byte = [(int(student_id) % (256 ** -x)) // (256 ** (-x - 1)) for x in range(-4, 0)]
        first_checksum = checksum_algorithm(student_id_byte)
        student_id_byte += [first_checksum]
        second_checksum = checksum_algorithm(student_id_byte)
        student_id_byte += [second_checksum]
        student_name = self.StudentNameLineEdit.text()
        student_name_byte = [ord(char) for char in student_name]
        student_name_byte += [0] * (26 - len(student_name_byte))
        self.access_key = student_id_byte
        self.student_infomation_byte = student_id_byte + student_name_byte
        self.Execute()
        
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card_gui.show())
        self.Thread.finished.connect(lambda: tap_card_gui.close())
        self.Thread.start()

    def MainProgram(self, uid, access_key):
        mifare_reader.MFRC522_Auth(uid, 3, mifare_reader.DEFAULT_KEY)
        mifare_reader.MFRC522_Write(1, self.student_infomation_byte[:16])
        mifare_reader.MFRC522_Write(2, self.student_infomation_byte[16:])
        for index in range(7, 64, 4):
            try:
                mifare_reader.MFRC522_Auth(uid, index, mifare_reader.DEFAULT_KEY)
                if index == 7:
                    mifare_reader.MFRC522_Write(4, [0] * 16)
                elif index == 11:
                    mifare_reader.MFRC522_Write(8, [1] + [0] * 15)
                    mifare_reader.MFRC522_Write(9, [0] * 16)
                block_data = mifare_reader.MFRC522_Read(index)
                mifare_reader.MFRC522_Write(index, self.access_key + block_data[6:])
            except mifare_reader.AuthenticationError:
                continue
        return


class CardResetGui(QtWidgets.QWidget):
    '''This is the View session of Card Reset'''
    def __init__(self):
        super().__init__()
        screen_width, screen_height, center_point = get_screen_infomation()
        self.setFixedSize(screen_width // 4, screen_height // 4)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.CommonFont = QtGui.QFont()
        self.CommonFont.setFamily('Calibri')
        self.CommonFont.setPointSize(12)
        self.setFont(self.CommonFont)
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.ResetMessageLabel_1 = QtWidgets.QLabel('Are you sure to reset this card.')
        self.ResetMessageLabel_1.setAlignment(QtCore.Qt.AlignCenter)
        self.ResetMessageLabel_2 = QtWidgets.QLabel('All data cannot be recovered!')
        self.ResetMessageLabel_2.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.ResetMessageLabel_1, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.ResetMessageLabel_2, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)


class CardResetController(CardResetGui):
    '''This is the Controller session of Card Reset'''
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(lambda: self.close())
        self.ConfirmButton.clicked.connect(self.Execute)


class CardResetProgram(CardResetController):
    '''This is the Model session of Card Reset'''
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card_gui.show())
        self.Thread.finished.connect(lambda: tap_card_gui.close())
        self.Thread.start()
    
    def MainProgram(self, uid, access_key):
        access_key = access_key if access_key else mifare_reader.GetKey(uid)
        for block in range(0, 64):
            try:
                if block % 4 == 0:
                    key = mifare_reader.DEFAULT_KEY if block == 0 else access_key
                    mifare_reader.MFRC522_Auth(uid, block, key)
                if block == 0:
                    continue
                elif block % 4 != 3:
                    mifare_reader.MFRC522_Write(block, [0] * 16)
                else:
                    block_data = mifare_reader.MFRC522_Read(block)
                    mifare_reader.MFRC522_Write(block, mifare_reader.DEFAULT_KEY + block_data[6:])
            except mifare_reader.AuthenticationError:
                continue


class CardDumpProgram(QtCore.QObject):
    '''This is the Model session of Card Dump'''
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card_gui.show())
        self.Thread.finished.connect(self.DisplayCardData)
        self.Thread.start()
    
    def MainProgram(self, uid, access_key):
        card_data = []
        for sector in range(16):
            key = mifare_reader.DEFAULT_KEY if sector == 0 else access_key
            mifare_reader.MFRC522_Auth(uid, 4 * sector, key)
            card_data.append([mifare_reader.MFRC522_Read(4 * sector + block) for block in range(4)])
        return card_data

    def DisplayCardData(self):
        tap_card_gui.close()
        if self.Thread.Result:
            display_gui.show()
            display_gui.TextEdit.setText(f'{pformat(self.Thread.Result)}')


def get_screen_infomation():
    current_screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
    screen_width = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().width()
    screen_height = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().height()
    center_point = QtWidgets.QApplication.desktop().screenGeometry(current_screen).center()
    return screen_width, screen_height, center_point


def checksum_algorithm(data: list) -> int:
    return sum([data[i] * -i for i in range(-len(data), 0)]) % 251


if __name__ == '__main__':
    if exists(SYSTEM_CONFIGURATION_FILE_PATH) and exists(SYSTEM_STATUS_FILE_PATH) and exists(SYSTEM_LOG_FILE_PATH):
        app = QtWidgets.QApplication(argv)
        mifare_reader = MFRC522libExtension()
        tap_card_gui = TapCardController()
        display_gui = DisplayController()
        system_gui = SystemProgram()
        card_initialization_gui = CardInitializationProgram()
        card_reset_gui = CardResetProgram()
        card_dump = CardDumpProgram()
        system_gui.show()
        exit(app.exec_())
    else:
        print('Some system file cannot be found.')
        print('Please run the system configuration first.')
        for i in range(9, 0, -1):
            print(f'\rThe program will exit after {i}s', end='')
            sleep(1)
        exit(0)
