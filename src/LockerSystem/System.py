import Buzzerlib
import MFRC522lib
from functools import partial, wraps
from json import dumps, loads
import logging
from os import getpid, kill
from os.path import dirname, exists, join
from pprint import pformat
from PyQt5 import QtCore, QtGui, QtWidgets
import RPi.GPIO as GPIO
from subprocess import Popen
from sys import argv, exit
import Database
from time import localtime, sleep, strftime, time


# Constant
SYSTEM_CONFIGURATION_FILE_PATH = join(dirname(__file__), 'Config.json')
SYSTEM_STATUS_FILE_PATH = join(dirname(__file__), 'Status.json')
SYSTEM_LOG_FILE_PATH = join(dirname(__file__), 'Log.log')
EXTERNAL_CONTROLLER_PATH = join(dirname(__file__), 'ExternalController.py')
HELP_TEXT_EN = '''Welcome to use this locker system.
Here is the user guide:
Each number button corresponding to the locker with the same index,
different colour show different locker status, which:
Green  - Ready to be borrowed
Red    - Has been borrowed
Yellow - Under maintenance

If you select the button with these colour, the action of system will be:
Green  - Borrow this locker
Red    - Return this locker
Yellow - Pop an error message

If you select the those function botton at the same row of this help button, the action of system will be:
Borrow  - The system will borrow the locker for you automatically
Return  - The system will return the longest locker you have borrowed automatically
Inquire - You can tap your card and the system will display your information and the recent history record

You can select the UI language you like in the pull down menu
The information bar at the bottom shows the name, index, welcome message of this system and the current time

This system was implemented by TAM Kai Fung, NG Wing Huen and LO Lok Yin'''
HELP_TEXT_TC = '''歡迎使用本儲物櫃系統
以下是用户指引：
每個數字按鈕對應相同索引的儲物櫃
不同的顏色顯示不同的儲物櫃狀態，其中：
綠色 - 可以借出
紅色 - 已被借用
黃色 - 維護中

如果你選擇了這些按鈕的儲物櫃，系統將會
綠色 - 借用這個櫃子
紅色 - 退回這個櫃子
黃色 - 彈出一個錯誤信息

如果你選擇了與此幫助按鈕的同一行的功能鍵，系統將會
借用 - 系統會自動幫你借用儲物櫃
歸還 - 系統會自動歸還你所借的最長時間的儲物櫃
查詢 - 你可以拍你的卡，系統會顯示你的信息和最近的歷史記錄

你可以在下拉菜單中選擇你喜歡的介面語言
底部的信息欄顯示了本系統的名稱、索引、歡迎詞和當前時間

此系統由 TAM Kai Fung, NG Wing Huen 和 LO Lok Yin 實現'''


class MFRC522libExtension(MFRC522lib.MFRC522lib):
    '''Contain all RFID related program and value'''
    DEFAULT_KEY = [0xFF] * 6
    
    class UnmatchError(BaseException): pass

    def __init__(self):
        super().__init__()
        self.Language = 'English'
        # Translation
        self.HoldCardPrompt = {'English': 'Please hold your card until this window is close', 'Chinese': '請保持拍卡直至此視窗關閉'}
        self.TapCardAgainPrompt = {'English': 'Please tap your card again', 'Chinese': '請再次拍卡'}
        self.CardHolderNotBorrowerPrompt = {'English': 'The card holder does not is a borrower of this locker', 'Chinese': '此儲物櫃並不屬於持卡人'}

    def ChecksumAuth(self, uid):
        data = self.GetKey(uid)
        if Converter.GetChecksum(data[:4]) != data[4] or Converter.GetChecksum(data[:5]) != data[5]:
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
                        tap_card.HintLabel.setText(self.HoldCardPrompt[self.Language])
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
                        tap_card.HintLabel.setText(self.TapCardAgainPrompt[self.Language])
                        self.MFRC522_StopCrypto1()
                    except (self.UnmatchError):
                        tap_card.HintLabel.setText(self.CardHolderNotBorrowerPrompt[self.Language])
                        self.MFRC522_StopCrypto1()
                sleep(0.1)
            return result
        return StandardFrame
    
    def Interrupt(self):
        self.InterruptSignal = True
    
    def SetLanguage(self, language):
        self.Language = language


class CurrentTime(QtCore.QThread):
    time_trigger = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            current_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
            self.time_trigger.emit(current_time)
            sleep(1)


