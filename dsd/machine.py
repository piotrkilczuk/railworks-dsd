import transitions


__all__ = (
    'Inactive',

    'DSD',
)


Inactive = transitions.State(name='inactive')
"""
Reverser is in Neutral or Off. This is also the initial state.
"""


class DSD(transitions.Machine):

    def __init__(self):
        super(DSD, self).__init__(states=[Inactive], initial='inactive')
