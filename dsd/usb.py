from pywinusb.hid import core as pywinusb


__all__ = (
    'DEVICES',
    'InfinityInUSB2Device',
    'USBReader',
)


DEVICES = {
    0x05f3: {  # Infinity
        0x00ff: 'InfinityInUSB2Device',
    }
}


class AbstractDevice(object):

    device = None
    usb_reader = None

    product_id = None
    """
    Hex product_id of a HID device such as 0x00ff for In-USB-2. Override in a subclass.
    """

    vendor_id = None
    """
    Hex vendor_id of a HID device such as 0x05f3 for Infinity. Override in a subclass.
    """

    def __init__(self, usb_reader):
        self.usb_reader = usb_reader
        device_filter = pywinusb.HidDeviceFilter(product_id=self.product_id, vendor_id=self.vendor_id)
        self.device = device_filter.get_devices()[0]
        self.device.open()
        self.add_handlers()

    def add_handlers(self):
        raise NotImplementedError('Not implemented in subclass: {}'.format(type(self)))

    def close(self):
        self.device.close()


class InfinityInUSB2Device(AbstractDevice):
    """
    Infinity IN-USB-2

    http://www.martelelectronics.com/infinity-in-usb-2-universal-foot-pedal/

    Only use the middle pedal.

    Rawdata:

    Depressed: [0, 2, 0]
    Released:  [0, 0, 0]

    Other invalid.
    """

    vendor_id = 0x05f3
    product_id = 0x00ff

    def add_handlers(self):
        self.device.set_raw_data_handler(self.raw_data_handler)

    def raw_data_handler(self, rawdata):
        depressed = rawdata[1] == 2
        released = rawdata[1] == 0
        if depressed:
            self.usb_reader.execute_bindings('on_depress')
        elif released:
            self.usb_reader.execute_bindings('on_release')


class USBReader(object):

    bindings = {
        'on_depress': [],
        'on_release': [],
    }

    device = None
    """
    One of AbstractDevice descendants
    """

    def __init__(self, vendor_id, product_id):
        self.device = self.instantiate_device(vendor_id, product_id)

    def close(self):
        self.device.close()

    def execute_bindings(self, type, *args, **kwargs):
        for binding in self.bindings[type]:
            binding(*args, **kwargs)

    def instantiate_device(self, vendor_id, product_id):
        try:
            class_name = DEVICES[vendor_id][product_id]
            return globals()[class_name](self)
        except KeyError:
            raise ValueError('Device vid={} pid={} is not supported'.format(vendor_id, product_id))

    def on_depress(self, fun):
        self.bindings['on_depress'].append(fun)

    def on_release(self, fun):
        self.bindings['on_release'].append(fun)