class RollSystemGreeting(QtCore.QThread):
    trigger = QtCore.pyqtSignal(str)
    def __init__(self, system_greeting):
        super().__init__()
        self.string_to_roll_string(system_greeting)

    def string_to_roll_string(self, system_greeting):
        new_system_greeting = f'{" " * ((60 - len(system_greeting)) // 2)}{system_greeting}{" " * ((60 - len(system_greeting)) // 2)}'
        self.system_greeting_list = [x for x in new_system_greeting]
    
    def run(self):
        while True:
            self.system_greeting_list = self.system_greeting_list[1:] + self.system_greeting_list[:1]
            system_greeting_string = ''.join(self.system_greeting_list)
            self.trigger.emit(system_greeting_string)
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
    def StudentId(student_id_data):
        '''Return a list if an int is input, return an int if a list with length 6 is input.'''
        if type(student_id_data) == int:
            student_id_byte_list = [(int(student_id_data) % (256 ** -x)) // (256 ** (-x - 1)) for x in range(-4, 0)]
            return student_id_byte_list
        elif type(student_id_data) == list and len(student_id_data) == 6:
            student_id = sum([student_id_data[:4][i] * (256 ** (-i - 1)) for i in range(-4, 0)])
            return student_id
        else:
            raise TypeError('Input value should be an int or list with length 6.')

    @staticmethod
    def AddChecksum(student_id_byte_list: list) -> list:
        '''Add the checksum after the student id byte list.'''
        if type(student_id_byte_list) == list and len(student_id_byte_list) == 4:
            first_checksum = Converter.GetChecksum(student_id_byte_list)
            student_id_byte_list += [first_checksum]
            second_checksum = Converter.GetChecksum(student_id_byte_list)
            student_id_byte_list += [second_checksum]
            return student_id_byte_list
        else:
            raise TypeError('Input value should be a list with length 4.')
    
    @staticmethod
    def StudentName(student_name_data):
        '''Return a list if a str is input, return a str if a list is input.'''
        if type(student_name_data) == str:
            student_name_byte_list = [ord(char) for char in student_name_data]
            if len(student_name_byte_list) <= 26:
                student_name_byte_list += [0] * (26 - len(student_name_byte_list))
            else:
                student_name_byte_list = student_name_byte_list[:26]
            return student_name_byte_list
        elif type(student_name_data) == list:
            return ''.join([chr(byte) for byte in student_name_data if byte])
        else:
            raise TypeError('Input value should be a str or a list')
    
    @staticmethod
    def Balance(balance_data: list) -> int:
        '''Return an int if a list with length 16 is input.'''
        if type(balance_data) == list and len(balance_data) == 16:
            balance = sum([balance_data[1:][i] * (256 ** (-i - 1)) for i in range(-15, 0)])
            balance = balance if balance_data[0] == 0 else -balance
            return balance
        else:
            raise TypeError('Input value should be a list with length 16')
    
    @staticmethod
    def HistoryRecord(history_data: list) -> list:
        if type(history_data) == list and len(history_data) == 3:
            locker_data = history_data[0] + history_data[1]
            locker_name = Converter.SystemName(locker_data[:30])
            locker_no = Converter.LockerIndex(locker_data[30:])
            start_time = Converter.Time(history_data[2][:8])
            end_time = Converter.Time(history_data[2][8:])
            history_record_list = [locker_name, locker_no, start_time, end_time]
            return history_record_list
        else:
            raise TypeError('Input value should be a list with length 3')
    
    @staticmethod
    def SystemName(system_name_data):
        if type(system_name_data) == str:
            system_name_byte_list = [ord(char) for char in system_name_data]
            if len(system_name_byte_list) <= 30:
                system_name_byte_list += [0] * (30 - len(system_name_byte_list))
            else:
                system_name_byte_list = system_name_byte_list[:30]
            return system_name_byte_list
        elif type(system_name_data) == list:
            system_name = ''.join([chr(x) for x in system_name_data[:30] if x])
            return system_name
        else:
            raise TypeError('Input value should be a str or a list')
    
    @staticmethod
    def LockerIndex(locker_index_data):
        if type(locker_index_data) == int and locker_index_data <= 256 ** 2 - 1:
            locker_index_byte_list = [locker_index_data // 256, locker_index_data % 256]
            return locker_index_byte_list
        elif type(locker_index_data) == list:
            locker_index = sum([locker_index_data[i] * (256 ** (-i - 1)) for i in range(-2, 0)])
            return locker_index
        else:
            raise TypeError('Input value should be an integer less than 256 ** 2 - 1 or a list')
    
    @staticmethod
    def Time(time_data):
        if type(time_data) == int:
            time_data_byte_list = [(time_data % (256 ** -i)) // (256 ** (-i - 1)) for i in range(-8, 0)]
            return time_data_byte_list
        elif type(time_data) == list:
            time_data = sum([time_data[i] * (256 ** (-i - 1)) for i in range(-8, 0)])
            return time_data
        else:
            raise TypeError('Input value should be an integer or a list')
    
    @staticmethod
    def TimeString(time_data: int) -> str:
        if type(time_data) == int:
            time_string = strftime('%Y-%m-%d %H:%M:%S', localtime(time_data))
            return time_string
        else:
            raise TypeError('Input value should be an integer')

    @staticmethod
    def GetChecksum(byte_list: list) -> int:
        checksum = sum([byte_list[i] * -i for i in range(-len(byte_list), 0)]) % 251
        return checksum


class KeyPadDriver:
    def __init__(self):
        self.LineEditObject = None
        self.ReadyInput = False
        self.PreviousCharacter = None
        self.L1 = 29
        self.L2 = 31
        self.L3 = 33
        self.L4 = 35
        self.C1 = 32
        self.C2 = 36
        self.C3 = 38
        self.C4 = 40
        GPIO.setup(self.L1, GPIO.OUT)
        GPIO.setup(self.L2, GPIO.OUT)
        GPIO.setup(self.L3, GPIO.OUT)
        GPIO.setup(self.L4, GPIO.OUT)
        GPIO.setup(self.C1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.C2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.C3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.C4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
    def KeyPadScan(self):
        while self.ReadyInput:
            self.ChooseCharacter(self.L1, ["1","2","3","A"])
            self.ChooseCharacter(self.L2, ["4","5","6","B"])
            self.ChooseCharacter(self.L3, ["7","8","9","C"])
            self.ChooseCharacter(self.L4, ["*","0","#","D"])
            sleep(0.1)
        
    def ChooseCharacter(self, line, characters):
        GPIO.output(line, GPIO.HIGH)
        if(GPIO.input(self.C1) == 1):
            self.InputCharacter(characters[0])
        elif(GPIO.input(self.C2) == 1):
            self.InputCharacter(characters[1])
        elif(GPIO.input(self.C3) == 1):
            self.InputCharacter(characters[2])
        elif(GPIO.input(self.C4) == 1):
            self.InputCharacter(characters[3])
        GPIO.output(line, GPIO.LOW)
    
    def InputCharacter(self, character):
        if self.PreviousCharacter != character:
            current_text = self.LineEditObject.text()
            self.PreviousCharacter = character
            if not character in ['A', 'B', 'C', 'D', '*', '#']:
                new_text = current_text + character
            else:
                new_text = current_text[:-1]
            self.LineEditObject.setText(new_text)
        else:
            self.PreviousCharacter = None

    def Connect(self, line_edit):
        self.LineEditObject = line_edit
        self.ReadyInput = True
    
    def Disconnect(self):
        self.LineEditObject = None
        self.ReadyInput = False


# System window
class SystemView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 1, 'Calibri', 36, 'LockerSystem')
        self.ScreenWidth = screen_width
        self.ScreenHeight = screen_height
        self.MainLayout = QtWidgets.QGridLayout()
        self.UserInterfaceSetup()
        self.AdminInterfaceSetup()
        self.CommonInterfaceSetup()
        self.setLayout(self.MainLayout)
        # Translation
        self.BorrowButtonText = {'English': 'Borrow', 'Chinese': '借用'}
        self.ReturnButtonText = {'English': 'Return', 'Chinese': '歸還'}
        self.InquireButtonText = {'English': 'Inquire', 'Chinese': '查詢'}
        self.HelpButtonText = {'English': 'Help', 'Chinese': '幫助'}
        self.SystemGreeting = {'English': self.SystemConfiguration['system_greeting_en'], 'Chinese': self.SystemConfiguration['system_greeting_tc']}

    def __interface__(self):
        '''Return a list which contain all interface'''
        return [self.UserInterface, self.AdminInterface]

    def UserInterfaceSetup(self):
        # Interface setting
        self.UserInterface = QtWidgets.QFrame(self)
        self.UserInterfaceLayout = QtWidgets.QGridLayout()
        # First part
        self.LockerButtonFrame = QtWidgets.QFrame()
        self.LockerButtonLayout = QtWidgets.QGridLayout()
        for row in range(self.SystemConfiguration['locker_row']):
            for column in range(self.SystemConfiguration['locker_column']):
                index = row * self.SystemConfiguration['locker_column'] + column
                exec(f'self.LockerButton{index} = QtWidgets.QPushButton(\'{index}\')')
                exec(f'self.LockerButton{index}.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)')
                exec(f'self.LockerButtonLayout.addWidget(self.LockerButton{index}, {row}, {column})')
        self.LockerButtonFrame.setLayout(self.LockerButtonLayout)
        self.UserInterfaceLayout.addWidget(self.LockerButtonFrame, 0, 0, 7, 1)
        # Second part
        self.FunctionButtonFrame = QtWidgets.QFrame()
        self.FunctionButtonLayout = QtWidgets.QGridLayout()
        self.BorrowButton = QtWidgets.QPushButton('Borrow')
        self.BorrowButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.BorrowButton, 0, 0, 2, 2)
        self.ReturnButton = QtWidgets.QPushButton('Return')
        self.ReturnButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.ReturnButton, 0, 2, 2, 2)
        self.InquireButton = QtWidgets.QPushButton('Inquire')
        self.InquireButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.InquireButton, 0, 4, 2, 2)
        self.TranslationBox = QtWidgets.QComboBox()
        self.TranslationBox.addItems(['English', '中文'])
        self.TranslationBox.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.TranslationBox, 0, 12, 2, 2)
        self.HelpButton = QtWidgets.QPushButton('Help')
        self.HelpButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.FunctionButtonLayout.addWidget(self.HelpButton, 0, 14, 2, 2)
        for i in range(16):
            self.FunctionButtonLayout.setColumnStretch(i, 1)
        self.FunctionButtonFrame.setLayout(self.FunctionButtonLayout)
        self.UserInterfaceLayout.addWidget(self.FunctionButtonFrame, 7, 0)
        # Add widget to main layout
        self.UserInterface.setLayout(self.UserInterfaceLayout)
        self.MainLayout.addWidget(self.UserInterface, 0, 0, 8, 1)
    
    def AdminInterfaceSetup(self):
        self.AdminInterface = QtWidgets.QFrame(self)
        self.AdminInterfaceLayout = QtWidgets.QGridLayout()
        # First part
        self.AdminFunctionFrame = QtWidgets.QFrame()
        self.AdminFunctionLayout = QtWidgets.QGridLayout()
        self.CardManagementButton = QtWidgets.QPushButton('CardManagement')
        self.CardManagementButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.CardManagementButton, 0, 0)
        self.DatabaseManagementButton = QtWidgets.QPushButton('DatabaseManagement')
        self.DatabaseManagementButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.DatabaseManagementButton, 0, 1)
        self.ExitButton = QtWidgets.QPushButton('Exit')
        self.ExitButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.AdminFunctionLayout.addWidget(self.ExitButton, 1, 1)
        self.AdminFunctionFrame.setLayout(self.AdminFunctionLayout)
        self.AdminInterfaceLayout.addWidget(self.AdminFunctionFrame, 0, 0, 7, 1)
        # Second part
        self.ReturnFrame = QtWidgets.QFrame()
        self.ReturnLayout = QtWidgets.QGridLayout()
        self.UserGuiButton = QtWidgets.QPushButton('User')
        self.UserGuiButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.ReturnLayout.addWidget(self.UserGuiButton, 0, 14, 1, 2)
        self.ReturnFrame.setLayout(self.ReturnLayout)
        self.AdminInterfaceLayout.addWidget(self.ReturnFrame, 7, 0)
        # Add widget to main layout
        self.AdminInterface.setLayout(self.AdminInterfaceLayout)
        self.MainLayout.addWidget(self.AdminInterface, 0, 0, 8, 1)
        self.AdminInterface.hide()
    
    def CommonInterfaceSetup(self):
        self.CommonInterfaceLayout = QtWidgets.QGridLayout()
        self.SystemNameLabel = QtWidgets.QLabel(f'{self.SystemConfiguration["system_name"]}')
        self.SystemNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.CommonInterfaceLayout.addWidget(self.SystemNameLabel, 0, 0)
        self.SystemCodeLabel = QtWidgets.QLabel(f'{self.SystemConfiguration["system_code"]}')
        self.SystemCodeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.CommonInterfaceLayout.addWidget(self.SystemCodeLabel, 0, 1)
        self.SystemGreetingLabel = QtWidgets.QLabel()
        self.SystemGreetingLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.CommonInterfaceLayout.addWidget(self.SystemGreetingLabel, 0, 2, 1, 10)
        self.TimeLabel = QtWidgets.QLabel()
        self.TimeLabel.setAlignment(QtCore.Qt.AlignVCenter)
        self.CommonInterfaceLayout.addWidget(self.TimeLabel, 0, 12, 1, 4)
        self.MainLayout.addLayout(self.CommonInterfaceLayout, 8, 0)
    
    def SetLanguage(self, language):
        self.Language = language
        self.BorrowButton.setText(self.BorrowButtonText[self.Language])
        self.ReturnButton.setText(self.ReturnButtonText[self.Language])
        self.InquireButton.setText(self.InquireButtonText[self.Language])
        self.HelpButton.setText(self.HelpButtonText[self.Language])
        self.RollSystemGreeting.string_to_roll_string(self.SystemGreeting[self.Language])


