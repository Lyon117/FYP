from csv import writer
from functools import wraps
from os.path import exists, join
from pickle import dump, load


SYSTEM_CONFIGURATION_FILE_PATH = join('.', 'Config.data')
SYSTEM_STATUS_FILE_PATH = join('.', 'Status.data')
SYSTEM_LOG_FILE_PATH = join('.', 'Log.data')


def system_configuration_initialization():
    '''Setup the system configuration file'''
    system_name = get_system_name()
    system_code = get_system_code()
    locker_column = get_locker_column()
    locker_row = get_locker_row()
    system_greeting = get_system_greeting(system_name)
    system_configuration_data = {'system_name': system_name, 'system_code': system_code, 'locker_column': locker_column, 'locker_row': locker_row, 'system_greeting_en': system_greeting[0], 'system_greeting_tc': system_greeting[1]}
    with open(SYSTEM_CONFIGURATION_FILE_PATH, 'wb') as system_configuration_file:
        dump(system_configuration_data, system_configuration_file)


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


@empty_input_validator
@int_input_validator
def get_locker_column() -> int:
    locker_column = input('Please input the number of column of the system:\n')
    return locker_column


@empty_input_validator
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


def system_configuration_alteration():
    with open(SYSTEM_CONFIGURATION_FILE_PATH, 'rb') as system_configuration_file:
        system_configuration_data = load(system_configuration_file)
    # Need modify the following two list when add more alterable item
    alterable_item_list = ['Change system name', 'Change system code', 'Change system greeting']
    alterable_function_list = ['get_system_name()', 'get_system_code()', 'get_system_greeting(system_configuration_data[\'system_name\'])']
    while True:
        user_input = get_alterate_option(alterable_item_list)
        input_value = alterable_function_list[user_input]
        system_configuration_data[list(system_configuration_data.keys())[user_input]] = eval(input_value)
        with open(SYSTEM_CONFIGURATION_FILE_PATH, 'wb') as system_configuration_file:
            dump(system_configuration_data, system_configuration_file)


def alterate_option_validator(input_function):
    @wraps(input_function)
    def alterate_option_validator(*args, **kwargs):
        while True:
            option_length, input_value = input_function(*args, **kwargs)
            try:
                input_value = int(input_value)
            except ValueError:
                pass
            if input_value in range(option_length):
                break
            elif input_value.lower() == 'q':
                exit(0)
            else:
                print('Invalid input')
        return input_value
    return alterate_option_validator 


@alterate_option_validator
def get_alterate_option(alterable_item_list):
    for index, item in enumerate(alterable_item_list):
        print(f'{index} - {item}')
    user_input = input('You can ENTER the index to alterate the correponding item, or \'q\' to exit.\n')
    return len(alterable_item_list), user_input


def system_status_initialization():
    with open(SYSTEM_CONFIGURATION_FILE_PATH, 'rb') as system_configuration_file:
        system_configuration_data = load(system_configuration_file)
    locker_column = system_configuration_data['locker_column']
    locker_row = system_configuration_data['locker_row']
    locker_number = locker_column * locker_row
    system_status_data = {f'{index}': {'availability': 1, 'student_name': None, 'student_id': None, 'start_time': None, 'usage_count': 0} for index in range(locker_number)}
    with open(SYSTEM_STATUS_FILE_PATH, 'wb') as system_status_file:
        dump(system_status_data, system_status_file)


def system_log_initialization():
    with open(SYSTEM_LOG_FILE_PATH, 'w', encoding='utf-8-sig', newline='') as system_log_file:
        writer(system_log_file).writerow([f'{"Time":<19}', 'Event'])


if __name__ == "__main__":
    if exists(SYSTEM_CONFIGURATION_FILE_PATH):
        system_configuration_alteration()
    else:    
        system_configuration_initialization()
        system_status_initialization()
        system_log_initialization()
