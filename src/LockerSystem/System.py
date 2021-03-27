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
USER_HELP_ENGLISH = 'Welcome to use this locker system.\n\
Here is the user guide:\n\
Each number button corresponding to the locker with the same index,\n\
different colour show different locker status, which:\n\
    Green  - Ready to be borrowed\n\
    Red    - Has been borrowed\n\
    Yellow - Under maintenance\n\
\n\
If you select the button with these colour, the action of system will be:\n\
    Green  - Borrow this locker\n\
    Red    - Return this locker\n\
    Yellow - Pop an error message\n\
\n\
If you select the those function botton at the same row of this help button, the action of system will be:\n\
    Borrow  - The system will borrow the locker for you automatically\n\
    Return  - The system will return the longest locker you have borrowed automatically\n\
    Inquire - You can tap your card and the system will display your information and the recent history record\n\
\n\
You can select the UI language you like in the pull down menu\n\
The information bar at the bottom shows the name, index, welcome message of this system and the current time\n\
\n\
This system was implemented by TAM Kai Fung, NG Wing Huen and LO Lok Yin.'
USER_HELP_CHINESE = '歡迎使用本儲物櫃系統\n\
以下是用户指引：\n\
每個數字按鈕對應相同索引的儲物櫃\n\
不同的顏色顯示不同的儲物櫃狀態，其中：\n\
    綠色 - 可以借出\n\
    紅色 - 已被借用\n\
    黃色 - 維護中\n\
\n\
如果你選擇了這些按鈕的儲物櫃，系統將會\n\
    綠色 - 借用這個櫃子\n\
    紅色 - 退回這個櫃子\n\
    黃色 - 彈出一個錯誤信息\n\
\n\
如果你選擇了與此幫助按鈕的同一行的功能鍵，系統將會\n\
    借用 - 系統會自動幫你借用儲物櫃\n\
    歸還 - 系統會自動歸還你所借的最長時間的儲物櫃\n\
    查詢 - 你可以拍你的卡，系統會顯示你的信息和最近的歷史記錄\n\
\n\
你可以在下拉菜單中選擇你喜歡的介面語言\n\
底部的信息欄顯示了本系統的名稱、索引、歡迎詞和當前時間\n\
\n\
此系統由 TAM Kai Fung, NG Wing Huen 和 LO Lok Yin 實現'


# Get system configuration
with open(SYSTEM_CONFIGURATION_FILE_PATH, 'r', encoding='utf-8') as system_configuration_file:
    system_configuration_data = system_configuration_file.read()
    system_configuration_data = loads(system_configuration_data)
system_configuration = system_configuration_data


class Translation:
    HoldCard = {'English': 'Please hold your card until this window is close', 'Chinese': '請保持拍卡直至此視窗關閉'}
    TapCardAgain = {'English': 'Please tap your card again', 'Chinese': '請再次拍卡'}
    NotBorrower = {'English': 'The card holder does not is a borrower of this locker', 'Chinese': '此儲物櫃並不屬於持卡人'}
    NoBorrow = {'English': 'The card holder does not borrow any locker', 'Chinese': '持卡人沒有租借任何儲物櫃'}
    InsufficientBalance = {'English': 'Insufficient balance', 'Chinese': '餘額不足'}
    UiLanguage = {'English': '中文', 'Chinese': 'English'}
    Borrow = {'English': 'Borrow', 'Chinese': '借用'}
    Return = {'English': 'Return', 'Chinese': '歸還'}
    Inquire = {'English': 'Inquire', 'Chinese': '查詢'}
    Help = {'English': 'Help', 'Chinese': '幫助'}
    SystemGreeting = {'English': system_configuration['system_greeting_en'], 'Chinese': system_configuration['system_greeting_tc']}
    TapCard = {'English': 'Please tap your card', 'Chinese': '請拍卡'}
    Cancel = {'English': 'Cancel', 'Chinese': '取消'}
    Confirm = {'English': 'Comfirm', 'Chinese': '確認'}
    SelectMessage = {'English': 'You have selected locker', 'Chinese': '您選擇了儲物櫃'}
    BorrowHint = {'English': 'Please put all the things you want into locker \nand close the door properly \nbefore you click the confirm button.', 'Chinese': '請將您的東西全部放進儲物櫃，\n並正確關閉櫃門，\n然後再點擊確認按鈕。'}
    ReturnHint = {'English': 'Are you comfirm to return?', 'Chinese': '您確定要歸還嗎?'}
    MaintenanceHint = {'English': 'This locker is in maintenance.\nPlease choose another locker.', 'Chinese': '此儲物櫃正在維護中\n請選擇另一個儲物櫃'}
    UserHelp = {'English': USER_HELP_ENGLISH, 'Chinese': USER_HELP_CHINESE}


