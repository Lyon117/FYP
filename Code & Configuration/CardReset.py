import MFRC522libExtension
import RPi.GPIO as GPIO


def main():
    MIFAREReader = MFRC522libExtension.MFRC522libExtension()

    def card_reset():
        @MIFAREReader.standard_frame()
        def card_reset(access_key, uid):
            access_key = access_key if access_key else MIFAREReader.get_key(uid)
            for block in range(0, 64):
                try:
                    if block % 4 == 0:
                        key = MIFAREReader.DEFAULT_KEY if block == 0 else access_key
                        status = MIFAREReader.MFRC522_Auth(MIFAREReader.PICC_AUTHENT1A, block, key, uid)
                        if status == MIFAREReader.MI_OK:
                            pass
                    if block == 0:
                        continue
                    elif block % 4 != 3:
                        MIFAREReader.MFRC522_Write(block, [0] * 16)
                    else:
                        block_data = MIFAREReader.MFRC522_Read(block)
                        MIFAREReader.MFRC522_Write(block, MIFAREReader.DEFAULT_KEY + block_data[6:])
                except MIFAREReader.AuthenticationError:
                    continue

    card_reset()
    GPIO.cleanup()


if __name__ == '__main__':
    main()
