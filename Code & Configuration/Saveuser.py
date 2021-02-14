import mysql.connector
from time import sleep


db = mysql.connector.connect(host='localhost', user='recordadmin', passwd='fyp123', database='historyrecordsystem')
cursor = db.cursor()


def main(uid, student_name, student_id):
    uid = [str(i) for i in uid]
    uid = ''.join(uid)
    cursor.execute(f'SELECT id FROM reg_user WHERE rfid_uid={uid}')
    cursor.fetchone()
    if cursor.rowcount >= 1:
        sleep(1)
        sql_insert = 'UPDATE reg_user SET name =%s WHERE rfid_uid=%s'
        cursor.execute(sql_insert, (student_name, id))
        sql_insert = 'UPDATE reg_user SET sid =%s WHERE rfid_uid=%s'
        cursor.execute(sql_insert, (str(student_id), id))
        sql_insert = 'UPDATE reg_user SET pw =%s WHERE rfid_uid=%s'
        cursor.execute(sql_insert, ('12345678', id))
    else:
        sql_insert = 'INSERT INTO reg_user (name, rfid_uid, sid, pw) VALUES (%s,%s,%s,%s)'
        cursor.execute(sql_insert, (student_name, uid, student_id, '12345678'))
    db.commit()
    sleep(2)
