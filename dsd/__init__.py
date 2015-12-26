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

    try:
        machine = DSDMachine()
        while True:
            while machine.running:
                pass
            machine = DSDMachine()
    except KeyboardInterrupt:
        machine.close()
    except Exception:
        machine.close()
        raise
