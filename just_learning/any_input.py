import time

import pywinusb.hid.core as hid


PRODUCTS = {
    'LOGITECH': {
        'G13': {'vendor_id': 0x046d, 'product_id': 0xc21c},
        'G25': {'vendor_id': 0x046d, 'product_id': 0xc299},
    }
}


devices = hid.HidDeviceFilter(**PRODUCTS['LOGITECH']['G25']).get_devices()
assert len(devices) == 1, 'Cannot continue found {} devices'.format(len(devices))


CURRENT_VALUE = False


# def dummy_handler(new_value, evt_type):
#     global CURRENT_VALUE
#
#     bit_sum = sum(new_value[2:6])
#     CURRENT_VALUE = bit_sum != 128


def dummy_handler(data, evt_type):
    global CURRENT_VALUE
    CURRENT_VALUE = data < 255


g25 = devices[0]
g25.open()
# g13 key presses don't report as buttons, so we need to handle them in a different way...
g25.add_event_handler(hid.get_full_usage_id(0x1, 0x32), dummy_handler, hid.HID_EVT_CHANGED)
g25.add_event_handler(hid.get_full_usage_id(0x1, 0x35), dummy_handler, hid.HID_EVT_CHANGED)
g25.add_event_handler(hid.get_full_usage_id(0x1, 0x36), dummy_handler, hid.HID_EVT_CHANGED)

try:
    while g25.is_plugged():
        print CURRENT_VALUE
        time.sleep(0.25)
except KeyboardInterrupt:
    g25.close()
finally:
    g25.close()
