import MFRC522libExtension
import RPi.GPIO as GPIO
import sys


def main():
    MIFAREReader = MFRC522libExtension.MFRC522libExtension()
    student_id = input('Please input your student ID:\n')
    while 1:
        if student_id.isdigit() and len(student_id) == 8:
            break
        else:
            student_id = input('Student ID is in incorrect format. Please input your student ID again:\n')
    student_id_data = [(int(student_id) % (256 ** -x)) // (256 ** (-x - 1)) for x in range(-4, 0)]
    student_id_checksum1 = MIFAREReader.checksum_generator(student_id_data)
    student_id_data += [student_id_checksum1]
    student_id_checksum2 = MIFAREReader.checksum_generator(student_id_data)
    student_id_data += [student_id_checksum2]
    student_name = input('Please input your name:\n')
    while 1:
        if student_name.isascii() and student_name.replace(' ', '').isalpha():
            break
        else:
            student_name = input('Student name is in incorrect format. Please input you student name again:\n')
    student_name_data = [ord(x) for x in student_name]
    if len(student_name_data) <= 26:
        student_name_data += [0] * (26 - len(student_name_data))
    else:
        print('The student name is too long')
        input('Press ENTER to exit')
        sys.exit(0)

    def card_initialization():
        @MIFAREReader.standard_frame(initialize=1, access_key=student_id_data, student_data=student_id_data + student_name_data)
        def card_initialization(access_key, student_data, uid):
            status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 3, MIFAREReader.DEFAULT_KEY, uid)
            if status == MIFAREReader.MI_OK:
                MIFAREReader.MFRC522_Write(1, student_data[:16])
                MIFAREReader.MFRC522_Write(2, student_data[16:])
                for index in range(7, 64, 4):
                    try:
                        status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, index, MIFAREReader.DEFAULT_KEY, uid)
                        if status == MIFAREReader.MI_OK:
                            if index == 7:
                                MIFAREReader.MFRC522_Write(4, [1] + [0] * 15)
                            elif index == 11:
                                MIFAREReader.MFRC522_Write(8, [1] + [0] * 15)
                                MIFAREReader.MFRC522_Write(9, [0] * 16)
                            block_data = MIFAREReader.MFRC522_Read(index)
                            MIFAREReader.MFRC522_Write(index, access_key + block_data[6:])
                    except MIFAREReader.AuthenticationError:
                        continue

    card_initialization()
    GPIO.cleanup()


if __name__ == '__main__':
    main()