class SystemController(SystemView):
    def __init__(self):
        super().__init__()
        # Authentication key
        self.AuthenticationKey = [1, 2, 4, 4, 4]
        self.InputAuthenticationKey = []
        self.LockerButtonConnection()
        self.UserFunctionConnection()
        self.AdminFunctionConnection()
        self.LockerStatusRefresh()
    
    def UserFunctionConnection(self):
        self.BorrowButton.clicked.connect(lambda: locker_borrow.LockerSelection())
        self.InquireButton.clicked.connect(lambda: inquire.Execute())
        self.TranslationBox.currentIndexChanged.connect(self.SetUILanguage)
        self.HelpButton.clicked.connect(lambda: help.Display())
        self.RollSystemGreeting = RollSystemGreeting(self.SystemGreeting[self.Language])
        self.RollSystemGreeting.trigger.connect(self.SystemGreetingDisplay)
        self.RollSystemGreeting.start()
        self.CurrentTime = CurrentTime()
        self.CurrentTime.time_trigger.connect(self.CurrentTimeDisplay)
        self.CurrentTime.start()
    
    def SystemGreetingDisplay(self, system_greeting):
        self.SystemGreetingLabel.setText(f'{system_greeting}')

    def CurrentTimeDisplay(self, current_time):
        self.TimeLabel.setText(f'{current_time}')

    def AdminFunctionConnection(self):
        self.CardManagementButton.clicked.connect(lambda: card_management.show())
        self.DatabaseManagementButton.clicked.connect(lambda: database_management.show())
        self.ExitButton.clicked.connect(lambda: exit_program.show())
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
        locker_total = self.SystemConfiguration['locker_row'] * self.SystemConfiguration['locker_column']
        for i in range(locker_total):
            exec(f'self.LockerButton{i}.clicked.connect(partial(self.LockerController, {i}))')
    
    def LockerController(self, locker_index):
        locker_index = str(locker_index)
        if self.SystemStatus[locker_index]['availability'] == 1:
            locker_borrow.GetLockerIndex(locker_index)
        elif self.SystemStatus[locker_index]['availability'] == 0:
            locker_return.GetLockerIndex(locker_index)
    
    def SetUILanguage(self, index):
        if index == 0:
            set_ui_language('English')
        elif index == 1:
            set_ui_language('Chinese')
        
    def LockerStatusRefresh(self):
        for locker in self.SystemStatus.keys():
            if self.SystemStatus[locker]['availability'] == 1:
                exec(f'self.LockerButton{locker}.setStyleSheet("background-color: green; border: none; font-size: 36px; font-family: Calibri")')
            else:
                exec(f'self.LockerButton{locker}.setStyleSheet("background-color: red; border: none; font-size: 36px; font-family: Calibri")')


