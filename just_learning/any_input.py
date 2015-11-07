import time

import pywinusb.hid.core as hid


PRODUCTS = {
    'LOGITECH': {
        'G13': {'vendor_id': 0x046d, 'product_id': 0xc21c}
    }
}


devices = hid.HidDeviceFilter(**PRODUCTS['LOGITECH']['G13']).get_devices()
assert len(devices) == 1, 'Cannot continue found {} devices'.format(len(devices))


CURRENT_VALUE = False


def dummy_handler(new_value, evt_type):
    global CURRENT_VALUE

    bit_sum = sum(new_value[2:6])
    CURRENT_VALUE = bit_sum != 128


g13 = devices[0]
usage_id = hid.get_full_usage_id(0xff00, 0x1)  # ???
g13.open()
# g13 key presses don't report as buttons, so we need to handle them in a different way...
g13.add_event_handler(usage_id, dummy_handler, hid.HID_EVT_CHANGED)

try:
    while g13.is_plugged():
        print CURRENT_VALUE
        time.sleep(0.25)
except KeyboardInterrupt:
    g13.close()
finally:
    g13.close()
