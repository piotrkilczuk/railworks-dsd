import raildriver
import transitions

from dsd import sound


__all__ = (
    'Inactive',
    'NeedsDepress',

    'DSDMachine',
    'DSDModel',
)


Inactive = transitions.State(name='inactive')
"""
Reverser is in Neutral or Off. This is also the initial state.
"""

NeedsDepress = transitions.State(name='needs_depress')
"""
Driver should depress the DSD pedal in 3 seconds.
"""


class DSDModel(object):

    beeper = None
    """
    A threaded sound player
    """

    raildriver = None
    """
    raildriver.RailDriver instance used to exchange control data with Train Simulator
    """

    def __init__(self):
        self.beeper = sound.Beeper()
        self.raildriver = raildriver.RailDriver()

    def on_enter_needs_depress(self):
        self.beeper.start()


class DSDMachine(transitions.Machine):
    
    def __init__(self):
        super(DSDMachine, self).__init__(DSDModel(), states=[Inactive, NeedsDepress], initial='inactive')
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