class MFRC522libExtension(MFRC522lib.MFRC522lib):
    '''Contain all RFID related program and value'''
    DEFAULT_KEY = [0xFF] * 6
    
    class UnmatchError(BaseException): pass

    class NotFindError(BaseException): pass

    class BalanceUnderflowError(BaseException): pass

    class BalanceOverflowError(BaseException): pass

    def __init__(self):
        super().__init__()
        self.Language = 'English'
        
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
                        tap_card.HintLabel.setText(Translation.HoldCard[self.Language])
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
                        tap_card.HintLabel.setText(Translation.TapCardAgain[self.Language])
                        self.MFRC522_StopCrypto1()
                    except (self.UnmatchError):
                        tap_card.HintLabel.setText(Translation.NotBorrower[self.Language])
                        self.MFRC522_StopCrypto1()
                    except (self.NotFindError):
                        tap_card.HintLabel.setText(Translation.NoBorrow[self.Language])
                        self.MFRC522_StopCrypto1()
                    except (self.BalanceUnderflowError):
                        tap_card.HintLabel.setText(f'{Translation.InsufficientBalance[self.Language]}, Balance = {self.Balance}')
                        self.MFRC522_StopCrypto1()
                    except (self.BalanceOverflowError):
                        tap_card.HintLabel.setText(f'Balance Overflow')
                        self.MFRC522_StopCrypto1()
                sleep(0.1)
            return result
        return StandardFrame
    
    def Interrupt(self):
        self.InterruptSignal = True
    
    def SetLanguage(self, language):
        self.Language = language


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
    def Balance(balance_data):
        '''Return an int if a list with length 16 is input.'''
        if type(balance_data) == list and len(balance_data) == 16:
            balance = sum([balance_data[1:][i] * (256 ** (-i - 1)) for i in range(-15, 0)])
            balance = balance if balance_data[0] == 0 else -balance
            return balance
        elif type(balance_data) == int:
            if balance_data >= 0:
                balance_data = [0] + [(balance_data % (256 ** -i)) // (256 ** (-i - 1)) for i in range(-15, 0)]
            else:
                balance_data = abs(balance_data)
                balance_data = [1] + [(balance_data % (256 ** -i)) // (256 ** (-i - 1)) for i in range(-15, 0)]
            return balance_data
        else:
            raise TypeError('Input value should be a list with length 16')
    
    @staticmethod
    def HistoryRecord(history_data: list) -> list:
        if type(history_data) == list and len(history_data) == 3:
            locker_data = history_data[0] + history_data[1]
            locker_name = Converter.SystemName(locker_data[:30])
            locker_no = str(Converter.LockerIndex(locker_data[30:]))
            borrow_time_string = Converter.TimeString((Converter.Time(history_data[2][:8])))
            return_time = Converter.Time(history_data[2][8:])
            return_time_string =  Converter.TimeString(return_time) if return_time != 0 else 'Not return yet'
            history_record_list = [locker_name, locker_no, borrow_time_string, return_time_string]
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

    @staticmethod
    def TableView(header_list: list, information_list: list) -> str:
        information_length = list({len(information) for information in information_list})
        if len(information_length) == 1:
            if len(header_list) == information_length[0]:
                whole_list = [header_list] + information_list
                column_length_list = [max([len(str(row_data[i])) for row_data in whole_list]) for i in range(information_length[0])]
                first_row = ''.join([f'+{"-" * (column_length + 2)}' for column_length in column_length_list] + ['+'])
                second_row = ''.join([f'| {header_name}{" " * (column_length_list[i] - len(header_name) + 1)}' for i, header_name in enumerate(header_list)] + ['|'])
                third_row = last_row = str(first_row)
                information_row = [''.join([f'| {str(data)}{" " * (column_length_list[i] - len(str(data)) + 1)}' for i, data in enumerate(record)] + ['|']) for record in information_list]
                information_string = '\n'.join(information_row)
                result = '\n'.join([first_row, second_row, third_row, information_string, last_row])
                return result
            else:
                return 'No Data Found'
        else:
            return 'Invalid Input'


# Thread related
class Threading(QtCore.QThread):
    Result = QtCore.pyqtSignal(str)
    def __init__(self, main_program):
        super().__init__()
        self.MainProgram = main_program
    
    def run(self):
        result = self.MainProgram()
        self.Result.emit(repr(result))


class CurrentTime(Threading):
    def __init__(self):
        super().__init__(None)

    def run(self):
        while True:
            current_time_string = strftime("%Y-%m-%d %H:%M:%S", localtime())
            self.Result.emit(current_time_string)
            sleep(1)


class RollSystemGreeting(Threading):
    def __init__(self):
        super().__init__(None)

    def Set(self, system_greeting):
        system_greeting = f'{" " * ((60 - len(system_greeting)) // 2)}{system_greeting}{" " * ((60 - len(system_greeting)) // 2)}'
        self.system_greeting_list = [char for char in system_greeting]
    
    def run(self):
        while True:
            self.system_greeting_list = self.system_greeting_list[1:] + self.system_greeting_list[:1]
            system_greeting_string = ''.join(self.system_greeting_list)
            self.Result.emit(system_greeting_string)
            sleep(0.1)


# Customized widget class
class CustomizedQWidget(QtWidgets.QWidget):
    def __init__(self, window_title, window_to_screen_ratio=(3, 3), center=True, font_family_size=('Calibri', 18), frameless=True):
        '''size is the magnification against the screen size, i.e. widget size = 640x360 when screen size = 1920x1080 and size = 3'''
        super().__init__()
        # Set widget size and position
        self.setFixedSize(screen_width // window_to_screen_ratio[0], screen_height // window_to_screen_ratio[1])
        if center:
            frame_geometry = self.frameGeometry()
            frame_geometry.moveCenter(center_point)
            self.move(frame_geometry.topLeft())
        # Set font property
        font = QtGui.QFont()
        font.setFamily(font_family_size[0])
        font.setPointSize(font_family_size[1])
        self.setFont(font)
        # Set widget property
        if frameless:
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowTitle(window_title)
        # Set default language
        self.Language = 'English'


class CustomizedQMessageBox(QtWidgets.QMessageBox):
    def __init__(self, message, accept_role_action, *arg):
        super().__init__()
        # Set font property
        font = QtGui.QFont()
        font.setFamily('Calibri')
        font.setPointSize(18)
        self.setFont(font)
        # Set widget property
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        # Set default language
        self.setIcon(self.Warning)
        self.setText(message)
        self.addButton('Corfirm', self.AcceptRole)
        self.addButton('Cancel', self.RejectRole)
        reply = self.exec()
        if reply == self.AcceptRole:
            accept_role_action(*arg)


class CustomizedQPushButton(QtWidgets.QPushButton):
    def __init__(self, button_name):
        super().__init__(button_name)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)


# User input class
class VirtualNumberPadView(CustomizedQWidget):
    def __init__(self):
        super().__init__('VirtualNumPad', (5.3333, 3), False, frameless=False)
        self.KeyToButtonName = {'0': 'Key0Button', '1': 'Key1Button', '2': 'Key2Button', '3': 'Key3Button', '4': 'Key4Button',\
                                '5': 'Key5Button', '6': 'Key6Button', '7': 'Key7Button', '8': 'Key8Button', '9': 'Key9Button',\
                                '⌫': 'BackSpaceButton', ',': 'CommaButton', '-': 'HyphenButton'}
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]} = CustomizedQPushButton("{key}")')
        self.MainLayout.addWidget(self.Key7Button, 0, 0)
        self.MainLayout.addWidget(self.Key8Button, 0, 1)
        self.MainLayout.addWidget(self.Key9Button, 0, 2)
        self.MainLayout.addWidget(self.BackSpaceButton, 0, 3)
        self.MainLayout.addWidget(self.Key4Button, 1, 0)
        self.MainLayout.addWidget(self.Key5Button, 1, 1)
        self.MainLayout.addWidget(self.Key6Button, 1, 2)
        self.MainLayout.addWidget(self.CommaButton, 1, 3)
        self.MainLayout.addWidget(self.Key1Button, 2, 0)
        self.MainLayout.addWidget(self.Key2Button, 2, 1)
        self.MainLayout.addWidget(self.Key3Button, 2, 2)
        self.MainLayout.addWidget(self.HyphenButton, 2, 3)
        self.MainLayout.addWidget(self.Key0Button, 3, 1)
        self.setLayout(self.MainLayout)


class VirtualNumberPadController(VirtualNumberPadView):
    def __init__(self):
        super().__init__()
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]}.clicked.connect(partial(self.InsertText, "{key}"))')
    
    def Connect(self, line_edit, *invalid_character):
        self.LineEditObject = line_edit
        for character in invalid_character:
            exec(f'self.{self.KeyToButtonName[character]}.setEnabled(False)')
        self.show()
    
    def closeEvent(self, event):
        self.LineEditObject = None
        for button in list(self.KeyToButtonName.values()):
            exec(f'self.{button}.setEnabled(True)')
    
    def InsertText(self, key):
        if key != '⌫':
            self.LineEditObject.insert(key)
        else:
            text = self.LineEditObject.text()
            text = text[:-1]
            self.LineEditObject.setText(text)


