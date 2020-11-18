import RPi.GPIO as GPIO
import time


class Buzzerlib():
    BUZZER_PIN = 12

    def __init__(self, switch=1):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)
        self.switch = switch

    def notification(self):
        if self.switch:
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        else:
            print('Card detected')

    def finish(self):
        if self.switch:
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        else:
            print('Process completed')

    def close(self):
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        GPIO.cleanup()
