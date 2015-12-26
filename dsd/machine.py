import datetime
import logging

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

    def bind_listener(self):
        available_controls = dict(self.raildriver.get_controller_list()).values()
        important_controls = ['AWSReset', 'Bell', 'Horn', 'Regulator', 'Reverser', 'TrainBrakeControl']
        subscribe_controls = filter(lambda i: i in available_controls, important_controls)
        self.raildriver_listener.subscribe(subscribe_controls)
        self.raildriver_listener.on_awsreset_change(self.on_important_control_change)
        self.raildriver_listener.on_bell_change(self.on_important_control_change)
        self.raildriver_listener.on_horn_change(self.on_important_control_change)
        self.raildriver_listener.on_regulator_change(self.on_important_control_change)
        self.raildriver_listener.on_reverser_change(self.reverser_changed)
        self.raildriver_listener.on_time_change(self.on_time_change)
        self.raildriver_listener.on_trainbrakecontrol_change(self.on_important_control_change)
        self.raildriver_listener.start()

    def emergency_brake(self):
        self.raildriver.set_controller_value('EmergencyBrake', 1.0)

    def is_reverser_in_neutral(self, *args, **kwargs):
        return -0.5 < self.raildriver.get_current_controller_value('Reverser') < 0.5

    def on_enter_needs_depress(self, *args, **kwargs):
        self.beeper.start()

        current_datetime = datetime.datetime.combine(datetime.datetime.today(), self.raildriver.get_current_time())
        self.react_by = (current_datetime + datetime.timedelta(seconds=6)).time()

    def on_enter_idle(self, *args, **kwargs):
        self.beeper.stop()

        current_datetime = datetime.datetime.combine(datetime.datetime.today(), self.raildriver.get_current_time())
        self.react_by = (current_datetime + datetime.timedelta(seconds=60)).time()

    def on_important_control_change(self, new, old):
        if old is None:
            return
        difference = abs(new - old)
        if difference > 0.1:
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

    running = False
    """
    True if instance is operational, False if DSDMachine should be reinstantiated
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

        loco_name = self.raildriver.get_loco_name()
        logging.debug('Detected new active loco {}'.format(loco_name))
        if not loco_name:
            self.close()
            return

        self.init_model()
        self.raildriver_listener.on_loconame_change(self.close)

    def check_initial_reverser_state(self):
        if not self.model.is_reverser_in_neutral():
            self.set_state(NeedsDepress)

    def close(self, *args, **kwargs):
        self.beeper.stop()
        self.raildriver_listener.stop()
        self.usb.close()
        self.running = False

    def init_model(self, *args, **kwargs):  # because we hook it into on_loco_change
        model = DSDModel(self.beeper, self.raildriver, self.raildriver_listener, self.usb)
        super(DSDMachine, self).__init__(model, states=[Inactive, NeedsDepress, Idle], initial='inactive')

        self.add_transition('device_depressed', 'needs_depress', 'idle')
        self.add_transition('device_released', 'idle', 'needs_depress', before='emergency_brake')
        self.add_transition('reverser_changed', 'inactive', 'needs_depress', unless='is_reverser_in_neutral')
        self.add_transition('reverser_changed', 'idle', 'inactive', conditions='is_reverser_in_neutral')
        self.add_transition('timeout', 'idle', 'needs_depress')
        self.add_transition('timeout', 'needs_depress', 'needs_depress', before='emergency_brake')
        self.usb.on_depress(self.model.device_depressed)
        self.usb.on_release(self.model.device_released)

        self.model.bind_listener()
        self.running = True

        self.check_initial_reverser_state()

    def set_state(self, state):
        previous_state = self.current_state
        super(DSDMachine, self).set_state(state)
        event_data = transitions.EventData(previous_state, None, self, self.model)
        self.current_state.enter(event_data)
