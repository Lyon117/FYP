import Buzzerlib
from functools import partial, wraps
import MFRC522lib
from os.path import exists, join
from pickle import dump, load
from pprint import pformat
from PyQt5 import QtCore, QtGui, QtWidgets
import RPi.GPIO as GPIO
# import Saveuser #
from sys import argv, exit
from time import localtime, sleep, strftime, time
from typing import Union


# Constant
SYSTEM_CONFIGURATION_FILE_PATH = join('.', 'Config.data')
SYSTEM_STATUS_FILE_PATH = join('.', 'Status.data')
SYSTEM_LOG_FILE_PATH = join('.', 'Log.data')


class MFRC522libExtension(MFRC522lib.MFRC522lib):
    '''Contain all RFID related program and value'''
    DEFAULT_KEY = [0xFF] * 6
    
    class UnmatchError(BaseException): pass

    def __init__(self):
        super().__init__()

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
            self.InterruptSignal = False
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
    
    def Interrupt(self):
        self.InterruptSignal = True


class GetCurrentTime(QtCore.QThread):
    time_trigger = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            current_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
            self.time_trigger.emit(current_time)
            sleep(0.1)


class Threading(QtCore.QThread):
    def __init__(self, main_program):
        super().__init__()
        self.MainProgram = main_program
        self.Result = None
    
    def run(self):
        self.Result = self.MainProgram()


