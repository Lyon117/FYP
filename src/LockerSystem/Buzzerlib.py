import RPi.GPIO as GPIO
import time


class Buzzerlib():
    '''A library for a buzzer'''
    BUZZER_PIN = 12

    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT)

    def notification(self):
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def finish(self):
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def close(self):
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        GPIO.cleanup()
