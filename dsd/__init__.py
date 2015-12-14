import logging

from dsd.machine import *
from dsd.sound import *
from dsd.usb import *


def __main__():
    logging.basicConfig(
        filename='dsd.log',
        level=logging.DEBUG,
        format='%(asctime)s %(module)s:%(lineno)d %(message)s'
    )
    machine = DSDMachine()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        machine.close()
    except Exception:
        machine.close()
        raise