class Converter:
    @staticmethod
    def StudentId(student_id_data: Union[int, list]) -> Union[list, int]:
        '''Return a list if an int is input, return an int if a list with length 6 is input.'''
        if student_id_data.__class__ == int:
            return [(int(student_id_data) % (256 ** -x)) // (256 ** (-x - 1)) for x in range(-4, 0)]
        elif student_id_data.__class__ == list and student_id_data.__len__() == 6:
            return sum([student_id_data[:4][i] * (256 ** (-i - 1)) for i in range(-4, 0)])
        else:
            raise TypeError('Input value should be an int or list with length 6.')

    @staticmethod
    def AddChecksum(student_id_byte_list: list) -> list:
        '''Add the checksum after the student id byte list.'''
        if student_id_byte_list.__class__ == list and student_id_byte_list.__len__() == 4:
            first_checksum = checksum_algorithm(student_id_byte_list)
            student_id_byte_list += [first_checksum]
            second_checksum = checksum_algorithm(student_id_byte_list)
            student_id_byte_list += [second_checksum]
            return student_id_byte_list
        else:
            raise TypeError('Input value should be a list with length 4.')
    
    @staticmethod
    def StudentName(student_name_data: Union[str, list]) -> Union[list, str]:
        '''Return a list if a str is input, return a str if a list is input.'''
        if student_name_data.__class__ == str:
            student_name_byte_list = [ord(char) for char in student_name_data]
            if len(student_name_byte_list) <= 26:
                student_name_byte_list += [0] * (26 - len(student_name_byte_list))
            else:
                student_name_byte_list = student_name_byte_list[:26]
            return student_name_byte_list
        elif student_name_data.__class__ == list:
            return ''.join([chr(byte) for byte in student_name_data if byte])
        else:
            raise TypeError('Input value should be a str or a list')
    
    @staticmethod
    def Balance(balance_data: list) -> int:
        '''Return an int if a list with length 16 is input.'''
        if balance_data.__class__ == list and balance_data.__len__() == 16:
            balance = sum([balance_data[1:][i] * (256 ** (-i - 1)) for i in range(-15, 0)])
            return balance if balance_data[0] == 0 else -balance
        else:
            raise TypeError('Input value should be a list with length 16')
    
    HistoryRecordByte = [list, list, list]
    @staticmethod
    def HistoryRecord(history_data: HistoryRecordByte) -> list:
        if history_data.__class__ == list and history_data.__len__() == 3:
            locker_data = history_data[0] + history_data[1]
            locker_name = Converter.SystemName(locker_data[:30])
            locker_no = Converter.LockerIndex(locker_data[30:])
            start_time = Converter.Time(history_data[2][:8])
            end_time = Converter.Time(history_data[2][8:])
            return [locker_name, locker_no, start_time, end_time]
        else:
            raise TypeError('Input value should be a list with length 3')
    
    @staticmethod
    def SystemName(system_name_data: Union[str, list]) -> Union[list, str]:
        if system_name_data.__class__ == str:
            system_name_byte_list = [ord(char) for char in system_name_data]
            if len(system_name_byte_list) <= 30:
                system_name_byte_list += [0] * (30 - len(system_name_byte_list))
            else:
                system_name_byte_list = system_name_byte_list[:30]
            return system_name_byte_list
        elif system_name_data.__class__ == list:
            system_name = ''.join([chr(x) for x in system_name_data[:30] if x])
            return system_name
        else:
            raise TypeError('Input value should be a str or a list')
    
    @staticmethod
    def LockerIndex(locker_index_data: Union[int, list]) -> Union[list, int]:
        if locker_index_data.__class__ == int and locker_index_data <= 256 ** 2 - 1:
            return [locker_index_data // 256, locker_index_data % 256]
        elif locker_index_data.__class__ == list:
            return sum([locker_index_data[i] * (256 ** (-i - 1)) for i in range(-2, 0)])
        else:
            raise TypeError('Input value should be an integer less than 256 ** 2 - 1 or a list')
    
    @staticmethod
    def Time(time_data: Union[int, list]) -> Union[list, int]:
        if time_data.__class__ == int:
            return [(time_data % (256 ** -i)) // (256 ** (-i - 1)) for i in range(-8, 0)]
        elif time_data.__class__ == list:
            return sum([time_data[i] * (256 ** (-i - 1)) for i in range(-8, 0)])
        else:
            raise TypeError('Input value should be an integer or a list')


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
        self.FunctionButtonLayout.addWidget(self.BorrowButton, 0, 0, 2, 2)
        self.ReturnButton = QtWidgets.QPushButton('Return')
        self.ReturnButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.ReturnButton, 0, 2, 2, 2)
        self.CardInfoButton = QtWidgets.QPushButton('CardInfo')
        self.CardInfoButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.CardInfoButton, 0, 4, 2, 2)
        self.TimeLabel = QtWidgets.QLabel()
        self.TimeLabel.setAlignment(QtCore.Qt.AlignRight)
        self.FunctionButtonLayout.addWidget(self.TimeLabel, 1, 8, 1, 8)
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
        # Authentication key
        self.AuthenticationKey = [1, 2, 4, 4, 4]
        self.InputAuthenticationKey = []
        self.LockerButtonConnection()
        self.UserFunctionConnection()
        self.AdminFunctionConnection()
        self.LockerStatusRefresh()
    
    def UserFunctionConnection(self):
        self.BorrowButton.clicked.connect(lambda: locker_borrow_gui.LockerSelection())
        self.CardInfoButton.clicked.connect(lambda: card_info.Execute())
        self.CurrentTime = GetCurrentTime()
        self.CurrentTime.start()
        self.CurrentTime.time_trigger.connect(self.Display)
    
    def Display(self, current_time):
        self.TimeLabel.setText(f'Current Time: {current_time}')

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
    
    def mousePressEvent(self, event):
        if self.UserInterface.isVisible():
            self.AdminInterfaceAuthentication(event.x(), event.y())

    def AdminInterfaceAuthentication(self, position_x, position_y):
        if position_x in range(0, self.ScreenWidth//16) and position_y in range(0, self.ScreenHeight//9):
            self.InputAuthenticationKey.append(1)
        elif position_x in range(self.ScreenWidth-self.ScreenWidth//16, self.ScreenWidth) and position_y in range(0, self.ScreenHeight//9):
            self.InputAuthenticationKey.append(2)
        elif position_x in range(0, self.ScreenWidth//16) and position_y in range(self.ScreenHeight-self.ScreenHeight//9, self.ScreenHeight):
            self.InputAuthenticationKey.append(3)
        elif position_x in range(self.ScreenWidth-self.ScreenWidth//16, self.ScreenWidth) and position_y in range(self.ScreenHeight-self.ScreenHeight//9, self.ScreenHeight):
            self.InputAuthenticationKey.append(4)
        if len(self.InputAuthenticationKey) >= 1:
            for index, position in enumerate(self.AuthenticationKey):
                try:
                    if self.InputAuthenticationKey[index] != position:
                        self.InputAuthenticationKey = []
                        break
                    if self.InputAuthenticationKey == self.AuthenticationKey:
                        self.InputAuthenticationKey = []
                        self.ShowInterface(1)
                except IndexError:
                    break
    
    def LockerButtonConnection(self):
        locker_total = self.SystemSetting['locker_row'] * self.SystemSetting['locker_column']
        for i in range(locker_total):
            exec(f'self.LockerButton{i}.clicked.connect(partial(self.LockerController, {i}))')
    
    def LockerController(self, locker_index):
        locker_index = str(locker_index)
        if self.SystemStatus[locker_index]['availability'] == 1:
            locker_borrow_gui.GetLockerIndex(locker_index)
        elif self.SystemStatus[locker_index]['availability'] == 0:
            locker_return_gui.GetLockerIndex(locker_index)


class SystemProgram(SystemController):
    '''This is the Model session of the system'''
    def __init__(self, frameless=True):
        # Get the setting from the configuration file
        self.SystemSetting = self.GetSystemSetting()
        self.SystemStatus = self.GetSystemStatus()
        super().__init__(frameless)
    
    def GetSystemSetting(self):
        with open(SYSTEM_CONFIGURATION_FILE_PATH, 'rb') as system_configuration_file:
            system_configuration_data = load(system_configuration_file)
        return system_configuration_data
    
    def GetSystemStatus(self):
        with open(SYSTEM_STATUS_FILE_PATH, 'rb') as system_status_file:
            system_status_data = load(system_status_file)
        return system_status_data
    
    def ExitSystem(self):
        self.close()
    
    def LockerStatusRefresh(self):
        for locker in self.SystemStatus.keys():
            if self.SystemStatus[locker]['availability'] == 1:
                exec(f'self.LockerButton{locker}.setStyleSheet("background-color: green; border: none; font-size: 36px; font-family: Calibri")')
            else:
                exec(f'self.LockerButton{locker}.setStyleSheet("background-color: red; border: none; font-size: 36px; font-family: Calibri")')
        self.setFont(self.CommonFont)


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
        self.CancelButton.clicked.connect(lambda: mifare_reader.Interrupt())
    
    def closeEvent(self, event):
        self.HintLabel.setText('')
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
        self.TextEdit.setReadOnly(False)
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
        self.student_id = self.StudentIdLineEdit.text()
        student_id_byte_list = Converter.AddChecksum(Converter.StudentId(int(self.student_id)))
        self.student_name = self.StudentNameLineEdit.text()
        student_name_byte_list = Converter.StudentName(self.student_name)
        self.access_key = student_id_byte_list
        self.student_infomation_byte = student_id_byte_list + student_name_byte_list
        self.Execute()
        
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card_gui.show())
        self.Thread.finished.connect(self.DatabaseUpdate)
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
        return uid
    
    def DatabaseUpdate(self):
        tap_card_gui.close()
        uid = self.Thread.Result
        # Saveuser.main(uid, self.StudentName, self.StudentId)


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
        self.CancelButton.clicked.connect(self.close)
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


class CardInfoProgram(QtCore.QObject):
    '''This is the Model session of Card Info'''
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card_gui.show())
        self.Thread.finished.connect(self.DisplayCardInfo)
        self.Thread.start()
    
    def MainProgram(self, uid, access_key):
        history_data = []
        mifare_reader.MFRC522_Auth(uid, 1, mifare_reader.DEFAULT_KEY)
        block1_data = mifare_reader.MFRC522_Read(1)
        block2_data = mifare_reader.MFRC522_Read(2)
        mifare_reader.MFRC522_Auth(uid, 4, access_key)
        block4_data = mifare_reader.MFRC522_Read(4)
        for x in range(3, 13):
            mifare_reader.MFRC522_Auth(uid, 4 * x, access_key)
            sector_data = [mifare_reader.MFRC522_Read(4 * x + y) for y in range(3)]
            if sector_data == [[0] * 16] * 3:
                break
            else:
                history_data.append(sector_data)
        return block1_data, block2_data, block4_data, history_data
    
    def DisplayCardInfo(self):
        tap_card_gui.close()
        if self.Thread.Result:
            block1_data, block2_data, block4_data, history_data = self.Thread.Result
            student_data = block1_data + block2_data
            student_id = Converter.StudentId(student_data[:6])
            student_name = Converter.StudentName(student_data[6:])
            balance = Converter.Balance(block4_data)
            if len(history_data) != 0:
                history_data_list = [Converter.HistoryRecord(data) for data in history_data]
                history_data_list.sort(key=lambda x: x[2])
            else:
                history_data_list = []
            display_info = self.Pformat(student_id, student_name, balance, history_data_list)
            display_gui.show()
            display_gui.TextEdit.setText(display_info)
            display_gui.TextEdit.setReadOnly(True)
    
    def Pformat(self, student_id, student_name, balance, history_data_list):
        display_info = '\n'.join([f'Student Name:{student_name}', f'Student ID:{student_id}', f'Balance:{balance}'])
        if history_data_list == []:
            display_info = '\n'.join([display_info, 'No history data found'])
        else:
            history_data_display_list = [f"{'Locker Location':<30} {'Index':<5} {'Borrow Time':<19} {'Return Time':<19}"]
            history_data_display_list += [f"{data[0]:<30} {data[1]:<5d} {strftime('%Y-%m-%d %H:%M:%S', localtime(data[2]))} {strftime('%Y-%m-%d %H:%M:%S', localtime(data[3])) if data[3] != 0 else 'Not return yet'}" for data in history_data_list]
            history_data_display_list = '\n'.join(history_data_display_list)
            display_info = '\n'.join([display_info, history_data_display_list])
        return display_info


class LockerBorrowGui(QtWidgets.QWidget):
    '''This is the View session of Locker Borrow'''
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
        self.BorrowMessageLabel_1 = QtWidgets.QLabel()
        self.BorrowMessageLabel_1.setAlignment(QtCore.Qt.AlignCenter)
        self.BorrowMessageLabel_2 = QtWidgets.QLabel('Please put all the things you want into locker \nand close the door properly \nbefore you click the confirm button.')
        self.BorrowMessageLabel_2.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.BorrowMessageLabel_1, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.BorrowMessageLabel_2, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)


class LockerBorrowController(LockerBorrowGui):
    '''This is the Controller session of Locker Borrow'''
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.BorrowLockerPreparation)
    
    def GetLockerIndex(self, index):
        self.LockerIndex = index
        self.BorrowMessageLabel_1.setText(f'You have selected locker {self.LockerIndex}')
        self.show()


class LockerBorrowProgram(LockerBorrowController):
    '''This is the Model session of Locker Borrow'''
    def __init__(self):
        super().__init__()
    
    def LockerSelection(self):
        locker_list = list(system_gui.SystemStatus.items())
        locker_list.sort(key=lambda x:x[1]['usage_count'])
        self.GetLockerIndex(locker_list[0][0])

    def BorrowLockerPreparation(self):
        system_name_byte = Converter.SystemName(system_gui.SystemSetting['system_name'])
        locker_index_byte = Converter.LockerIndex(int(self.LockerIndex))
        self.SystemData = system_name_byte + locker_index_byte
        self.StartTime = int(time())
        self.TimeData = Converter.Time(self.StartTime) + [0] * 8
        self.Execute()
        
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(tap_card_gui.show)
        self.Thread.finished.connect(self.StatusUpate)
        self.Thread.start()

    def MainProgram(self, uid, access_key):
        mifare_reader.MFRC522_Auth(uid, 1, mifare_reader.DEFAULT_KEY)
        block1_data = mifare_reader.MFRC522_Read(1)
        block2_data = mifare_reader.MFRC522_Read(2)
        mifare_reader.MFRC522_Auth(uid, 8, access_key)
        block8_data = mifare_reader.MFRC522_Read(8)
        block9_data = mifare_reader.MFRC522_Read(9)
        write_position = block8_data.index(1)
        mifare_reader.MFRC522_Auth(uid, 12 + write_position * 4, access_key)
        mifare_reader.MFRC522_Write(12 + write_position * 4, self.SystemData[:16])
        mifare_reader.MFRC522_Write(12 + write_position * 4 + 1, self.SystemData[16:])
        mifare_reader.MFRC522_Write(12 + write_position * 4 + 2, self.TimeData)
        # write flag reflesh
        while 1:
            block8_data = [block8_data[9]] + block8_data[:9] + block8_data[10:]
            if block9_data[block8_data.index(1)] != 1:
                break
        block9_data[write_position] = 1
        mifare_reader.MFRC522_Auth(uid, 8, access_key)
        mifare_reader.MFRC522_Write(8, block8_data)
        mifare_reader.MFRC522_Write(9, block9_data)
        return block1_data, block2_data
    
    def StatusUpate(self):
        tap_card_gui.close()
        student_info_data = self.Thread.Result[0] + self.Thread.Result[1]
        student_id = Converter.StudentId(student_info_data[:6])
        student_name = Converter.StudentName(student_info_data[6:])
        system_gui.SystemStatus[self.LockerIndex]['availability'] = 0
        system_gui.SystemStatus[self.LockerIndex]['student_name'] = student_name
        system_gui.SystemStatus[self.LockerIndex]['student_id'] = student_id
        system_gui.SystemStatus[self.LockerIndex]['start_time'] = self.StartTime
        system_gui.SystemStatus[self.LockerIndex]['usage_count'] += 1
        with open(SYSTEM_STATUS_FILE_PATH, 'wb') as system_status_file:
            dump(system_gui.SystemStatus, system_status_file)
        time_string = strftime('%Y-%m-%d %H:%M:%S', localtime(self.StartTime))
        with open(SYSTEM_LOG_FILE_PATH, 'a') as system_log_file:
            system_log_file.write(f'{time_string},Borrow - Locker {self.LockerIndex} was borrowed by {student_id} {student_name}\n')
        print(system_gui.SystemStatus)
        system_gui.LockerStatusRefresh()


class LockerReturnGui(QtWidgets.QWidget):
    '''This is the View session of Locker Return'''
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
        self.ReturnMessageLabel_1 = QtWidgets.QLabel()
        self.ReturnMessageLabel_1.setAlignment(QtCore.Qt.AlignCenter)
        self.ReturnMessageLabel_2 = QtWidgets.QLabel('Are you comfirm?')
        self.ReturnMessageLabel_2.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.ReturnMessageLabel_1, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.ReturnMessageLabel_2, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)


