import mysql.connector


db = mysql.connector.connect(host='localhost', user='recordadmin', passwd='fyp123', database='historyrecordsystem')
cursor = db.cursor()


def Update(uid, student_name, student_id):
    uid = [str(i) for i in uid]
    uid = ''.join(uid)
    sql_insert = 'INSERT INTO USER (STUDENT_ID, STUDENT_NAME, UID) VALUES (%s,%s,%s)'
    cursor.execute(sql_insert, (student_id, student_name, uid))
    db.commit()

def Search(student_id):
    cursor.execute(f'SELECT * FROM USER WHERE STUDENT_ID = {student_id}')
    cursor.fetchone()
    if cursor.rowcount >= 1:
        return 1
    else:
        return 0