class SystemModel(SystemController):
    def __init__(self):
        # Get the configuration from the configuration file
        self.SystemConfiguration = self.__GetSystemConfiguration()
        self.SystemStatus = self.__GetSystemStatus()
        self.__SetSystemLog()
        Database.Initialization()
        super().__init__()
    
    def __GetSystemConfiguration(self):
        with open(SYSTEM_CONFIGURATION_FILE_PATH, 'r', encoding='utf-8') as system_configuration_file:
            system_configuration_data = system_configuration_file.read()
            system_configuration_data = loads(system_configuration_data)
        return system_configuration_data
    
    def __GetSystemStatus(self):
        if exists(SYSTEM_STATUS_FILE_PATH):
            with open(SYSTEM_STATUS_FILE_PATH, 'r', encoding='utf-8') as system_status_file:
                system_status_data = system_status_file.read()
        else:
            locker_column = self.SystemConfiguration['locker_column']
            locker_row = self.SystemConfiguration['locker_row']
            total_locker_number = locker_column * locker_row
            system_status_data = {f'{index}': {'availability': 1, 'student_name': None, 'student_id': None, 'start_time': None, 'usage_count': 0} for index in range(total_locker_number)}
            system_status_data = dumps(system_status_data, indent=4)
            with open(SYSTEM_STATUS_FILE_PATH, 'w', encoding='utf-8') as system_status_file:
                system_status_file.write(system_status_data)
        system_status_data = loads(system_status_data)
        return system_status_data
    
    def __SetSystemLog(self):
        logging.basicConfig(filename=SYSTEM_LOG_FILE_PATH, filemode='a', format='%(message)s', level=logging.DEBUG)
    
    def SystemLogWrite(self, message):
        logging.info(message)


