import datetime

import raildriver
import transitions

from dsd import sound
from dsd import usb


__all__ = (
    'Inactive',
    'NeedsDepress',
    'Idle',

    'DSDMachine',
    'DSDModel',
)


Inactive = transitions.State(name='inactive', ignore_invalid_triggers=True)
"""
Reverser is in Neutral or Off. This is also the initial state.
"""

NeedsDepress = transitions.State(name='needs_depress', ignore_invalid_triggers=True)
"""
Driver should depress the DSD pedal in 3 seconds.
"""

Idle = transitions.State(name='idle', ignore_invalid_triggers=True)
"""
Driver should keep the DSD pedal depressed for 60 seconds when will need to re-depress.
Release will trigger emergency braking.
Time will be reset when one of main controls is moved.
"""


class DSDModel(object):

    beeper = None
    raildriver = None
    raildriver_listener = None
    react_by = None
    usb = None

    def __init__(self, beeper, raildriver, raildriver_listener, usb):
        self.beeper = beeper
        self.raildriver = raildriver
        self.raildriver_listener = raildriver_listener
        self.usb = usb

        self.raildriver_listener.subscribe(['AWSReset', 'Bell', 'Horn', 'Regulator', 'TrainBrakeControl'])
        self.raildriver_listener.on_awsreset_change(self.on_important_control_change)
        self.raildriver_listener.on_bell_change(self.on_important_control_change)
        self.raildriver_listener.on_horn_change(self.on_important_control_change)
        self.raildriver_listener.on_regulator_change(self.on_important_control_change)
        self.raildriver_listener.on_time_change(self.on_time_change)
        self.raildriver_listener.on_trainbrakecontrol_change(self.on_important_control_change)

    def emergency_brake(self):
        self.raildriver.set_controller_value('EmergencyBrake', 1.0)

    def on_enter_needs_depress(self):
        self.beeper.start()

        current_datetime = datetime.datetime.combine(datetime.datetime.today(), self.raildriver.get_current_time())
        self.react_by = (current_datetime + datetime.timedelta(seconds=6)).time()

    def on_enter_idle(self):
        self.beeper.stop()

        current_datetime = datetime.datetime.combine(datetime.datetime.today(), self.raildriver.get_current_time())
        self.react_by = (current_datetime + datetime.timedelta(seconds=60)).time()

    def on_important_control_change(self, new, old):
        percentage_difference = new / old
        if percentage_difference < 0.9 or percentage_difference > 1.1:
            current_datetime = datetime.datetime.combine(datetime.datetime.today(), self.raildriver.get_current_time())
            self.react_by = (current_datetime + datetime.timedelta(seconds=60)).time()

    def on_time_change(self, new, _):
        if self.react_by and new >= self.react_by:
            self.timeout()


class DSDMachine(transitions.Machine):

    beeper = None
    """
    A threaded sound player
    """

    raildriver = None
    """
    raildriver.RailDriver instance used to exchange control data with Train Simulator
    """

    raildriver_listener = None
    """
    raildriver.events.Listener instance used to listen for control movements
    """

    usb = None
    """
    usb.USB reader instance used to read data from a footpedal
    """

    def __init__(self):
        self.beeper = sound.Beeper()
        self.raildriver = raildriver.RailDriver()
        self.raildriver_listener = raildriver.events.Listener(self.raildriver, interval=0.1)
        self.usb = usb.USBReader(0x05f3, 0x00ff)  # @TODO: provide support also for other devices

        model = DSDModel(self.beeper, self.raildriver, self.raildriver_listener, self.usb)
        super(DSDMachine, self).__init__(model, states=[Inactive, NeedsDepress, Idle], initial='inactive')

        self.add_transition('device_depressed', 'needs_depress', 'idle')
        self.add_transition('timeout', 'idle', 'needs_depress')
        self.add_transition('timeout', 'needs_depress', 'needs_depress', before='emergency_brake')
        self.usb.on_depress(self.model.device_depressed)

        self.check_initial_reverser_state()

    def check_initial_reverser_state(self):
        reverser_state = self.model.raildriver.get_current_controller_value('Reverser')
        if reverser_state > 0.1 or reverser_state < -0.1:
            self.set_state(NeedsDepress)

    def set_state(self, state):
        previous_state = self.current_state
        super(DSDMachine, self).set_state(state)
        event_data = transitions.EventData(previous_state, None, self, self.model)
        self.current_state.enter(event_data)
