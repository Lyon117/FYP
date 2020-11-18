import Buzzerlib
import MFRC522lib
import time


class MFRC522libExtension(MFRC522lib.MFRC522lib):
    DEFAULT_KEY = [0xFF] * 6

    def __init__(self):
        super().__init__()

    def checksum_generator(self, data):
        return sum([data[i] * -i for i in range(-len(data), 0)]) % 251

    def checksum_auth(self, uid):
        data = self.get_key(uid)
        if self.checksum_generator(data[:4]) == data[4] and self.checksum_generator(data[:5]) == data[5]:
            return self.MI_OK
        else:
            print('Not authorised card')
            raise self.AuthenticationError

    def get_key(self, uid):
        status = self.MFRC522_Auth(self.PICC_AUTHENT1A, 1, self.DEFAULT_KEY, uid)
        if status == self.MI_OK:
            return self.MFRC522_Read(1)[:6]

    def standard_frame(self, initialize=0, buzzer=1, *args, **kwargs):
        def standard_frame(function):
            print('Plaese tap your card')
            Buzzer = Buzzerlib.Buzzerlib(buzzer)
            while 1:
                status, _ = self.MFRC522_Request(self.PICC_REQIDL)
                try:
                    if status == self.MI_OK:
                        status, uid = self.MFRC522_Anticoll()
                        self.MFRC522_SelectTag(uid)
                        if status == self.MI_OK:
                            status = self.checksum_auth(uid)
                            if status == self.MI_OK:
                                Buzzer.notification()
                                start_time = time.time()
                                kwargs['uid'] = uid
                                if not initialize:
                                    kwargs['access_key'] = self.get_key(uid)
                                result = function(**kwargs)
                                self.MFRC522_StopCrypto1()
                                print(f'The total elapsed time is {time.time() - start_time:.5f}s')
                                Buzzer.finish()
                                break
                except (self.AuthenticationError, self.CommunicationError, self.IntegrityError):
                    print('Please tap you card again')
                    self.MFRC522_StopCrypto1()
            return result
        return standard_frame