class TapCardView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'TapCard')
        # Translation
        self.TapCardPrompt = {'English': 'Please tap your card', 'Chinese': '請拍卡'}
        self.CancelButtonText = {'English': 'Cancel', 'Chinese': '取消'}
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.TapCardLabel = QtWidgets.QLabel(self.TapCardPrompt[self.Language])
        self.TapCardLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.TapCardLabel, 0, 0, 1, 3)
        self.HintLabel = QtWidgets.QLabel('')
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(self.CancelButtonText[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 1, 1, 1)
        self.setLayout(self.MainLayout)
    
    def SetLanguage(self, language):
        self.Language = language
        self.TapCardLabel.setText(self.TapCardPrompt[self.Language])
        self.CancelButton.setText(self.CancelButtonText[self.Language])


class TapCardController(TapCardView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(lambda: mifare_reader.Interrupt())
    
    def closeEvent(self, event):
        self.HintLabel.setText('')
        event.accept()


class DisplayView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 2, 'Consolas', 12, 'Display')
        # Translation
        self.CancelButtonText = {'English': 'Cancel', 'Chinese': '取消'}
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.TextEdit = QtWidgets.QTextEdit()
        self.TextEdit.setReadOnly(True)
        self.MainLayout.addWidget(self.TextEdit, 0, 0, 2, 3)
        self.CancelButton = QtWidgets.QPushButton(self.CancelButtonText[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 1)
        self.setLayout(self.MainLayout)
    
    def SetLanguage(self, language):
        self.Language = language
        self.CancelButton.setText(self.CancelButtonText[self.Language])


class DisplayController(DisplayView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
    
    def Display(self, text):
        self.TextEdit.setText(text)
        self.show()

    def closeEvent(self, event):
        self.TextEdit.clear()
        event.accept()


class WarningMessageBox(QtWidgets.QMessageBox):
    def __init__(self, message):
        super().__init__()
        # Set font property
        font = QtGui.QFont()
        font.setFamily('Calibri')
        font.setPointSize(12)
        self.setFont(font)
        # Set widget property
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # Set default language
        self.Language = 'English'
        self.setIcon(self.Warning)
        self.setText(message)
        comfirm = self.addButton('Corfirm', self.AcceptRole)
        cancel = self.addButton('Cancel', self.RejectRole)
        
    
    def AcceptAction(self, function, *arg):
        reply = self.exec()
        if reply == self.AcceptRole:
            function(*arg)
        elif reply == self.RejectRole:
            pass


# User function window
class LockerBorrowView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'LockerBorrow')
        # Translation
        self.BorrowMessageLabel_2Prompt = {'English': 'Please put all the things you want into locker \nand close the door properly \nbefore you click the confirm button.', 'Chinese': '請將您的東西全部放進儲物櫃，\n並正確關閉櫃門，\n然後再點擊確認按鈕。'}
        self.CancelButtonText = {'English': 'Cancel', 'Chinese': '取消'}
        self.ConfirmButtonText = {'English': 'Comfirm', 'Chinese': '確認'}
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.BorrowMessageLabel_1 = QtWidgets.QLabel()
        self.BorrowMessageLabel_1.setAlignment(QtCore.Qt.AlignCenter)
        self.BorrowMessageLabel_2 = QtWidgets.QLabel(self.BorrowMessageLabel_2Prompt[self.Language])
        self.BorrowMessageLabel_2.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.BorrowMessageLabel_1, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.BorrowMessageLabel_2, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(self.CancelButtonText[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton(self.ConfirmButtonText[self.Language])
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)
    
    def SetLanguage(self, language):
        self.Language = language
        self.BorrowMessageLabel_2.setText(self.BorrowMessageLabel_2Prompt[self.Language])
        self.CancelButton.setText(self.CancelButtonText[self.Language])
        self.ConfirmButton.setText(self.ConfirmButtonText[self.Language])


class LockerBorrowController(LockerBorrowView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.BorrowLockerPreparation)
    
    def GetLockerIndex(self, index):
        self.LockerIndex = index
        if self.Language == 'English':
            self.BorrowMessageLabel_1.setText(f'You have selected locker {self.LockerIndex}')
        elif self.Language == 'Chinese':
            self.BorrowMessageLabel_1.setText(f'您選擇了儲物櫃 {self.LockerIndex}')
        self.show()


class LockerBorrowModel(LockerBorrowController):
    def __init__(self):
        super().__init__()
    
    def LockerSelection(self):
        locker_list = list(system.SystemStatus.items())
        locker_list.sort(key=lambda x:x[1]['usage_count'])
        self.GetLockerIndex(locker_list[0][0])

    def BorrowLockerPreparation(self):
        system_name_byte = Converter.SystemName(system.SystemConfiguration['system_name'])
        locker_index_byte = Converter.LockerIndex(int(self.LockerIndex))
        self.SystemData = system_name_byte + locker_index_byte
        self.StartTime = int(time())
        self.TimeData = Converter.Time(self.StartTime) + [0] * 8
        self.Execute()
        
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(tap_card.show)
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
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            student_info_data = self.Thread.Result[0] + self.Thread.Result[1]
            student_id = Converter.StudentId(student_info_data[:6])
            student_name = Converter.StudentName(student_info_data[6:])
            system.SystemStatus[self.LockerIndex]['availability'] = 0
            system.SystemStatus[self.LockerIndex]['student_name'] = student_name
            system.SystemStatus[self.LockerIndex]['student_id'] = student_id
            system.SystemStatus[self.LockerIndex]['start_time'] = self.StartTime
            system.SystemStatus[self.LockerIndex]['usage_count'] += 1
            updated_status = dumps(system.SystemStatus)
            with open(SYSTEM_STATUS_FILE_PATH, 'w') as system_status_file:
                system_status_file.write(updated_status)
            time_string = Converter.TimeString(self.StartTime)
            system.SystemLogWrite(f'{time_string} Borrow - Locker {self.LockerIndex} was borrowed by {student_id} {student_name}')
            system.LockerStatusRefresh()
            Database.HistoryRecordUpdateBorrow(student_id, self.LockerIndex, time_string)


class LockerReturnView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'LockerReturn')
        # Translation
        self.ReturnMessageLabel_2Prompt = {'English': 'Are you comfirm to return?', 'Chinese': '您確定要歸還嗎?'}
        self.CancelButtonText = {'English': 'Cancel', 'Chinese': '取消'}
        self.ConfirmButtonText = {'English': 'Comfirm', 'Chinese': '確認'}
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.ReturnMessageLabel_1 = QtWidgets.QLabel()
        self.ReturnMessageLabel_1.setAlignment(QtCore.Qt.AlignCenter)
        self.ReturnMessageLabel_2 = QtWidgets.QLabel('Are you comfirm to return?')
        self.ReturnMessageLabel_2.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.ReturnMessageLabel_1, 0, 0, 1, 3)
        self.MainLayout.addWidget(self.ReturnMessageLabel_2, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)

    def SetLanguage(self, language):
        self.Language = language
        self.ReturnMessageLabel_2.setText(self.ReturnMessageLabel_2Prompt[self.Language])
        self.CancelButton.setText(self.CancelButtonText[self.Language])
        self.ConfirmButton.setText(self.ConfirmButtonText[self.Language])


class LockerReturnController(LockerReturnView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.ReturnLockerPreparation)
    
    def GetLockerIndex(self, index):
        self.LockerIndex = index
        if self.Language == 'English':
            self.ReturnMessageLabel_1.setText(f'You have selected locker {self.LockerIndex}')
        elif self.Language == 'Chinese':
            self.ReturnMessageLabel_1.setText(f'您選擇了儲物櫃 {self.LockerIndex}')
        self.show()


class LockerReturnModel(LockerReturnController):
    def __init__(self):
        super().__init__()

    def ReturnLockerPreparation(self):
        self.StudentIdForSelectedLocker = system.SystemStatus[self.LockerIndex]['student_id']
        self.StartTimeData = Converter.Time(system.SystemStatus[self.LockerIndex]['start_time'])
        self.EndTime = int(time())
        self.EndTimeData = Converter.Time(self.EndTime)
        self.Execute()

    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(tap_card.show)
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
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            student_name = system.SystemStatus[self.LockerIndex]['student_name']
            student_id = system.SystemStatus[self.LockerIndex]['student_id']
            borrow_time = system.SystemStatus[self.LockerIndex]['start_time']
            system.SystemStatus[self.LockerIndex]['availability'] = 1
            system.SystemStatus[self.LockerIndex]['student_name'] = None
            system.SystemStatus[self.LockerIndex]['student_id'] = None
            system.SystemStatus[self.LockerIndex]['start_time'] = None
            updated_status = dumps(system.SystemStatus)
            with open(SYSTEM_STATUS_FILE_PATH, 'w') as system_status_file:
                system_status_file.write(updated_status)
            borrow_time_string = Converter.TimeString(borrow_time)
            return_time_string = Converter.TimeString(self.EndTime)
            system.SystemLogWrite(f'{return_time_string} Return - Locker {self.LockerIndex} was return by {student_id} {student_name}\n')
            system.LockerStatusRefresh()
            Database.HistoryRecordUpdateReturn(student_id, self.LockerIndex, borrow_time_string, return_time_string)


class Inquire(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.Language = 'English'
        # Translation
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.finished.connect(self.DisplayInquire)
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
    
    def DisplayInquire(self):
        tap_card.close()
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
            formatted_string = self.FormatInquireResult(student_id, student_name, balance, history_data_list)
            display.Display(formatted_string)
    
    def FormatInquireResult(self, student_id, student_name, balance, history_data_list):
        student_info = '\n'.join([f'Student Name: {student_name}', f'Student ID: {student_id}', f'Balance: {balance}'])
        if history_data_list == []:
            formatted_string = '\n'.join([student_info, 'No history data found'])
        else:
            first_column_data = [data[0] for data in history_data_list]
            first_column_width = max([len(data) for data in first_column_data] + [len('Locker Location')]) + 2
            second_column_data = [str(data[1]) for data in history_data_list]
            second_column_width = max([len(data) for data in second_column_data] + [len('Index')]) + 2
            third_column_data = [strftime('%Y-%m-%d %H:%M:%S', localtime(data[2])) for data in history_data_list]
            third_column_width = max([len(data) for data in third_column_data] + [len('Borrow Time')]) + 2
            fourth_column_data = [data[3] for data in history_data_list]
            for i in range(len(fourth_column_data)):
                if fourth_column_data[i] == 0:
                    fourth_column_data[i] = 'Not return yet'
                else:
                    fourth_column_data[i] = strftime('%Y-%m-%d %H:%M:%S', localtime(fourth_column_data[i]))
            fourth_column_width = max([len(data) for data in fourth_column_data]+ [len('Return Time')]) + 2
            first_row = 'History Record:'
            second_row = f'+{"-" * first_column_width}+{"-" * second_column_width}+{"-" * third_column_width}+{"-" * fourth_column_width}+'
            third_row = f'| Locker Location{" " * (first_column_width - len(" Locker Location"))}| Index{" " * (second_column_width - len(" Index"))}| Borrow Time{" " * (third_column_width - len(" Borrow Time"))}| Return Time{" " * (fourth_column_width - len(" Return Time"))}|'
            fourth_row = last_row = str(second_row)
            history_data_row_list = [f'| {first_column_data[i]}{" " * (first_column_width - len(f" {first_column_data[i]}"))}| {second_column_data[i]}{" " * (second_column_width - len(f" {second_column_data[i]}"))}| {third_column_data[i]}{" " * (third_column_width - len(f" {third_column_data[i]}"))}| {fourth_column_data[i]}{" " * (fourth_column_width - len(f" {fourth_column_data[i]}"))}|' for i, _ in enumerate(history_data_list)]
            history_data_string = '\n'.join(history_data_row_list)
            formatted_string = '\n'.join([student_info, first_row, second_row, third_row, fourth_row, history_data_string, last_row])
        return formatted_string

    def SetLanguage(self, language):
        self.Language = language


class Help(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.Language = 'English'
        # Translation
        self.HelpText = {'English': HELP_TEXT_EN, 'Chinese': HELP_TEXT_TC}

    def Display(self):
        display.Display(self.HelpText[self.Language])

    def SetLanguage(self, language):
        self.Language = language


# Admin function window
# Card related
class CardManagementView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'CardManagaement')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.CardInitializationButton = QtWidgets.QPushButton('CardInitialization')
        self.CardInitializationButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.CardInitializationButton, 0, 0, 4, 3)
        self.CardResetButton = QtWidgets.QPushButton('CardReset')
        self.CardResetButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.CardResetButton, 4, 0, 4, 3)
        self.CardDumpButton = QtWidgets.QPushButton('CardDump')
        self.CardDumpButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.CardDumpButton, 8, 0, 4, 3)
        self.TopUpButton = QtWidgets.QPushButton('TopUp')
        self.TopUpButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.TopUpButton, 12, 0, 4, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class CardManagementController(CardManagementView):
    def __init__(self):
        super().__init__()
        self.CardInitializationButton.clicked.connect(self.RunCardInitialization)
        self.CardResetButton.clicked.connect(self.RunCardReset)
        self.CardDumpButton.clicked.connect(self.RunCardDump)
        self.TopUpButton.clicked.connect(self.RunTopUp)
        self.CancelButton.clicked.connect(self.close)
    
    def RunCardInitialization(self):
        self.close()
        card_initialization.show()

    def RunCardReset(self):
        self.close()
        card_reset.ShowWarning()
    
    def RunCardDump(self):
        self.close()
        card_dump.Execute()
    
    def RunTopUp(self):
        self.close()
        balance.show()
        balance.Execute()