class VirtualKeyBoardView(CustomizedQWidget):
    def __init__(self):
        super().__init__('VirtualKeyBoard', (1.3714, 2.25), False, frameless=False)
        self.CurrentLetterCase = 'Upper' # Can be 'Upper' or 'Lower'
        self.KeyToButtonName = {'A': 'KeyAButton', 'B': 'KeyBButton', 'C': 'KeyCButton', 'D': 'KeyDButton', 'E': 'KeyEButton',\
                                'F': 'KeyFButton', 'G': 'KeyGButton', 'H': 'KeyHButton', 'I': 'KeyIButton', 'J': 'KeyJButton',\
                                'K': 'KeyKButton', 'L': 'KeyLButton', 'M': 'KeyMButton', 'N': 'KeyNButton', 'O': 'KeyOButton',\
                                'P': 'KeyPButton', 'Q': 'KeyQButton', 'R': 'KeyRButton', 'S': 'KeySButton', 'T': 'KeyTButton',\
                                'U': 'KeyUButton', 'V': 'KeyVButton', 'W': 'KeyWButton', 'X': 'KeyXButton', 'Y': 'KeyYButton',\
                                'Z': 'KeyZButton', '⌫': 'BackSpaceButton', '⇧': 'ShiftButton', ' ': 'SpaceButton'}
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]} = CustomizedQPushButton("{key}")')
        # First Row
        self.MainLayout.addWidget(self.KeyQButton, 0, 2, 3, 3)
        self.MainLayout.addWidget(self.KeyWButton, 0, 5, 3, 3)
        self.MainLayout.addWidget(self.KeyEButton, 0, 8, 3, 3)
        self.MainLayout.addWidget(self.KeyRButton, 0, 11, 3, 3)
        self.MainLayout.addWidget(self.KeyTButton, 0, 14, 3, 3)
        self.MainLayout.addWidget(self.KeyYButton, 0, 17, 3, 3)
        self.MainLayout.addWidget(self.KeyUButton, 0, 20, 3, 3)
        self.MainLayout.addWidget(self.KeyIButton, 0, 23, 3, 3)
        self.MainLayout.addWidget(self.KeyOButton, 0, 26, 3, 3)
        self.MainLayout.addWidget(self.KeyPButton, 0, 29, 3, 3)
        self.MainLayout.addWidget(self.BackSpaceButton, 0, 32, 3, 3)
        # Second Row
        self.MainLayout.addWidget(self.KeyAButton, 3, 3, 3, 3)
        self.MainLayout.addWidget(self.KeySButton, 3, 6, 3, 3)
        self.MainLayout.addWidget(self.KeyDButton, 3, 9, 3, 3)
        self.MainLayout.addWidget(self.KeyFButton, 3, 12, 3, 3)
        self.MainLayout.addWidget(self.KeyGButton, 3, 15, 3, 3)
        self.MainLayout.addWidget(self.KeyHButton, 3, 18, 3, 3)
        self.MainLayout.addWidget(self.KeyJButton, 3, 21, 3, 3)
        self.MainLayout.addWidget(self.KeyKButton, 3, 24, 3, 3)
        self.MainLayout.addWidget(self.KeyLButton, 3, 27, 3, 3)
        # Third Row
        self.MainLayout.addWidget(self.ShiftButton, 6, 1, 3, 3)
        self.MainLayout.addWidget(self.KeyZButton, 6, 4, 3, 3)
        self.MainLayout.addWidget(self.KeyXButton, 6, 7, 3, 3)
        self.MainLayout.addWidget(self.KeyCButton, 6, 10, 3, 3)
        self.MainLayout.addWidget(self.KeyVButton, 6, 13, 3, 3)
        self.MainLayout.addWidget(self.KeyBButton, 6, 16, 3, 3)
        self.MainLayout.addWidget(self.KeyNButton, 6, 19, 3, 3)
        self.MainLayout.addWidget(self.KeyMButton, 6, 22, 3, 3)
        # Fourth Row
        self.MainLayout.addWidget(self.SpaceButton, 9, 9, 3, 17)
        self.setLayout(self.MainLayout)
        

class VirtualKeyBoardController(VirtualKeyBoardView):
    def __init__(self):
        super().__init__()
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]}.clicked.connect(partial(self.InsertText, "{key}"))')
    
    def Connect(self, line_edit):
        self.LineEditObject = line_edit
        self.show()
    
    def closeEvent(self, event):
        self.LineEditObject = None
    
    def InsertText(self, key):
        if key == '⌫':
            text = self.LineEditObject.text()
            text = text[:-1]
            self.LineEditObject.setText(text)
            if len(text) == 0 or text[-1] == ' ':
                self.SetUpper()
            elif text[-1].islower():
                self.SetLower()
        elif key == '⇧':
            if self.CurrentLetterCase == 'Upper':
                self.SetLower()
            elif self.CurrentLetterCase == 'Lower':
                self.SetUpper()
        elif key == ' ':
            self.LineEditObject.insert(' ')
            self.SetUpper()
        else:
            if self.CurrentLetterCase == 'Lower':
                key = key.lower()
            self.LineEditObject.insert(key)
            if self.CurrentLetterCase == 'Upper':
                self.SetLower()
    
    def SetUpper(self):
        self.CurrentLetterCase = 'Upper'
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]}.setText("{key}")')
    
    def SetLower(self):
        self.CurrentLetterCase = 'Lower'
        for key in list(self.KeyToButtonName.keys()):
            exec(f'self.{self.KeyToButtonName[key]}.setText("{key.lower()}")')


