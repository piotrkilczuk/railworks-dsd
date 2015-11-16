from dsd.machine import *
from dsd.sound import *
from dsd.usb import *


def __main__():
    machine = DSDMachine()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        machine.close()
