import MFRC522libExtension
import RPi.GPIO as GPIO


def main():
    MIFAREReader = MFRC522libExtension.MFRC522libExtension()

    def card_dump():
        @MIFAREReader.standard_frame()
        def card_dump(access_key, uid):
            card_data = []
            for sector in range(16):
                key = MIFAREReader.DEFAULT_KEY if sector == 0 else access_key
                status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, 4 * sector, key, uid)
                if status == MIFAREReader.MI_OK:
                    card_data.append([MIFAREReader.MFRC522_Read(4 * sector + block) for block in range(4)])
            return card_data
        return card_dump

    card_data = card_dump()
    for sector_data in card_data:
        print(sector_data)
    GPIO.cleanup()


if __name__ == '__main__':
    main()
