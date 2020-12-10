from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from SampleUserGUI import SampleUserGUI
import System


class SampleUserGUIExtension(SampleUserGUI):
    def __init__(self):
        self.system_configuration_data = System.system_configuration()
        self.system_status_data = System.system_status(self.system_configuration_data)
        super().__init__()
        self.locker_dict = dict(zip([str(i) for i in range(1, 10)], self.locker_list()))
        self.reflesh()
    
    def reflesh(self):
        self.system_available, self.system_using, self.system_unavailable = System.get_system_status(self.system_status_data)
        for i in self.system_available:
            self.locker_dict[i].setStyleSheet('QPushButton {background-color: green; border: none}')
        for i in self.system_using:
            self.locker_dict[i].setStyleSheet('QPushButton {background-color: red; border: none}')
        for i in self.system_unavailable:
            self.locker_dict[i].setStyleSheet('QPushButton {background-color: yellow; border: none}')
    
    def locker_function(self, user_selection):
        if user_selection in self.system_available or user_selection == 'borrow':
            self.system_status_data = System.borrow_locker(self.system_configuration_data, self.system_status_data, self.system_available, user_selection)
            self.reflesh()
            return
        if user_selection in self.system_using or user_selection == 'return':
            self.system_status_data = System.return_locker(self.system_status_data, user_selection)
            self.reflesh()
            return


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    sampleusergui = SampleUserGUIExtension()
    sampleusergui.show()
    sys.exit(app.exec_())
