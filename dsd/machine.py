import logging

import raildriver
import transitions

from dsd import machine_models as models
from dsd import sound
from dsd import usb


__all__ = (
    'DSDMachine',
    'MODEL_MAPPING',

    'Inactive',
    'NeedsDepress',
    'Idle',
)


MODEL_MAPPING = {
    'Default': models.GenericDSDModel,

    'RSC.Class70Pack01': models.GenericDSDModel,
}


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


class DSDMachine(transitions.Machine):

    beeper = None
    """
    A threaded sound player
    """

    needs_restart = False
    """
    True if instance is is no more operational and should be restarted.
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

        loco_name = self.raildriver.get_loco_name()
        self.raildriver_listener.on_loconame_change(self.set_needs_restart_flag)
        self.raildriver_listener.start()
        if not loco_name:
            logging.debug('No active loco detected')
            return
        logging.debug('Detected new active loco {}'.format(loco_name))

        self.init_model(loco_name)

    def check_initial_reverser_state(self):
        if not self.model.is_reverser_in_neutral():
            self.set_state(NeedsDepress)

    def close(self, *args, **kwargs):
        self.beeper.stop()
        self.raildriver_listener.stop()
        if self.raildriver_listener.thread:  # @TODO: this might be a bug in RD listener
            self.raildriver_listener.thread.join()
        self.usb.close()

    def init_model(self, loco_name):
        model_class = MODEL_MAPPING.get('{}.{}'.format(*loco_name), MODEL_MAPPING['Default'])
        model = model_class(self.beeper, self.raildriver, self.raildriver_listener, self.usb)
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
        self.check_initial_reverser_state()

    def set_needs_restart_flag(self, _, __):
        logging.debug('Needs restart due to loco change')
        self.needs_restart = True

    def set_state(self, state):
        previous_state = self.current_state
        super(DSDMachine, self).set_state(state)
        event_data = transitions.EventData(previous_state, None, self, self.model)
        self.current_state.enter(event_data)
