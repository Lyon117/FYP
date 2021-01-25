import RPi.GPIO as GPIO
import spi


class MFRC522lib:
    class AuthenticationError(BaseException):
        pass

    class CommunicationError(BaseException):
        pass

    class IntegrityError(BaseException):
        pass

    NRSTPD = 22

    MAX_LEN = 16

    PCD_IDLE = 0x00
    PCD_CALCCRC = 0x03
    PCD_TRANSMIT = 0x04
    PCD_RECEIVE = 0x08
    PCD_TRANSCEIVE = 0x0C
    PCD_AUTHENT = 0x0E
    PCD_RESETPHASE = 0x0F

    PICC_REQIDL = 0x26
    PICC_READ = 0x30
    PICC_HALT = 0x50
    PICC_REQALL = 0x52
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_ANTICOLL = 0x93
    PICC_SElECTTAG = 0x93
    PICC_WRITE = 0xA0
    PICC_TRANSFER = 0xB0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE = 0xC2

    OK = 0
    NOTAGERR = 1
    ERR = 2

    Reserved00 = 0x00
    CommandReg = 0x01
    CommIEnReg = 0x02
    DivlEnReg = 0x03
    CommIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    WaterLevelReg = 0x0B
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    Reserved01 = 0x0F

    Reserved10 = 0x10
    ModeReg = 0x11
    TxModeReg = 0x12
    RxModeReg = 0x13
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TxSelReg = 0x16
    RxSelReg = 0x17
    RxThresholdReg = 0x18
    DemodReg = 0x19
    Reserved11 = 0x1A
    Reserved12 = 0x1B
    MifareReg = 0x1C
    Reserved13 = 0x1D
    Reserved14 = 0x1E
    SerialSpeedReg = 0x1F

    Reserved20 = 0x20
    CRCResultRegM = 0x21
    CRCResultRegL = 0x22
    Reserved21 = 0x23
    ModWidthReg = 0x24
    Reserved22 = 0x25
    RFCfgReg = 0x26
    GsNReg = 0x27
    CWGsPReg = 0x28
    ModGsPReg = 0x29
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F

    Reserved30 = 0x30
    TestSel1Reg = 0x31
    TestSel2Reg = 0x32
    TestPinEnReg = 0x33
    TestPinValueReg = 0x34
    TestBusReg = 0x35
    AutoTestReg = 0x36
    VersionReg = 0x37
    AnalogTestReg = 0x38
    TestDAC1Reg = 0x39
    TestDAC2Reg = 0x3A
    TestADCReg = 0x3B
    Reserved31 = 0x3C
    Reserved32 = 0x3D
    Reserved33 = 0x3E
    Reserved34 = 0x3F

    def __init__(self, dev='/dev/spidev0.0', spd=1000000):
        self.dev_dictionary = spi.openSPI(device=dev, speed=spd)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.NRSTPD, GPIO.OUT)
        GPIO.output(self.NRSTPD, 1)
        self.MFRC522_Reset()
        self.Write_MFRC522(self.TModeReg, 0x8D)
        self.Write_MFRC522(self.TPrescalerReg, 0x3E)
        self.Write_MFRC522(self.TReloadRegL, 30)
        self.Write_MFRC522(self.TReloadRegH, 0)
        self.Write_MFRC522(self.TxAutoReg, 0x40)
        self.Write_MFRC522(self.ModeReg, 0x3D)
        self.Write_MFRC522(self.RFCfgReg, 0x70)
        self.AntennaOn()

    def MFRC522_Reset(self):
        self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

    def Write_MFRC522(self, addr, val):
        spi.transfer(self.dev_dictionary, ((addr << 1) & 0x7E, val))

    def Read_MFRC522(self, addr):
        val = spi.transfer(self.dev_dictionary, (((addr << 1) & 0x7E) | 0x80, 0))
        return val[1]

    def SetBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp | mask)

    def ClearBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp & (~mask))

    def AntennaOn(self):
        temp = self.Read_MFRC522(self.TxControlReg)
        if ~(temp & 0x03):
            self.SetBitMask(self.TxControlReg, 0x03)

    def AntennaOff(self):
        self.ClearBitMask(self.TxControlReg, 0x03)

    def MFRC522_ToCard(self, command, send_data):
        back_data = []
        back_len = 0
        status = self.ERR
        if command == self.PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        if command == self.PCD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30
        self.Write_MFRC522(self.CommIEnReg, irq_en | 0x80)
        self.ClearBitMask(self.CommIrqReg, 0x80)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
        self.Write_MFRC522(self.CommandReg, self.PCD_IDLE)
        for i in range(len(send_data)):
            self.Write_MFRC522(self.FIFODataReg, send_data[i])
        self.Write_MFRC522(self.CommandReg, command)
        if command == self.PCD_TRANSCEIVE:
            self.SetBitMask(self.BitFramingReg, 0x80)
        i = 2000
        while True:
            n = self.Read_MFRC522(self.CommIrqReg)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break
        self.ClearBitMask(self.BitFramingReg, 0x80)
        if i != 0:
            if (self.Read_MFRC522(self.ErrorReg) & 0x1B) == 0x00:
                status = self.OK
                if n & irq_en & 0x01:
                    status = self.NOTAGERR
                if command == self.PCD_TRANSCEIVE:
                    n = self.Read_MFRC522(self.FIFOLevelReg)
                    last_bits = self.Read_MFRC522(self.ControlReg) & 0x07
                    back_len = (n - 1) * 8 + last_bits if last_bits != 0 else n * 8
                    n = 1 if n == 0 else self.MAX_LEN if n > self.MAX_LEN else n
                    for i in range(n):
                        back_data.append(self.Read_MFRC522(self.FIFODataReg))
            else:
                status = self.ERR
        return status, back_data, back_len

    def MFRC522_Request(self, req_mode=PICC_REQIDL):
        tagtype = [req_mode]
        self.Write_MFRC522(self.BitFramingReg, 0x07)
        status, back_data, back_bits = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, tagtype)
        if status == self.OK and back_bits == 0x10:
            return self.OK
        else:
            return self.ERR

    def MFRC522_Anticoll(self):
        sernum_check = 0
        sernum = [self.PICC_ANTICOLL, 0x20]
        self.Write_MFRC522(self.BitFramingReg, 0x00)
        status, back_data, back_bits = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, sernum)
        if status == self.OK and len(back_data) == 5:
            for i in range(4):
                sernum_check = sernum_check ^ back_data[i]
            i += 1
            if sernum_check != back_data[i]:
                raise self.CommunicationError('Error while anticoll')
        else:
            raise self.CommunicationError('Error while anticoll')
        return back_data

    def CalulateCRC(self, input_data):
        self.ClearBitMask(self.DivIrqReg, 0x04)
        self.SetBitMask(self.FIFOLevelReg, 0x80)
        for i in range(len(input_data)):
            self.Write_MFRC522(self.FIFODataReg, input_data[i])
        self.Write_MFRC522(self.CommandReg, self.PCD_CALCCRC)
        i = 0xFF
        while True:
            n = self.Read_MFRC522(self.DivIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break
        output_data = [self.Read_MFRC522(self.CRCResultRegL), self.Read_MFRC522(self.CRCResultRegM)]
        return output_data

    def MFRC522_SelectTag(self, sernum):
        buff = [self.PICC_SElECTTAG, 0x70] + sernum
        buff += self.CalulateCRC(buff)
        status, back_data, back_len = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buff)
        if status != self.OK or back_len != 0x18:
            raise self.CommunicationError('Error while select tag')

    def MFRC522_Auth(self, sernum, block_addr, sector_key, authmode=PICC_AUTHENT1A):
        buff = [authmode, block_addr] + sector_key + sernum[:4]
        status, back_data, back_len = self.MFRC522_ToCard(self.PCD_AUTHENT, buff)
        if status != self.OK or (self.Read_MFRC522(self.Status2Reg) & 0x08) == 0:
            raise self.AuthenticationError()

    def MFRC522_StopCrypto1(self):
        self.ClearBitMask(self.Status2Reg, 0x08)

    def MFRC522_Read(self, block_addr):
        recv_data = [self.PICC_READ, block_addr]
        recv_data += self.CalulateCRC(recv_data)
        status, back_data, back_len = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, recv_data)
        if status != self.OK:
            raise self.CommunicationError('Error while reading')
        if len(back_data) != 16:
            raise self.IntegrityError()
        return back_data

    def MFRC522_Write(self, block_addr, write_data):
        buff = [self.PICC_WRITE, block_addr]
        buff += self.CalulateCRC(buff)
        status, back_data, back_len = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, buff)
        if status == self.OK and back_len == 4 and (back_data[0] & 0x0F) == 0x0A:
            write_data += self.CalulateCRC(write_data)
            status, back_data, back_len = self.MFRC522_ToCard(self.PCD_TRANSCEIVE, write_data)
            if not status == self.OK or not back_len == 4 or not (back_data[0] & 0x0F) == 0x0A:
                raise self.CommunicationError('Error while writing')
        else:
            raise self.CommunicationError('Error while writing')
