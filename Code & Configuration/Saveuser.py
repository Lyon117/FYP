import mysql.connector
from time import sleep


db = mysql.connector.connect(host='localhost', user='recordadmin', passwd='fyp123', database='historyrecordsystem')
cursor = db.cursor()


def main(uid, student_name, student_id):
    uid = [str(i) for i in uid]
    uid = ''.join(uid)
    sql_insert = 'INSERT INTO reg_user (STUDENT_ID, STUDENT_NAME, UID) VALUES (%s,%s,%s)'
    cursor.execute(sql_insert, (student_id, student_name, uid))
    db.commit()
    sleep(2)
