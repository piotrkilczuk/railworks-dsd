import logging

from dsd.machine import *
from dsd.sound import *
from dsd.usb import *


def __main__():
    logging.basicConfig(
        filename='dsd.log',
        level=logging.DEBUG,
    )
    machine = DSDMachine()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        machine.close()