# System window
class SystemView(CustomizedQWidget):
    def __init__(self):
        super().__init__('LockerSYstem', (1, 1), True, ('Calibri', 36))
        self.MainLayout = QtWidgets.QGridLayout()
        self.UserInterfaceSetup()
        self.AdminInterfaceSetup()
        self.CommonInterfaceSetup()
        self.setLayout(self.MainLayout)

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
                exec(f'self.LockerButton{index} = CustomizedQPushButton("{index}")')
                exec(f'self.LockerButtonLayout.addWidget(self.LockerButton{index}, {row}, {column})')
        self.LockerButtonFrame.setLayout(self.LockerButtonLayout)
        self.UserInterfaceLayout.addWidget(self.LockerButtonFrame, 0, 0, 7, 1)
        # Second part
        self.FunctionButtonFrame = QtWidgets.QFrame()
        self.FunctionButtonLayout = QtWidgets.QGridLayout()
        self.BorrowButton = CustomizedQPushButton(Translation.Borrow[self.Language])
        self.FunctionButtonLayout.addWidget(self.BorrowButton, 0, 0, 2, 2)
        self.ReturnButton = CustomizedQPushButton(Translation.Return[self.Language])
        self.FunctionButtonLayout.addWidget(self.ReturnButton, 0, 2, 2, 2)
        self.InquireButton = CustomizedQPushButton(Translation.Inquire[self.Language])
        self.FunctionButtonLayout.addWidget(self.InquireButton, 0, 4, 2, 2)
        self.TranslationButton = CustomizedQPushButton(Translation.UiLanguage[self.Language])
        self.FunctionButtonLayout.addWidget(self.TranslationButton, 0, 12, 2, 2)
        self.HelpButton = CustomizedQPushButton(Translation.Help[self.Language])
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
        self.CardManagementButton = CustomizedQPushButton('CardManagement')
        self.AdminFunctionLayout.addWidget(self.CardManagementButton, 0, 0)
        self.DatabaseManagementButton = CustomizedQPushButton('DatabaseManagement')
        self.AdminFunctionLayout.addWidget(self.DatabaseManagementButton, 0, 1)
        self.SystemManagementButton = CustomizedQPushButton('SystemManagement')
        self.AdminFunctionLayout.addWidget(self.SystemManagementButton, 1, 0)
        self.ExitButton = CustomizedQPushButton('Exit')
        self.AdminFunctionLayout.addWidget(self.ExitButton, 1, 1)
        self.AdminFunctionFrame.setLayout(self.AdminFunctionLayout)
        self.AdminInterfaceLayout.addWidget(self.AdminFunctionFrame, 0, 0, 7, 1)
        # Second part
        self.ReturnFrame = QtWidgets.QFrame()
        self.ReturnLayout = QtWidgets.QGridLayout()
        self.UserGuiButton = CustomizedQPushButton('User')
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
        self.ReturnButton.clicked.connect(lambda: locker_return.SelectLocker())
        self.InquireButton.clicked.connect(lambda: inquire.Execute())
        self.TranslationButton.clicked.connect(self.SetUILanguage)
        self.HelpButton.clicked.connect(lambda: help.Display())
        self.RollSystemGreeting = RollSystemGreeting()
        self.RollSystemGreeting.Set(Translation.SystemGreeting[self.Language])
        self.RollSystemGreeting.Result.connect(self.SystemGreetingDisplay)
        self.RollSystemGreeting.start()
        self.CurrentTime = CurrentTime()
        self.CurrentTime.Result.connect(self.CurrentTimeDisplay)
        self.CurrentTime.start()
    
    def SystemGreetingDisplay(self, system_greeting):
        self.SystemGreetingLabel.setText(system_greeting)

    def CurrentTimeDisplay(self, current_time):
        self.TimeLabel.setText(current_time)

    def AdminFunctionConnection(self):
        self.CardManagementButton.clicked.connect(lambda: card_management.show())
        self.DatabaseManagementButton.clicked.connect(lambda: database_management.show())
        self.SystemManagementButton.clicked.connect(lambda: system_management.show())
        self.ExitButton.clicked.connect(lambda: exit_system.show())
        self.UserGuiButton.clicked.connect(partial(self.ShowInterface, 0))
        
    def ShowInterface(self, interface_index):
        for index, interface in enumerate([self.UserInterface, self.AdminInterface]):
            if index == interface_index:
                interface.show()
            else:
                interface.hide()
    
    def mousePressEvent(self, event):
        if self.UserInterface.isVisible():
            self.AdminInterfaceAuthentication(event.x(), event.y())

    def AdminInterfaceAuthentication(self, position_x, position_y):
        if position_x in range(0, screen_width // 16) and position_y in range(0, screen_height//9):
            self.InputAuthenticationKey.append(1)
        elif position_x in range(screen_width - screen_width // 16, screen_width) and position_y in range(0, screen_height//9):
            self.InputAuthenticationKey.append(2)
        elif position_x in range(0, screen_width // 16) and position_y in range(screen_height - screen_height // 9, screen_height):
            self.InputAuthenticationKey.append(3)
        elif position_x in range(screen_width - screen_width // 16, screen_width) and position_y in range(screen_height - screen_height // 9, screen_height):
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
        for index in self.SystemStatus.keys():
            exec(f'self.LockerButton{index}.clicked.connect(partial(self.LockerController, "{index}"))')
    
    def LockerController(self, index):
        if self.SystemStatus[index]['availability'] == 0 or self.SystemStatus[index]['availability'] == 3:
            locker_return.SelectLocker(index)
        elif self.SystemStatus[index]['availability'] == 1:
            locker_borrow.SelectLocker(index)
        elif self.SystemStatus[index]['availability'] == 2:
            locker_maintenance.show()
    
    def SetUILanguage(self):
        if self.Language == 'Chinese':
            set_ui_language('English')
        elif self.Language == 'English':
            set_ui_language('Chinese')
        
    def LockerStatusRefresh(self):
        for index in self.SystemStatus.keys():
            if self.SystemStatus[index]['availability'] == 0 or self.SystemStatus[index]['availability'] == 3:
                exec(f'self.LockerButton{index}.setStyleSheet("background-color: #B95754; border: none; font-size: 36px; font-family: Calibri")')
            elif self.SystemStatus[index]['availability'] == 1:
                exec(f'self.LockerButton{index}.setStyleSheet("background-color: #6B9362; border: none; font-size: 36px; font-family: Calibri")')
            elif self.SystemStatus[index]['availability'] == 2:
                exec(f'self.LockerButton{index}.setStyleSheet("background-color: #FFA400; border: none; font-size: 36px; font-family: Calibri")')
        updated_status = dumps(self.SystemStatus)
        with open(SYSTEM_STATUS_FILE_PATH, 'w') as system_status_file:
            system_status_file.write(updated_status)
    
    def SetLanguage(self, language):
        self.Language = language
        self.BorrowButton.setText(Translation.Borrow[self.Language])
        self.ReturnButton.setText(Translation.Return[self.Language])
        self.InquireButton.setText(Translation.Inquire[self.Language])
        self.TranslationButton.setText(Translation.UiLanguage[self.Language])
        self.HelpButton.setText(Translation.Help[self.Language])
        self.RollSystemGreeting.Set(Translation.SystemGreeting[self.Language])


class SystemModel(SystemController):
    def __init__(self):
        # Get the configuration from the configuration file
        self.SystemConfiguration = system_configuration
        self.SystemStatus = self.__GetSystemStatus()
        self.__SetSystemLog()
        Database.Initialization()
        super().__init__()
    
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


class TapCardView(CustomizedQWidget):
    def __init__(self):
        super().__init__('TapCard')
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.TapCardLabel = QtWidgets.QLabel(Translation.TapCard[self.Language])
        self.TapCardLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.TapCardLabel, 0, 0, 1, 3)
        self.HintLabel = QtWidgets.QLabel('')
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(Translation.Cancel[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 1, 1, 1)
        self.setLayout(self.MainLayout)


class TapCardController(TapCardView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(lambda: mifare_reader.Interrupt())
    
    def closeEvent(self, event):
        self.HintLabel.setText('')
        event.accept()
    
    def SetLanguage(self, language):
        self.Language = language
        self.TapCardLabel.setText(Translation.TapCard[self.Language])
        self.CancelButton.setText(Translation.Cancel[self.Language])


class DisplayView(CustomizedQWidget):
    def __init__(self):
        super().__init__('Display', (1, 1), True, ('Consolas', 24))
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.TextEdit = QtWidgets.QTextEdit()
        self.TextEdit.setReadOnly(True)
        self.MainLayout.addWidget(self.TextEdit, 0, 0, 2, 3)
        self.CancelButton = QtWidgets.QPushButton(Translation.Cancel[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 1)
        self.setLayout(self.MainLayout)


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
    
    def SetLanguage(self, language):
        self.Language = language
        self.CancelButton.setText(Translation.Cancel[self.Language])


# User function window
class LockerBorrowView(CustomizedQWidget):
    def __init__(self):
        super().__init__('LockerBorrow')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.SelectLabel = QtWidgets.QLabel()
        self.SelectLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.SelectLabel, 0, 0, 1, 3)
        self.BorrowHintLabel = QtWidgets.QLabel(Translation.BorrowHint[self.Language])
        self.BorrowHintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.BorrowHintLabel, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(Translation.Cancel[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton(Translation.Confirm[self.Language])
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        for i in range(3):
            self.MainLayout.setColumnStretch(i, 1)
        self.setLayout(self.MainLayout)
    
    def SetLanguage(self, language):
        self.Language = language
        self.BorrowHintLabel.setText(Translation.BorrowHint[self.Language])
        self.CancelButton.setText(Translation.Cancel[self.Language])
        self.ConfirmButton.setText(Translation.Confirm[self.Language])


class LockerBorrowController(LockerBorrowView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.BorrowLockerPreparation)
    
    def SelectLocker(self, index):
        self.SelectedLockerIndex = index
        self.SelectLabel.setText(f'{Translation.SelectMessage[self.Language]} {self.SelectedLockerIndex}')
        self.show()


class LockerBorrowModel(LockerBorrowController):
    def __init__(self):
        super().__init__()
    
    def LockerSelection(self):
        locker_list = list(system.SystemStatus.items())
        locker_list.sort(key=lambda x:x[1]['usage_count'])
        self.SelectLocker(locker_list[0][0])

    def BorrowLockerPreparation(self):
        system_name_byte = Converter.SystemName(system.SystemConfiguration['system_name'])
        locker_index_byte = Converter.LockerIndex(int(self.SelectedLockerIndex))
        self.SystemData = system_name_byte + locker_index_byte
        self.StartTime = int(time())
        self.TimeData = Converter.Time(self.StartTime) + [0] * 8
        self.Execute()
        
    def Execute(self):
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(tap_card.show)
        self.Thread.Result.connect(self.StatusUpate)
        self.Thread.start()

    def MainProgram(self, uid, access_key):
        mifare_reader.MFRC522_Auth(uid, 4, access_key)
        balance_data = mifare_reader.MFRC522_Read(4)
        balance = Converter.Balance(balance_data)
        if balance < 0:
            mifare_reader.Balance = balance
            raise mifare_reader.BalanceUnderflowError
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
    
    def StatusUpate(self, result):
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            result = eval(result)
            student_info_data = result[0] + result[1]
            student_id = Converter.StudentId(student_info_data[:6])
            student_name = Converter.StudentName(student_info_data[6:])
            system.SystemStatus[self.SelectedLockerIndex]['availability'] = 0
            system.SystemStatus[self.SelectedLockerIndex]['student_name'] = student_name
            system.SystemStatus[self.SelectedLockerIndex]['student_id'] = student_id
            system.SystemStatus[self.SelectedLockerIndex]['start_time'] = self.StartTime
            system.SystemStatus[self.SelectedLockerIndex]['usage_count'] += 1
            time_string = Converter.TimeString(self.StartTime)
            system.SystemLogWrite(f'{time_string} Borrow - Locker {self.SelectedLockerIndex} was borrowed by {student_id} {student_name}')
            system.LockerStatusRefresh()
            Database.HistoryRecordUpdateBorrow(student_id, self.SelectedLockerIndex, time_string)


class LockerReturnView(CustomizedQWidget):
    def __init__(self):
        super().__init__('LockerReturn')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.SelectLabel = QtWidgets.QLabel()
        self.SelectLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.SelectLabel, 0, 0, 1, 3)
        self.ReturnHintLabel = QtWidgets.QLabel(Translation.ReturnHint[self.Language])
        self.ReturnHintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.ReturnHintLabel, 1, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(Translation.Cancel[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 0)
        self.ConfirmButton = QtWidgets.QPushButton(Translation.Confirm[self.Language])
        self.MainLayout.addWidget(self.ConfirmButton, 2, 2)
        self.setLayout(self.MainLayout)

    def SetLanguage(self, language):
        self.Language = language
        self.ReturnHintLabel.setText(Translation.ReturnHint[self.Language])
        self.CancelButton.setText(Translation.Cancel[self.Language])
        self.ConfirmButton.setText(Translation.Confirm[self.Language])


class LockerReturnController(LockerReturnView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)
        self.ConfirmButton.clicked.connect(self.ReturnLockerPreparation)
    
    def SelectLocker(self, index=None):
        self.SelectedLockerIndex = index
        if self.SelectedLockerIndex == None:
            self.ReturnLockerPreparation()
        else:
            self.SelectLabel.setText(f'{Translation.SelectMessage[self.Language]} {self.SelectedLockerIndex}')
            self.show()


class LockerReturnModel(LockerReturnController):
    def __init__(self):
        super().__init__()

    def ReturnLockerPreparation(self):
        if self.SelectedLockerIndex == None:
            self.SystemDict = {}
            student_id_set = {system.SystemStatus[i]['student_id'] for i in system.SystemStatus.keys() if system.SystemStatus[i]['student_id']}
            for student_id in student_id_set:
                temp = [index for index in list(system.SystemStatus.keys()) if system.SystemStatus[index]['student_id'] == student_id]
                temp.sort(key=lambda x: system.SystemStatus[x]['start_time'])
                self.SystemDict[student_id] = temp
        else:
            self.StudentIdForSelectedLocker = system.SystemStatus[self.SelectedLockerIndex]['student_id']
            self.StartTimeData = Converter.Time(system.SystemStatus[self.SelectedLockerIndex]['start_time'])
            self.LockerIndexData = Converter.LockerIndex(int(self.SelectedLockerIndex))
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
        student_id = Converter.StudentId(access_key)
        if self.SelectedLockerIndex != None and student_id != self.StudentIdForSelectedLocker:
            raise mifare_reader.UnmatchError
        elif self.SelectedLockerIndex == None:
            if student_id in self.SystemDict:
                self.SelectedLockerIndex = self.SystemDict[student_id][0]
                self.LockerIndexData = Converter.LockerIndex(int(self.SelectedLockerIndex))
            else:
                raise mifare_reader.NotFindError
        self.StartTime = system.SystemStatus[self.SelectedLockerIndex]['start_time']
        self.StartTimeData = Converter.Time(self.StartTime)
        time_elapsed = self.EndTime - self.StartTime
        mifare_reader.MFRC522_Auth(uid, 4, access_key)
        balance_data = mifare_reader.MFRC522_Read(4)
        balance = Converter.Balance(balance_data)
        balance -= time_elapsed
        balance_data = Converter.Balance(balance)
        mifare_reader.MFRC522_Auth(uid, 9, access_key)
        block9_data = mifare_reader.MFRC522_Read(9)
        for x in range(11):
            if x == 10:
                raise mifare_reader.UnmatchError
            if block9_data[x] == 1:
                mifare_reader.MFRC522_Auth(uid, 4 * x + 14, access_key)
                if mifare_reader.MFRC522_Read(4 * x + 14)[:8] == self.StartTimeData and mifare_reader.MFRC522_Read(4 * x + 13)[-2:] == self.LockerIndexData:
                    break
        mifare_reader.MFRC522_Write(4 * x + 14, self.StartTimeData + self.EndTimeData)
        block9_data[x] = 0
        mifare_reader.MFRC522_Auth(uid, 9, access_key)
        mifare_reader.MFRC522_Write(9, block9_data)
        mifare_reader.MFRC522_Auth(uid, 4, access_key)
        mifare_reader.MFRC522_Write(4, balance_data)

    def StatusUpate(self):
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            availability = system.SystemStatus[self.SelectedLockerIndex]['availability']
            student_name = system.SystemStatus[self.SelectedLockerIndex]['student_name']
            student_id = system.SystemStatus[self.SelectedLockerIndex]['student_id']
            borrow_time = system.SystemStatus[self.SelectedLockerIndex]['start_time']
            system.SystemStatus[self.SelectedLockerIndex]['availability'] = 1 if availability != 3 else 2
            system.SystemStatus[self.SelectedLockerIndex]['student_name'] = None
            system.SystemStatus[self.SelectedLockerIndex]['student_id'] = None
            system.SystemStatus[self.SelectedLockerIndex]['start_time'] = None
            borrow_time_string = Converter.TimeString(borrow_time)
            return_time_string = Converter.TimeString(self.EndTime)
            system.SystemLogWrite(f'{return_time_string} Return - Locker {self.SelectedLockerIndex} was return by {student_id} {student_name}\n')
            system.LockerStatusRefresh()
            Database.HistoryRecordUpdateReturn(student_id, self.SelectedLockerIndex, borrow_time_string, return_time_string)


class LockerMaintenanceView(CustomizedQWidget):
    def __init__(self):
        super().__init__('LockerMaintenance')
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.MaintenanceHintLabel = QtWidgets.QLabel(Translation.MaintenanceHint[self.Language])
        self.MaintenanceHintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.MaintenanceHintLabel, 0, 0, 1, 3)
        self.CancelButton = QtWidgets.QPushButton(Translation.Cancel[self.Language])
        self.MainLayout.addWidget(self.CancelButton, 2, 1)
        self.setLayout(self.MainLayout)
    
    def SetLanguage(self, language):
        self.Language = language
        self.MaintenanceHintLabel.setText(Translation.MaintenanceHint[self.Language])
        self.CancelButton.setText(Translation.Cancel[self.Language])


class LockerMaintenanceController(LockerMaintenanceView):
    def __init__(self):
        super().__init__()
        self.CancelButton.clicked.connect(self.close)


class Inquire(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.Language = 'English'
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.Result.connect(self.DisplayInquire)
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
    
    def DisplayInquire(self, result):
        tap_card.close()
        if result:
            block1_data, block2_data, block4_data, history_data = eval(result)
            student_data = block1_data + block2_data
            student_id = Converter.StudentId(student_data[:6])
            student_name = Converter.StudentName(student_data[6:])
            balance = Converter.Balance(block4_data)
            if len(history_data) != 0:
                history_data_list = [Converter.HistoryRecord(data) for data in history_data]
                history_data_list.sort(key=lambda x: x[2])
            else:
                history_data_list = []
            student_info = '\n'.join([f'Student Name: {student_name}', f'Student ID: {student_id}', f'Balance: {balance}', 'History Record:'])
            table_string = Converter.TableView(['Locker Location', 'Index', 'Borrow Time', 'Return Time'], history_data_list)
            formatted_string = '\n'.join([student_info, table_string])
            display.Display(formatted_string)

    def SetLanguage(self, language):
        self.Language = language


class Help(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.Language = 'English'

    def Display(self):
        display.Display(Translation.UserHelp[self.Language])

    def SetLanguage(self, language):
        self.Language = language


# Admin function window
# Card related
class CardManagementView(CustomizedQWidget):
    def __init__(self):
        super().__init__('CardManagaement')
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


class CardInitializationView(CustomizedQWidget):
    def __init__(self):
        super().__init__('CardInitialization')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.InputHintLabel = QtWidgets.QLabel('Please input:')
        self.InputHintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.InputHintLabel, 0, 2, 1, 2)
        self.StudentIdLabel = QtWidgets.QLabel('Student ID:')
        self.StudentIdLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.StudentIdLabel, 1, 0, 1, 2)
        self.StudentIdLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentIdLineEdit, 1, 2, 1, 3)
        self.VirtualNumPadButton = QtWidgets.QPushButton('⌨')
        self.MainLayout.addWidget(self.VirtualNumPadButton, 1, 5)
        self.StudentNameLabel = QtWidgets.QLabel('Student Name:')
        self.StudentNameLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.StudentNameLabel, 2, 0, 1, 2)
        self.StudentNameLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.StudentNameLineEdit, 2, 2, 1, 3)
        self.VirtualKeyboardButton = QtWidgets.QPushButton('⌨')
        self.MainLayout.addWidget(self.VirtualKeyboardButton, 2, 5)
        self.HintLabel = QtWidgets.QLabel()
        self.HintLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.HintLabel, 3, 0, 1, 6)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 4, 0, 1, 2)
        self.MainLayout.addWidget(QtWidgets.QLabel(), 4, 2, 1, 2)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ComfirmButton, 4, 4, 1, 2)
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
        self.VirtualNumPadButton.clicked.connect(lambda: virtual_number_pad.Connect(self.StudentIdLineEdit, ',', '-'))
        self.VirtualKeyboardButton.clicked.connect(lambda: virtual_keyboard.Connect(self.StudentNameLineEdit))
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
        self.Thread.Result.connect(self.DatabaseUpdate)
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
    
    def DatabaseUpdate(self, result):
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            uid = eval(result)
            initialization_time_string = Converter.TimeString(int(time()))
            Database.UserRegistrationUpdate(uid, self.student_name, self.student_id, initialization_time_string)


