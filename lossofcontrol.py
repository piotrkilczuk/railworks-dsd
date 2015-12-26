import time

from pywinusb.hid import core as pywinusb


READ_SECONDS = 15
READ_ITERATIONS = 10

DEVICE_REGISTRY = []


def open_device():
    device_filter = pywinusb.HidDeviceFilter(vendor_id=0x05f3, product_id=0x00ff)
    device = device_filter.get_devices()[0]
    device.open()
    DEVICE_REGISTRY.append(device)
    return device


def close_last_device():
    DEVICE_REGISTRY[-1].close()


def raw_handler(data):
    print data


for m in range(READ_ITERATIONS):
    print 'Iteration {}. Please keep pressing / releasing for {} seconds'.format(m + 1, READ_SECONDS)

    device = open_device()
    device.set_raw_data_handler(raw_handler)
    time_start = time.time()
    time_end = time_start + READ_SECONDS
    while time.time() < time_end:
        pass
    # close_last_device()

    print 'Iteration finished.'
    print 'Registry: {}'.format(DEVICE_REGISTRY)
    print
