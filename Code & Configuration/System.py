import json
import MFRC522lib
import MFRC522libExtension
import os
import os.path
import RPi.GPIO as GPIO
import SampleGUIApplication
import time


def system_configuration():
    system_configuration_file = os.path.join(os.getcwd(), 'SystemConfiguration.json')
    if not os.path.exists(system_configuration_file):
        print('Missing the system configuration file.')
        print('You now in system configuration.')
        system_configuration_data = {'system_name': '', 'system_code': '', 'no_of_locker': ''}
        for x in system_configuration_data:
            input_data = input(f'Please input {x}:\n')
            system_configuration_data[x] = input_data if x != 'no_of_locker' else int(input_data)
        system_configuration_data = json.dumps(system_configuration_data, sort_keys=True, indent=4, separators=(',', ': '))
        with open(system_configuration_file, 'w', encoding='utf-8-sig') as f:
            f.write(system_configuration_data)
    with open(system_configuration_file, 'r', encoding='utf-8-sig') as f:
        system_configuration_data = f.read()
    return json.loads(system_configuration_data)


def system_status(system_configuration_data):
    system_status_file = os.path.join(os.getcwd(), 'SystemStatus.json')
    if not os.path.exists(system_status_file):
        system_status_key = [str(x) for x in range(1, int(system_configuration_data['no_of_locker']) + 1)]
        system_status_data = [{'availability': 'available', 'student_name': '', 'student_id': '', 'start_time': '', 'usage_count': 0} for x in range(system_configuration_data['no_of_locker'])]
        system_status_data = dict(zip(system_status_key, system_status_data))
        system_status_data = json.dumps(system_status_data, sort_keys=True, indent=4, separators=(',', ': '))
        with open(system_status_file, 'w', encoding='utf-8-sig') as f:
            f.write(system_status_data)
    with open(system_status_file, 'r', encoding='utf-8-sig') as f:
        system_status_data = f.read()
    return json.loads(system_status_data)


def get_system_status(system_status_data):
    system_available = [x for x in system_status_data if system_status_data[x]['availability'] == 'available']
    system_using = [x for x in system_status_data if system_status_data[x]['availability'] == 'using']
    system_unavailable = [x for x in system_status_data if system_status_data[x]['availability'] == 'unavailable']
    return system_available, system_using, system_unavailable