class CardReset(QtCore.QObject):
    def __init__(self):
        super().__init__()
    
    def ShowWarning(self):
        warning_messagebox = CustomizedQMessageBox(f'You are going to reset your card.\nAre you sure?', self.Execute)
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.Result.connect(self.DatabaseUpdate)
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
    
    def DatabaseUpdate(self, result):
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            access_key = eval(result)
            student_id = Converter.StudentId(access_key)
            Database.UserRegistrationDelectRecord(student_id)


class CardDump(QtCore.QObject):
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.Result.connect(self.DisplayCardData)
        self.Thread.start()
    
    def MainProgram(self, uid, access_key):
        card_data = []
        for sector in range(16):
            key = mifare_reader.DEFAULT_KEY if sector == 0 else access_key
            mifare_reader.MFRC522_Auth(uid, 4 * sector, key)
            card_data.append([mifare_reader.MFRC522_Read(4 * sector + block) for block in range(4)])
        return card_data

    def DisplayCardData(self, result):
        tap_card.close()
        if mifare_reader.InterruptSignal == False:
            display.show()
            display.TextEdit.setText(f'{pformat(eval(result))}')


class BalanceView(CustomizedQWidget):
    def __init__(self):
        super().__init__('Balance')
        # Interface setup
        self.MainLayout = QtWidgets.QGridLayout(self)
        self.TopupLabel = QtWidgets.QLabel('Please input the top-up value')
        self.TopupLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.TopupLabel, 0, 0, 1, 6)
        self.BalanceLineEdit = QtWidgets.QLineEdit()
        self.MainLayout.addWidget(self.BalanceLineEdit, 1, 0, 1, 5)
        self.VirtualNumPadButton = QtWidgets.QPushButton('⌨')
        self.MainLayout.addWidget(self.VirtualNumPadButton, 1, 5)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 2, 0, 1, 2)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.MainLayout.addWidget(self.ComfirmButton, 2, 4, 1, 2)
        self.setLayout(self.MainLayout)


