import MFRC522libExtension
import RPi.GPIO as GPIO
import time


class CardInfo:
    def __init__(self, block1_data, block2_data, block4_data, history_data):
        self.student_id = self.student_id_decode(block1_data)
        self.student_name = self.student_name_decode(block1_data, block2_data)
        self.balance = self.balance_decode(block4_data)
        self.history_data = self.history_record_decode(history_data)

    def student_id_decode(self, block1_data):
        return sum([block1_data[:4][i] * (256 ** (-i - 1)) for i in range(-4, 0)])

    def student_name_decode(self, block1_data, block2_data):
        return ''.join([chr(x) for x in block1_data[6:] + block2_data if x])

    def balance_decode(self, block4_data):
        balance = sum([block4_data[1:][i] * (256 ** (-i - 1)) for i in range(-15, 0)])
        return balance if block4_data[0] == 0 else -balance

    def history_record_decode(self, history_data):
        history_data_dict = {}
        for x in range(len(history_data)):
            locker_data = history_data[x][0] + history_data[x][1]
            locker_name = ''.join([chr(x) for x in locker_data[:30] if x])
            locker_no = sum([locker_data[i] * (256 ** (-i - 1)) for i in range(-2, 0)])
            start_time = sum([history_data[x][2][:8][i] * (256 ** (-i - 1)) for i in range(-8, 0)])
            end_time = sum([history_data[x][2][8:][i] * (256 ** (-i - 1)) for i in range(-8, 0)])
            history_data_dict[str(start_time)] = {'locker_name': locker_name, 'locker_no': locker_no, 'end_time': end_time}
        return history_data_dict


def main():
    def card_info():
        @MIFAREReader.standard_frame()
        def card_info(access_key, uid):
            history_data = []
            MIFAREReader.MFRC522_Auth(uid, 1, MIFAREReader.DEFAULT_KEY)
            block1_data = MIFAREReader.MFRC522_Read(1)
            block2_data = MIFAREReader.MFRC522_Read(2)
            MIFAREReader.MFRC522_Auth(uid, 4, access_key)
            block4_data = MIFAREReader.MFRC522_Read(4)
            for x in range(3, 13):
                MIFAREReader.MFRC522_Auth(uid, 4 * x, access_key)
                sector_data = [MIFAREReader.MFRC522_Read(4 * x + y) for y in range(3)]
                if sector_data == [[0] * 16] * 3:
                    break
                else:
                    history_data.append(sector_data)
            return block1_data, block2_data, block4_data, history_data
        return card_info

    MIFAREReader = MFRC522libExtension.MFRC522libExtension()
    block1_data, block2_data, block4_data, history_data = card_info()
    card_info = CardInfo(block1_data, block2_data, block4_data, history_data)
    print(f'Student Name:{card_info.student_name}\nStudent ID:{card_info.student_id}\nBalance:{card_info.balance}')
    if len(card_info.history_data) == 0:
        print('No history data found')
    else:
        print('History data:')
        history_data_key = list(card_info.history_data)
        history_data_key.sort()
        for x in history_data_key:
            print(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(x)))} {card_info.history_data[x]["locker_name"]} '
                  f'{card_info.history_data[x]["locker_no"]} {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(card_info.history_data[x]["end_time"])) if card_info.history_data[x]["end_time"] else "Not return yet"}')
    GPIO.cleanup()


if __name__ == '__main__':
    main()
