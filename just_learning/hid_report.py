#!/usr/bin/env python

"""
Show all HID devices information
"""
import pywinusb.hid as hid

if __name__ == '__main__':
    hid.core.show_hids(output=open('hid_report.txt', 'w'))
