#!/usr/bin/env python

import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import mysql.connector
import Adafruit_CharLCD as LCD

db = mysql.connector.connect(
  host='localhost',
  user='recordadmin',
  passwd='fyp123',
  database='historyrecordsystem'
)

cursor=db.cursor()
reader=SimpleMFRC522()

try:
  while True:
    print('Please place your Card to register.')  
    id,text = reader.read()
    cursor.execute('SELECT id FROM reg_user WHERE rfid_uid='+str(id))
    cursor.fetchone()

    if cursor.rowcount >= 1:
      overwrite = input('You waant to overwrite current data? (Y/N)')
      if overwrite[0] == 'Y' or overwrite[0] == 'y':
        time.sleep(1)
        sql_insert = 'UPDATE reg_user SET name =%s WHERE rfid_uid=%s'
        new_name = input('Please enter your Name: ')
        cursor.execute(sql_insert, (new_name, id))
        sql_insert = 'UPDATE reg_user SET sid =%s WHERE rfid_uid=%s'
        new_sid = input('Please enter your Student ID: ')
        cursor.execute(sql_insert, (new_sid, id))
        sql_insert = 'UPDATE reg_user SET pw =%s WHERE rfid_uid=%s'
        new_pw = input('Please enter your password: ')
        cursor.execute(sql_insert, (new_pw, id))
      else:
        continue;
    else:
      sql_insert = 'INSERT INTO reg_user (name, rfid_uid, sid, pw) VALUES (%s,%s,%s,%s)'
      new_name = input('Please enter your Name: ')
      new_sid = input('Please enter your Student ID: ')
      new_pw = input('Please enter your password: ')
      cursor.execute(sql_insert, (new_name, id, new_sid, new_pw))

    db.commit()
    print('User '+new_name + " saved!")
    time.sleep(2)

finally:
  GPIO.cleanup()
