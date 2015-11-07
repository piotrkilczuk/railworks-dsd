#!/usr/bin/env python

from pywinusb.hid import core as hid


for device in hid.find_all_hid_devices():
    print device