class BalanceController(BalanceView):
    def __init__(self):
        super().__init__()
        self.BalanceLineEdit.setMaxLength(8)
        self.BalanceLineEdit.textChanged.connect(self.BalanceValidate)
        self.VirtualNumPadButton.clicked.connect(lambda: virtual_number_pad.Connect(self.BalanceLineEdit, ',', '-'))
        self.CancelButton.clicked.connect(self.close)
        self.ComfirmButton.setEnabled(False)
        self.ComfirmButton.clicked.connect(self.Execute)
    
    def BalanceValidate(self, text):
        pattern = QtCore.QRegExp('^[1-9]\d{0,7}$')
        validator = QtGui.QRegExpValidator(pattern)
        if validator.validate(text, 0)[0] == 2:
            self.ComfirmButton.setEnabled(True)
        else:
            self.ComfirmButton.setEnabled(False)

    def closeEvent(self, event):
        self.BalanceLineEdit.clear()


class BalanceModel(BalanceController):
    def __init__(self):
        super().__init__()
    
    def Execute(self):
        self.value = self.BalanceLineEdit.text()
        self.value = int(self.value)
        self.close()
        self.Thread = Threading(mifare_reader.StandardFrame(self.MainProgram))
        self.Thread.started.connect(lambda: tap_card.show())
        self.Thread.finished.connect(self.DatabaseUpdate)
        self.Thread.start()
    
    def MainProgram(self, uid, access_key):
        mifare_reader.MFRC522_Auth(uid, 4, access_key)
        balance_data = mifare_reader.MFRC522_Read(4)
        balance = Converter.Balance(balance_data)
        balance += self.value
        if abs(balance) > 256 ** 15:
            raise mifare_reader.BalanceOverflowError
        balance_data = Converter.Balance(balance)
        mifare_reader.MFRC522_Write(4, balance_data)
    
    def DatabaseUpdate(self):
        tap_card.close()
        # TODO: Updata Database


