import MFRC522libExtension
import RPi.GPIO as GPIO
import sys


def main():
    def change_balance():
        @MIFAREReader.standard_frame(value=value)
        def change_balance(access_key, uid, value):
            MIFAREReader.MFRC522_Auth(uid, 4, access_key)
            balance_data = MIFAREReader.MFRC522_Read(4)
            balance_sign, balance_value = balance_data[0], balance_data[1:]
            balance = sum([balance_value[i] * (256 ** (-i - 1)) for i in range(-15, 0)])
            balance = -balance if balance_sign else balance
            balance += value
            if balance < 0:
                input('Balance too small')
                sys.exit(0)
            elif balance > 256 ** 15:
                input('Balance over limit')
                sys.exit(0)
            balance_data = [0] + [(balance % (256 ** -i)) // (256 ** (-i - 1)) for i in range(-15, 0)]
            MIFAREReader.MFRC522_Write(4, balance_data)

    MIFAREReader = MFRC522libExtension.MFRC522libExtension()
    value = input('Please input the add value:\n')
    while 1:
        if value.isdigit():
            value = int(value)
            break
        value = input('Please input the add value again because of the incorrect format:\n')
    change_balance()
    GPIO.cleanup()


if __name__ == '__main__':
    main()