class LockerReturnController(LockerReturnGui):
    '''This is the Controller session of Locker Return'''
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.ReturnLockerPreparation)
    
    def GetLockerIndex(self, index):
        self.LockerIndex = index
        self.ReturnMessageLabel_1.setText(f'You have selected locker {self.LockerIndex}')
        self.show()


class LockerReturnProgram(LockerReturnController):
    '''This is the Model session of Locker Return'''
    def __init__(self):
        super().__init__()

    def ReturnLockerPreparation(self):
        self.StudentIdForSelectedLocker = system_gui.SystemStatus[self.LockerIndex]['student_id']
        self.StartTimeData = Converter.Time(system_gui.SystemStatus[self.LockerIndex]['start_time'])
        self.EndTime = int(time())
        self.EndTimeData = Converter.Time(self.EndTime)
        self.Execute()

    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(tap_card_gui.show)
        self.Thread.finished.connect(self.StatusUpate)
        self.Thread.start()

    def MainProgram(self, uid, access_key):
        if Converter.StudentId(access_key) != self.StudentIdForSelectedLocker:
            raise mifare_reader.UnmatchError
        mifare_reader.MFRC522_Auth(uid, 9, access_key)
        block9_data = mifare_reader.MFRC522_Read(9)
        for x in range(11):
            if x == 10:
                raise mifare_reader.UnmatchError
            if block9_data[x] == 1:
                mifare_reader.MFRC522_Auth(uid, 4 * x + 14, access_key)
                if mifare_reader.MFRC522_Read(4 * x + 14)[:8] == self.StartTimeData:
                    break
        mifare_reader.MFRC522_Write(4 * x + 14, self.StartTimeData + self.EndTimeData)
        block9_data[x] = 0
        mifare_reader.MFRC522_Auth(uid, 9, access_key)
        mifare_reader.MFRC522_Write(9, block9_data)

    def StatusUpate(self):
        tap_card_gui.close()
        student_name = system_gui.SystemStatus[self.LockerIndex]['student_name']
        student_id = system_gui.SystemStatus[self.LockerIndex]['student_id']
        system_gui.SystemStatus[self.LockerIndex]['availability'] = 1
        system_gui.SystemStatus[self.LockerIndex]['student_name'] = None
        system_gui.SystemStatus[self.LockerIndex]['student_id'] = None
        system_gui.SystemStatus[self.LockerIndex]['start_time'] = None
        with open(SYSTEM_STATUS_FILE_PATH, 'wb') as system_status_file:
            dump(system_gui.SystemStatus, system_status_file)
        time_string = strftime('%Y-%m-%d %H:%M:%S', localtime(self.EndTime))
        with open(SYSTEM_LOG_FILE_PATH, 'a') as system_log_file:
            system_log_file.write(f'{time_string},Return - Locker {self.LockerIndex} was return by {student_id} {student_name}\n')
        print(system_gui.SystemStatus)
        system_gui.LockerStatusRefresh()


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
        card_info = CardInfoProgram()
        locker_borrow_gui = LockerBorrowProgram()
        locker_return_gui = LockerReturnProgram()
        system_gui.show()
        exit(app.exec_())
    else:
        print('Some system file cannot be found.')
        print('Please run the system configuration first.')
        for i in range(9, 0, -1):
            print(f'\rThe program will exit after {i}s', end='')
            sleep(1)
        print()
        exit(0)