# Database related
class DatabaseManagementView(CustomizedQWidget):
    def __init__(self):
        super().__init__('DatabaseManagaement')
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


class PrintDatabaseView(CustomizedQWidget):
    def __init__(self):
        super().__init__('PrintDatabase')
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
        column_name = Database.PrintColumnName(table)
        column_name = [data[0] for data in column_name]
        search_result = Database.PrintAllRecord(table)
        formatted_string = Converter.TableView(column_name, search_result)
        self.close()
        display.Display(formatted_string)
    
    def CloseWindow(self):
        self.close()
        database_management.show()


class ResetDatabaseView(CustomizedQWidget):
    def __init__(self):
        super().__init__('PrintDatabase')
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
        warning_messagebox = CustomizedQMessageBox(f'You are going to reset table {table}.\nAre you sure?', self.ResetTable, table)

    def ResetTable(self, table):
        Database.ResetTable(table)
    
    def CloseWindow(self):
        self.close()
        database_management.show()
    

class SystemManagementView(CustomizedQWidget):
    def __init__(self):
        super().__init__('DatabaseManagaement')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.SetMaintenanceButton = QtWidgets.QPushButton('SetMaintenance')
        self.SetMaintenanceButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.SetMaintenanceButton, 0, 0, 8, 3)
        self.ResetMaintenanceButton = QtWidgets.QPushButton('ResetMaintenance')
        self.ResetMaintenanceButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ResetMaintenanceButton, 8, 0, 8, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class SystemManagementController(SystemManagementView):
    def __init__(self):
        super().__init__()
        self.SetMaintenanceButton.clicked.connect(partial(self.SetMaintenance, 0))
        self.ResetMaintenanceButton.clicked.connect(partial(self.SetMaintenance, 1))
        self.CancelButton.clicked.connect(self.close)
    
    def SetMaintenance(self, mode):
        maintenance.SetMode(mode)
        self.close()
        maintenance.show()
        maintenance.Execute()


class MaintenceView(CustomizedQWidget):
    def __init__(self):
        super().__init__('Maintenance')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.PromptLabel = QtWidgets.QLabel()
        self.PromptLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.MainLayout.addWidget(self.PromptLabel, 0, 0, 1, 6)
        self.InputLineEdit = QtWidgets.QLineEdit()
        self.InputLineEdit.setReadOnly(True)
        self.MainLayout.addWidget(self.InputLineEdit, 1, 0, 1, 5)
        self.VirtualNumPadButton = QtWidgets.QPushButton('⌨')
        self.MainLayout.addWidget(self.VirtualNumPadButton, 1, 5)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 4, 0, 1, 2)
        self.MainLayout.addWidget(QtWidgets.QLabel(), 4, 2, 1, 2)
        self.ComfirmButton = QtWidgets.QPushButton('Comfirm')
        self.ComfirmButton.setEnabled(False)
        self.MainLayout.addWidget(self.ComfirmButton, 4, 4, 1, 2)
        self.setLayout(self.MainLayout)
        # 0 = Set, 1 = Reset
        self.Prompt = {0: 'Please input the locker index for maintenance', 1: 'Please input the locker index that finish maintenance'}