class CardInitializationView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'CardInitialization')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.HintLabel = QtWidgets.QLabel('Please input:')
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 0, 0, 1, 3)
        self.StudentIdLabel = QtWidgets.QLabel('Student ID:')
        self.StudentIdLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.StudentIdLabel, 1, 0)
        self.StudentIdLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentIdLineEdit, 1, 1, 1, 2)
        self.StudentNameLabel = QtWidgets.QLabel('Student Name:')
        self.StudentNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.StudentNameLabel, 2, 0)
        self.StudentNameLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentNameLineEdit, 2, 1, 1, 2)
        self.HintLabel = QtWidgets.QLabel()
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 3, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 4, 0)
        self.MainLayout.addWidget(QtWidgets.QLabel(), 4, 1)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ComfirmButton, 4, 2)
        self.setLayout(self.MainLayout)


class CardInitializationController(CardInitializationView):
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
        self.HintLabel.setText('')
        pattern = QtCore.QRegExp('^\d{8}$')
        validator = QtGui.QRegExpValidator(pattern)
        try:
            used = Database.UserRegistrationSearch(text)
            if used == 0:
                if validator.validate(text, 0)[0] == 2:
                    self.StudentIdOkSignal.emit(True)
            else:
                self.HintLabel.setText('This Student ID has been used.')
        except Database.mysql.connector.errors.ProgrammingError:
            pass
    
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


