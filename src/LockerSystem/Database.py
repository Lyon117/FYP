from functools import wraps
import mysql.connector


class DatabaseUser:
    def __init__(self, user_name, user_password):
        self.host = 'localhost'
        self.user = user_name
        self.password = user_password


admin = DatabaseUser('admin', 'adminpwflockersystem2021')


def __AdminLogin(database_name):
    def AdminLogin(database_function):
        @wraps(database_function)
        def AdminLoginFunction(*arg, **kwarg):
            database = mysql.connector.connect(host=admin.host, user=admin.user, passwd=admin.password, database=database_name)
            admin_cursor = database.cursor()
            result = database_function(admin_cursor, database, *arg, **kwarg)
            admin_cursor.close()
            return result
        return AdminLoginFunction
    return AdminLogin


def Initialization():
    database = mysql.connector.connect(host=admin.host, user=admin.user, passwd=admin.password)
    admin_cursor = database.cursor()
    admin_cursor.execute('SHOW DATABASES')
    if not 'LOCKER_SYSTEM' in [x[0] for x in list(admin_cursor)]:
        admin_cursor.execute('CREATE DATABASE LOCKER_SYSTEM')
    admin_cursor.close()
    CheckTableExist()


@__AdminLogin('LOCKER_SYSTEM')
def CheckTableExist(admin_cursor, database):
    admin_cursor.execute('SHOW TABLES')
    if not 'USER_REGISTRATION' in [x[0] for x in list(admin_cursor)]:
        admin_cursor.execute('create table USER_REGISTRATION(ID INT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE, STUDENT_ID VARCHAR(8) NOT NULL UNIQUE, STUDENT_NAME VARCHAR(255) NOT NULL, UID VARCHAR(15) NOT NULL, REGISTRATION_TIME VARCHAR(255) NOT NULL, PRIMARY KEY (STUDENT_ID))')
    admin_cursor.execute('SHOW TABLES')
    if not 'HISTORY_RECORD' in [x[0] for x in list(admin_cursor)]:
        admin_cursor.execute('create table HISTORY_RECORD(ID INT UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE, STUDENT_ID VARCHAR(8) NOT NULL, LOCKER_ID VARCHAR(8) NOT NULL, BORROW_TIME VARCHAR(255) NOT NULL, RETURN_TIME VARCHAR(255), PRIMARY KEY (ID))')


@__AdminLogin('LOCKER_SYSTEM')
def UserRegistrationUpdate(cursor, database, uid, student_name, student_id, registration_time):
    uid = [str(i) for i in uid]
    uid = ''.join(uid)
    cursor.execute('INSERT INTO USER_REGISTRATION (STUDENT_ID, STUDENT_NAME, UID, REGISTRATION_TIME) VALUES (%s, %s, %s, %s)', (student_id, student_name, uid, registration_time))
    database.commit()


@__AdminLogin('LOCKER_SYSTEM')
def UserRegistrationSearch(cursor, database, student_id):
    cursor.execute(f'SELECT * FROM USER_REGISTRATION WHERE STUDENT_ID={student_id}')
    cursor.fetchall()
    if cursor.rowcount >= 1:
        return 1
    else:
        return 0


@__AdminLogin('LOCKER_SYSTEM')
def UserRegistrationDelectRecord(cursor, database, student_id):
    cursor.execute(f'DELETE FROM USER_REGISTRATION WHERE STUDENT_ID={student_id}')
    database.commit()


@__AdminLogin('LOCKER_SYSTEM')
def HistoryRecordUpdateBorrow(cursor, database, student_id, locker_id, borrow_time):
    cursor.execute('INSERT INTO HISTORY_RECORD (STUDENT_ID, LOCKER_ID, BORROW_TIME) VALUES (%s, %s, %s)', (str(student_id), str(locker_id), borrow_time))
    database.commit()


@__AdminLogin('LOCKER_SYSTEM')
def HistoryRecordUpdateReturn(cursor, database, student_id, locker_id, borrow_time, return_time):
    cursor.execute(f"UPDATE HISTORY_RECORD SET RETURN_TIME='{return_time}' WHERE STUDENT_ID='{str(student_id)}' AND LOCKER_ID='{str(locker_id)}' AND BORROW_TIME='{borrow_time}'")
    database.commit()