def borrow_locker(system_configuration_data, system_status_data, system_available, user_selection):
    MIFAREReader = MFRC522libExtension.MFRC522libExtension()
    system_name = system_configuration_data['system_name']
    system_name_data = [ord(x) for x in system_name]
    system_name_data += [0] * (30 - len(system_name_data))
    if user_selection == 'borrow':
        if len(system_available) == 0:
            print('No locker available')
            return
        else:
            usage_count_list = list(zip(system_available, [system_status_data[x]['usage_count'] for x in system_available]))
            usage_count_list.sort(key=lambda x: x[1])
            user_selection = usage_count_list[0][0]
    system_data = system_name_data + [int(user_selection) // 256, int(user_selection) % 256]
    start_time = int(time.mktime(time.localtime()))
    start_time_data = '0' * (16 - len(hex(start_time)[2:])) + hex(start_time)[2:]
    start_time_data = [int(start_time_data[2 * x:2 * x + 2], 16) for x in range(8)] + [0] * 8

    def borrow_locker_rfid():
        @MIFAREReader.standard_frame(locker=user_selection, system_data=system_data, start_time_data=start_time_data)
        def borrow_locker_rfid(access_key, uid, system_data, start_time_data):
            MIFAREReader.MFRC522_Auth(uid, 1, MIFAREReader.DEFAULT_KEY)
            block1_data = MIFAREReader.MFRC522_Read(1)
            block2_data = MIFAREReader.MFRC522_Read(2)
            MIFAREReader.MFRC522_Auth(uid, 8, access_key)
            block8_data = MIFAREReader.MFRC522_Read(8)
            block9_data = MIFAREReader.MFRC522_Read(9)
            write_position = block8_data.index(1)
            MIFAREReader.MFRC522_Auth(uid, 12 + write_position * 4, access_key)
            MIFAREReader.MFRC522_Write(12 + write_position * 4, system_data[:16])
            MIFAREReader.MFRC522_Write(12 + write_position * 4 + 1, system_data[16:])
            MIFAREReader.MFRC522_Write(12 + write_position * 4 + 2, start_time_data)
            # write flag reflesh
            while 1:
                block8_data = [block8_data[9]] + block8_data[:9] + block8_data[10:]
                if block9_data[block8_data.index(1)] != 1:
                    break
            block9_data[write_position] = 1
            MIFAREReader.MFRC522_Auth(uid, 8, access_key)
            MIFAREReader.MFRC522_Write(8, block8_data)
            MIFAREReader.MFRC522_Write(9, block9_data)
            return block1_data, block2_data
        return borrow_locker_rfid

    GPIO.cleanup()
    result = borrow_locker_rfid()
    if result:
        block1_data, block2_data = result
        student_info_data = block1_data + block2_data
        student_name = ''.join([chr(x) for x in student_info_data[6:] if x])
        student_id = sum([student_info_data[:4][i] * (256 ** (-i - 1)) for i in range(-4, 0)])
        system_status_data[user_selection]['availability'] = 'using'
        system_status_data[user_selection]['student_name'] = student_name
        system_status_data[user_selection]['student_id'] = str(student_id)
        system_status_data[user_selection]['start_time'] = start_time
        system_status_data[user_selection]['usage_count'] += 1
        system_status_data_json = json.dumps(system_status_data, sort_keys=True, indent=4, separators=(',', ': '))
        system_status_file = os.path.join(os.getcwd(), 'SystemStatus.json')
        with open(system_status_file, 'w', encoding='utf-8-sig') as f:
            f.write(system_status_data_json)
        return system_status_data


def return_locker(system_status_data, user_selection):
    MIFAREReader = MFRC522libExtension.MFRC522libExtension()
    if user_selection == 'return':
        borrow_time_list = list(system_status_data.items())
        borrow_time_list.sort(key=lambda x:x[1]['start_time'])
        borrow_dict = {y: [x[0] for x in borrow_time_list if x[1]['id'] == y] for y in {system_status_data[x]['id'] for x in system_status_data}}
        locker_borrower_id = ''
    else:
        locker_borrower_id = system_status_data[user_selection]['student_id']
        borrow_dict = ''
    end_time = int(time.mktime(time.localtime()))
    end_time_data = '0' * (16 - len(hex(end_time)[2:])) + hex(end_time)[2:]
    end_time_data = [int(end_time_data[2 * x:2 * x + 2], 16) for x in range(8)]

    def return_locker_rfid():
        @MIFAREReader.standard_frame(user_selection=user_selection, end_time_data=end_time_data, borrow_dict=borrow_dict, locker_borrower_id=locker_borrower_id, system_status_data=system_status_data)
        def retuen_locker_rfid(access_key, uid, borrow_dict, locker_borrower_id, end_time_data, system_status_data, user_selection):
            student_id = sum([access_key[:4][i] * (256 ** (-i - 1)) for i in range(-4, 0)])
            if str(student_id) == locker_borrower_id or str(student_id) in borrow_dict:
                pass
            else:
                raise MIFAREReader.UnmatchError
            if borrow_dict:
                user_selection = borrow_dict['student_id'][0]
            locker_start_time = int(system_status_data[user_selection]['start_time'])
            MIFAREReader.MFRC522_Auth(uid, 9, access_key)
            block9_data = MIFAREReader.MFRC522_Read(9)
            for x in range(11):
                if x == 10:
                    raise MIFAREReader.UnexpectedError
                if block9_data[x] == 1:
                    MIFAREReader.MFRC522_Auth(uid, 4 * x + 14, access_key)
                    start_time_data = MIFAREReader.MFRC522_Read(4 * x + 14)
                    start_time = sum([start_time_data[:8][y] * (256 ** (-y - 1)) for y in range(-8, 0)])
                    if locker_start_time == start_time:
                        break
            MIFAREReader.MFRC522_Write(4 * x + 14, start_time_data[:8] + end_time_data)
            block9_data[x] = 0
            MIFAREReader.MFRC522_Auth(uid, 9, access_key)
            MIFAREReader.MFRC522_Write(9, block9_data)
    
    return_locker_rfid()
    system_status_data[user_selection]['availability'] = 'available'
    system_status_data[user_selection]['student_name'] = ''
    system_status_data[user_selection]['student_id'] = ''
    system_status_data[user_selection]['start_time'] = ''
    system_status_data_json = json.dumps(system_status_data, sort_keys=True, indent=4, separators=(',', ': '))
    system_status_file = os.path.join(os.getcwd(), 'SystemStatus.json')
    with open(system_status_file, 'w', encoding='utf-8-sig') as f:
        f.write(system_status_data_json)
    return system_status_data


def main():
    system_configuration_data = system_configuration()
    system_status_data = system_status(system_configuration_data)
    while 1:
        system_available, system_using, system_unavailable = get_system_status(system_status_data)
        print(system_available, system_using, system_unavailable)
        user_selection = input('Please select the locker:\n')
        if user_selection in system_available or user_selection == 'borrow':
            system_status_data = borrow_locker(system_configuration_data, system_status_data, system_available, user_selection)
        elif user_selection in system_using or user_selection == 'return':
            system_status_data = return_locker(system_status_data, user_selection)


if __name__ == "__main__":
    main()