class CardInitializationModel(CardInitializationController):
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
        self.Thread.started.connect(lambda: tap_card.show())
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
        tap_card.close()
        uid = self.Thread.Result
        initialization_time_string = Converter.TimeString(int(time()))
        Database.UserRegistrationUpdate(uid, self.student_name, self.student_id, initialization_time_string)


class CardReset(QtCore.QObject):
    def __init__(self):
        super().__init__()
    
    def ShowWarning(self):
        warning_messagebox = WarningMessageBox(f'You are going to reset your card.\nAre you sure?')
        warning_messagebox.AcceptAction(self.Execute)
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.finished.connect(self.DatabaseUpdate)
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
        return access_key
    
    def DatabaseUpdate(self):
        tap_card.close()
        if self.Thread.Result != None:
            access_key = self.Thread.Result
            student_id = Converter.StudentId(access_key)
            Database.UserRegistrationDelectRecord(student_id)


class CardDump(QtCore.QObject):
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
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
        tap_card.close()
        if self.Thread.Result:
            display.show()
            display.TextEdit.setText(f'{pformat(self.Thread.Result)}')


class BalanceView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'Balance')
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.TopupLabel = QtWidgets.QLabel('Please input the top-up value')
        self.TopupLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.TopupLabel, 0, 0, 1, 3)
        self.BalanceLineEdit = QtWidgets.QLineEdit()
        self.BalanceLineEdit.setReadOnly(True)
        self.MainLayout.addWidget(self.BalanceLineEdit, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ComfirmButton, 2, 2)
        self.setLayout(self.MainLayout)


class BalanceController(BalanceView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)


class BalanceModel(BalanceController):
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        keypad.Connect(self.BalanceLineEdit)
        self.Thread = Threading(keypad.KeyPadScan)
        self.Thread.started.connect(self.show)
        self.Thread.start()
    
    def closeEvent(self, event):
        self.BalanceLineEdit.clear()
        keypad.Disconnect()


# Database related
class DatabaseManagementView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'DatabaseManagaement')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.PrintDatabaseButton = QtWidgets.QPushButton('PrintDatabase')
        self.PrintDatabaseButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.PrintDatabaseButton, 0, 0, 5, 3)
        self.ResetDatabaseButton = QtWidgets.QPushButton('ResetDatabase')
        self.ResetDatabaseButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ResetDatabaseButton, 5, 0, 5, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class DatabaseManagementController(DatabaseManagementView):
    def __init__(self):
        super().__init__()
        self.PrintDatabaseButton.clicked.connect(self.PrintDatabase)
        self.ResetDatabaseButton.clicked.connect(self.ResetDatabase)
        self.CancelButton.clicked.connect(self.close)
    
    def PrintDatabase(self):
        self.close()
        print_database.show()
    
    def ResetDatabase(self):
        self.close()
        reset_database.show()


class PrintDatabaseView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'PrintDatabase')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.PrintUserRegistrationButton = QtWidgets.QPushButton('PrintUserRegistration')
        self.PrintUserRegistrationButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.PrintUserRegistrationButton, 0, 0, 5, 3)
        self.PrintHistoryRecordButton = QtWidgets.QPushButton('PrintHistoryRecord')
        self.PrintHistoryRecordButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.PrintHistoryRecordButton, 5, 0, 5, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class PrintDatabaseController(PrintDatabaseView):
    def __init__(self):
        super().__init__()
        self.PrintUserRegistrationButton.clicked.connect(partial(self.PrintAllRecord, 'USER_REGISTRATION'))
        self.PrintHistoryRecordButton.clicked.connect(partial(self.PrintAllRecord, 'HISTORY_RECORD'))
        self.CancelButton.clicked.connect(self.CloseWindow)
    

