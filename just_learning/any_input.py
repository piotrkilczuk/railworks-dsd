import functools
import pprint
import time

import pywinusb.hid.core as hid


PRODUCTS = {
    'INFINITY': {
        'IN-USB-2': {'vendor_id': 0x05f3, 'product_id': 0x00ff},
    },
    'LOGITECH': {
        'G13': {'vendor_id': 0x046d, 'product_id': 0xc21c},
        'G25': {'vendor_id': 0x046d, 'product_id': 0xc299},
    }
}


devices = hid.HidDeviceFilter(**PRODUCTS['INFINITY']['IN-USB-2']).get_devices()
assert len(devices) == 1, 'Cannot continue found {} devices'.format(len(devices))


CURRENT_VALUE = False


# def dummy_handler(new_value, evt_type):
#     global CURRENT_VALUE
#
#     bit_sum = sum(new_value[2:6])
#     CURRENT_VALUE = bit_sum != 128


def dummy_handler_g25(data, evt_type):
    global CURRENT_VALUE
    CURRENT_VALUE = data < 255


def dummy_handler_infinity(rawdata):
    global CURRENT_VALUE
    CURRENT_VALUE = rawdata[1] == 2



device = devices[0]
device.open()

# infinity in-usb-2
device.set_raw_data_handler(dummy_handler_infinity)

# g25
# device.add_event_handler(hid.get_full_usage_id(0x1, 0x32), dummy_handler_g25, hid.HID_EVT_CHANGED)
# device.add_event_handler(hid.get_full_usage_id(0x1, 0x35), dummy_handler_g25, hid.HID_EVT_CHANGED)
# device.add_event_handler(hid.get_full_usage_id(0x1, 0x36), dummy_handler_g25, hid.HID_EVT_CHANGED)

try:
    while device.is_plugged():
        print CURRENT_VALUE
        time.sleep(0.25)
except KeyboardInterrupt:
    device.close()
finally:
    device.close()
