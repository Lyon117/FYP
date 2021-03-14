from csv import writer
from functools import wraps
from json import dumps
from os.path import dirname, exists, join


SYSTEM_CONFIGURATION_FILE_PATH = join(dirname(__file__), 'Config.json')


def system_configuration_initialization():
    '''Setup the system configuration file'''
    system_name = get_system_name()
    system_code = get_system_code()
    locker_column = get_locker_column()
    locker_row = get_locker_row()
    system_greeting = get_system_greeting(system_name)
    system_configuration_data = {'system_name': system_name, 'system_code': system_code, 'locker_column': locker_column, 'locker_row': locker_row, 'system_greeting_en': system_greeting[0], 'system_greeting_tc': system_greeting[1]}
    system_configuration_data = dumps(system_configuration_data, indent=4)
    with open(SYSTEM_CONFIGURATION_FILE_PATH, 'w', encoding='utf-8') as system_configuration_file:
        system_configuration_file.write(system_configuration_data)


def empty_input_validator(input_function):
    @wraps(input_function)
    def empty_input_validator():
        while 1:
            input_value = input_function()
            if input_value == '':
                print('This input should not be empty.')
            else:
                break
        return input_value
    return empty_input_validator


def int_input_validator(input_function):
    @wraps(input_function)
    def int_input_validator():
        while 1:
            try:
                input_value = int(input_function())
                break
            except ValueError:
                print('This input should be an interger.')
        return input_value
    return int_input_validator


@empty_input_validator
def get_system_name() -> str:
    system_name = input('Please input your system name:\n')
    return system_name


@empty_input_validator
def get_system_code() -> str:
    system_code = input('Please input your system code:\n')
    return system_code


@int_input_validator
def get_locker_column() -> int:
    locker_column = input('Please input the number of column of the system:\n')
    return locker_column


@int_input_validator
def get_locker_row() -> int:
    locker_row = input('Please input the number of row of the system:\n')
    return locker_row


def get_system_greeting(system_name: str) -> str:
    system_greeting_list = list()
    for language in ['English', 'Chinese']:
        system_greeting = input(f'Please input the system greeting for {language}:\n')
        if system_greeting == '' and language == 'English':
            system_greeting = f'Welcome to use {system_name}'
        elif system_greeting == '' and language == 'Chinese':
            system_greeting = f'歡迎來使用 {system_name}'
        system_greeting_list.append(system_greeting)
    return system_greeting_list


if __name__ == "__main__":
    system_configuration_initialization()