class MaintenanceController(MaintenceView):
    OkSignal = QtCore.pyqtSignal(bool)
    def __init__(self):
        super().__init__()
        self.VirtualNumPadButton.clicked.connect(lambda: virtual_number_pad.Connect(self.InputLineEdit))
        self.CancelButton.clicked.connect(self.close)
        self.ComfirmButton.clicked.connect(self.MaintenancePreparation)
        self.InputLineEdit.textChanged.connect(self.MaintenanceValidate)
        self.OkSignal.connect(self.InputOk)

    def SetMode(self, mode):
        self.Mode = mode
        self.PromptLabel.setText(self.Prompt[mode])
    
    def MaintenanceValidate(self, text):
        self.OkSignal.emit(False)
        pattern = QtCore.QRegExp('^(0|[1-9]\d*)(\-[1-9]\d*)?(,(0|[1-9]\d*)(\-[1-9]\d*)?)*$')
        validator = QtGui.QRegExpValidator(pattern)
        if validator.validate(text, 0)[0] == 2:
            self.OkSignal.emit(True)
    
    def InputOk(self, value):
        self.ComfirmButton.setEnabled(value)
    
    def closeEvent(self, event):
        self.InputLineEdit.clear()
        event.accept()


class MaintenanceModel(MaintenanceController):
    def __init__(self):
        super().__init__()
    
    def InputStringAnalyzer(self, input_string):
        result = []
        input_string_list = input_string.split(',')
        for string in input_string_list:
            if '-' in string:
                temp_string = string.split('-')
                start, end = min(temp_string), max(temp_string)
                temp = [str(i) for i in range(int(start), int(end) + 1)]
                result += temp
            else:
                result.append(string)
        result = list(set(result))
        result.sort()
        return result
    
    def MaintenancePreparation(self):
        input_text = self.InputLineEdit.text()
        result = self.InputStringAnalyzer(input_text)
        max_index = list(system.SystemStatus.keys())[-1]
        result = [i for i in result if int(i) <= int(max_index)]
        current_time = int(time())
        time_string = Converter.TimeString(current_time)
        if self.Mode == 0:
            for index in result:
                locker_current_availability = system.SystemStatus[index]['availability']
                if locker_current_availability == 0:
                    system.SystemStatus[index]['availability'] = 3
                else:
                    system.SystemStatus[index]['availability'] = 2
                system.SystemLogWrite(f'{time_string} Start Maintenance - Locker {index}')
        elif self.Mode == 1:
            for index in result:
                locker_current_availability = system.SystemStatus[index]['availability']
                if locker_current_availability == 2:
                    system.SystemStatus[index]['availability'] = 1
                    system.SystemLogWrite(f'{time_string} Finitsh Maintenance - Locker {index}')
        system.LockerStatusRefresh()
        self.close()


class ExitSystemView(CustomizedQWidget):
    def __init__(self):
        super().__init__('Exit')
        # Interface layout setup
        self.MainLayout = QtWidgets.QGridLayout()
        self.ExitSystemButton = QtWidgets.QPushButton('ExitSystem')
        self.ExitSystemButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.ExitSystemButton, 0, 0, 5, 3)
        self.RestartSystemButton = QtWidgets.QPushButton('RestartSystem')
        self.RestartSystemButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.RestartSystemButton, 5, 0, 5, 3)
        self.PowerOffButton = QtWidgets.QPushButton('PowerOff')
        self.PowerOffButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.MainLayout.addWidget(self.PowerOffButton, 10, 0, 5, 3)
        self.CancelButton = QtWidgets.QPushButton('Cancel')
        self.MainLayout.addWidget(self.CancelButton, 17, 1, 2, 1)
        self.setLayout(self.MainLayout)


class ExitSystemController(ExitSystemView):
    def __init__(self):
        super().__init__()
        self.ExitSystemButton.clicked.connect(partial(self.ActionConfirm, 'ExitSystem'))
        self.RestartSystemButton.clicked.connect(partial(self.ActionConfirm, 'RestartSystem'))
        self.PowerOffButton.clicked.connect(partial(self.ActionConfirm, 'PowerOff'))
        self.CancelButton.clicked.connect(self.close)


class ExitSystemModel(ExitSystemController):
    def __init__(self):
        super().__init__()
        self.PID = getpid()

    def ActionConfirm(self, mode):
        self.close()
        if mode == 'ExitSystem':
            CustomizedQMessageBox(f'Are you sure to {mode}?', self.ExitSystem)
        elif mode == 'RestartSystem':
            CustomizedQMessageBox(f'Are you sure to {mode}?', self.RestartSystem)
        elif mode == 'PowerOff':
            CustomizedQMessageBox(f'Are you sure to {mode}?', self.PowerOff)

    def ExitSystem(self):
        GPIO.cleanup()
        exit(0)

    def RestartSystem(self):
        GPIO.cleanup()
        Popen(['python3', EXTERNAL_CONTROLLER_PATH, f'{self.PID}', 'Restart'])

    def PowerOff(self):
        GPIO.cleanup()
        Popen(['python3', EXTERNAL_CONTROLLER_PATH, f'{self.PID}', 'PowerOff'])


def set_ui_language(language):
    mifare_reader.SetLanguage(language)
    system.SetLanguage(language)
    tap_card.SetLanguage(language)
    display.SetLanguage(language)
    locker_borrow.SetLanguage(language)
    locker_return.SetLanguage(language)
    locker_maintenance.SetLanguage(language)
    help.SetLanguage(language)


if __name__ == '__main__':
    if exists(SYSTEM_CONFIGURATION_FILE_PATH):
        GPIO.setwarnings(False)
        app = QtWidgets.QApplication(argv)
        # Get screen information
        current_screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        screen_width = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().width()
        screen_height = QtWidgets.QApplication.desktop().screenGeometry(current_screen).size().height()
        center_point = QtWidgets.QApplication.desktop().screenGeometry(current_screen).center()
        # Class initialization
        mifare_reader = MFRC522libExtension()
        virtual_number_pad = VirtualNumberPadController()
        virtual_keyboard = VirtualKeyBoardController()
        system = SystemModel()
        tap_card = TapCardController()
        display = DisplayController()
        locker_borrow = LockerBorrowModel()
        locker_return = LockerReturnModel()
        locker_maintenance = LockerMaintenanceController()
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
        system_management = SystemManagementController()
        maintenance = MaintenanceModel()
        exit_system = ExitSystemModel()
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