class PrintDatabaseModel(PrintDatabaseController):
    def __init__(self):
        super().__init__()

    def PrintAllRecord(self, table):
        result = Database.PrintAllRecord(table)
        self.close()
        display.Display(f'{pformat(result)}')
    
    def CloseWindow(self):
        self.close()
        database_management.show()


class ResetDatabaseView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'PrintDatabase')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.ResetUserRegistrationButton = QtWidgets.QPushButton('ResetUserRegistration')
        self.ResetUserRegistrationButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ResetUserRegistrationButton, 0, 0, 5, 3)
        self.ResetHistoryRecordButton = QtWidgets.QPushButton('ResetHistoryRecord')
        self.ResetHistoryRecordButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ResetHistoryRecordButton, 5, 0, 5, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class ResetDatabaseController(ResetDatabaseView):
    def __init__(self):
        super().__init__()
        self.ResetUserRegistrationButton.clicked.connect(partial(self.ResetTableWarning, 'USER_REGISTRATION'))
        self.ResetHistoryRecordButton.clicked.connect(partial(self.ResetTableWarning, 'HISTORY_RECORD'))
        self.CancelButton.clicked.connect(self.CloseWindow)


class ResetDatabaseModel(ResetDatabaseController):
    def __init__(self):
        super().__init__()

    def ResetTableWarning(self, table):
        self.close()
        warning_messagebox = WarningMessageBox(f'You are going to reset table {table}.\nAre you sure?')
        warning_messagebox.AcceptAction(self.ResetTable, table)

    def ResetTable(self, table):
        Database.ResetTable(table)
    
    def CloseWindow(self):
        self.close()
        database_management.show()
    

class ExitProgramView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        set_widget_setting(self, 4, 'Calibri', 12, 'ExitProgram')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.ExitProgramButton = QtWidgets.QPushButton('ExitProgram')
        self.ExitProgramButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ExitProgramButton, 0, 0, 5, 3)
        self.RestartProgramButton = QtWidgets.QPushButton('RestartProgram')
        self.RestartProgramButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.RestartProgramButton, 5, 0, 5, 3)
        self.PowerOffButton = QtWidgets.QPushButton('PowerOff')
        self.PowerOffButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.PowerOffButton, 10, 0, 5, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class ExitProgramController(ExitProgramView):
    def __init__(self):
        super().__init__()
        self.ExitProgramButton.clicked.connect(partial(self.ActionConfirm, 'ExitProgram'))
        self.RestartProgramButton.clicked.connect(partial(self.ActionConfirm, 'RestartProgram'))
        self.PowerOffButton.clicked.connect(partial(self.ActionConfirm, 'PowerOff'))
        self.CancelButton.clicked.connect(self.close)


class ExitProgramModel(ExitProgramController):
    def __init__(self):
        super().__init__()
        self.PID = getpid()

    def ActionConfirm(self, mode):
        self.close()
        warning_messagebox = WarningMessageBox(f'Are you sure to {mode}?')
        if mode == 'ExitProgram':
            warning_messagebox.AcceptAction(self.ExitProgram)
        elif mode == 'RestartProgram':
            warning_messagebox.AcceptAction(self.RestartProgram)
        elif mode == 'PowerOff':
            warning_messagebox.AcceptAction(self.PowerOff)

    def ExitProgram(self):
        exit(0)

    def RestartProgram(self):
        Popen(['python3', EXTERNAL_CONTROLLER_PATH, f'{self.PID}', 'Restart'])

    def PowerOff(self):
        Popen(['python3', EXTERNAL_CONTROLLER_PATH, f'{self.PID}', 'PowerOff'])


def get_screen_infomation():
    current_screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
    screen_width = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().width()
    screen_height = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().height()
    center_point = QtWidgets.QApplication.desktop().screenGeometry(current_screen).center()
    return screen_width, screen_height, center_point


def set_widget_setting(widget_object, size, font_family, font_size, window_title=''):
    '''size is the magnification against the screen size, i.e. widget size = 480x270 when screen size = 1920x1080 and size = 4'''
    # Set widget size and position
    widget_object.setFixedSize(screen_width // size, screen_height // size)
    frame_geometry = widget_object.frameGeometry()
    frame_geometry.moveCenter(center_point)
    widget_object.move(frame_geometry.topLeft())
    # Set font property
    font = QtGui.QFont()
    font.setFamily(font_family)
    font.setPointSize(font_size)
    widget_object.setFont(font)
    # Set widget property
    widget_object.setWindowFlag(QtCore.Qt.FramelessWindowHint)
    widget_object.setWindowModality(QtCore.Qt.ApplicationModal)
    widget_object.setWindowTitle(window_title)
    # Set default language
    widget_object.Language = 'English'


def set_ui_language(language):
    mifare_reader.SetLanguage(language)
    system.SetLanguage(language)
    tap_card.SetLanguage(language)
    display.SetLanguage(language)
    locker_borrow.SetLanguage(language)
    locker_return.SetLanguage(language)
    help.SetLanguage(language)


if __name__ == '__main__':
    if exists(SYSTEM_CONFIGURATION_FILE_PATH):
        GPIO.setwarnings(False)
        app = QtWidgets.QApplication(argv)
        screen_width, screen_height, center_point = get_screen_infomation()
        mifare_reader = MFRC522libExtension()
        keypad = KeyPadDriver()
        system = SystemModel()
        tap_card = TapCardController()
        display = DisplayController()
        locker_borrow = LockerBorrowModel()
        locker_return = LockerReturnModel()
        inquire = Inquire()
        help = Help()
        card_management = CardManagementController()
        card_initialization = CardInitializationModel()
        card_reset = CardReset()
        card_dump = CardDump()
        balance = BalanceModel()
        database_management = DatabaseManagementController()
        print_database = PrintDatabaseModel()
        reset_database = ResetDatabaseModel()
        exit_program = ExitProgramModel()
        system.show()
        exit(app.exec_())
    else:
        print('Some system file cannot be found.')
        print('Please run the system configuration first.')
        for i in range(9, 0, -1):
            print(f'\rThe program will exit after {i}s', end='')
            sleep(1)
        print()
        exit(0)
