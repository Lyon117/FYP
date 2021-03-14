from os import getpid, kill
from os.path import dirname, join
from subprocess import Popen
from sys import argv


# Constant
SYSTEM_PATH = join(dirname(__file__), 'System.py')


def restart_program(pid):
    kill(pid, 9)
    pid = getpid()
    subprocess = Popen(['python3', SYSTEM_PATH, f'{pid}'])
    _ = subprocess.communicate()


def power_off(pid):
    kill(pid, 9)
    subprocess = Popen(['sudo', 'poweroff'])


if __name__ == '__main__':
    pid, mode = argv[1:3]
    pid = int(pid)
    if mode == 'Restart':
        restart_program(pid)
    elif mode == 'PowerOff':
        power_off(pid)
