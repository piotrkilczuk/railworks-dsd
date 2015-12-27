import datetime
import random


class BaseDSDModel(object):
    """
    Base DSD Model that holds the core operations of a DSD and resets the timer whenever an 'important' control changes.
    """

    emergency_brake_control_name = 'EmergencyBrake'
    important_controls = None

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
        if self.important_controls:
            self.raildriver_listener.subscribe(self.important_controls)
            for control_name in self.important_controls:
                event_name = 'on_{}_change'.format(control_name.lower())
                getattr(self.raildriver_listener, event_name)(self.on_important_control_change)
        self.raildriver_listener.on_reverser_change(self.reverser_changed)
        self.raildriver_listener.on_time_change(self.on_time_change)

    def emergency_brake(self):
        self.raildriver.set_controller_value(self.emergency_brake_control_name, 1.0)

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


class BuiltinDSDIsolationMixin(object):

    dsd_controller_name = None
    dsd_controller_value = 0

    def bind_listener(self):
        self.raildriver.set_controller_value(self.dsd_controller_name, self.dsd_controller_value)
        super(BuiltinDSDIsolationMixin, self).bind_listener()


class GenericDSDModel(BaseDSDModel):

    important_controls = [
        'AWSReset',
        'Bell',
        'Horn',
        'Regulator',
        'Reverser',
        'TrainBrakeControl'
    ]


class Class90DSDModel(BaseDSDModel):

    important_controls = [
        'AWSReset',
        'Bell',
        'DRA',
        'Reverser',
        'SpeedSet',
        'VirtualBrake',
        'VirtualThrottle'
    ]

    def bind_listener(self):  # @todo: use BuiltinDSDIsolationMixin at next opportunity
        self.raildriver.set_controller_value('DSDEnabled', 0)
        super(Class90DSDModel, self).bind_listener()


class Class220_221DSDModel(BuiltinDSDIsolationMixin, BaseDSDModel):

    dsd_controller_name = 'SafetyIsolation'
    dsd_controller_value = 1
    emergency_brake_control_name = 'EmergencyStop'
    important_controls = [
        'AWSReset',
        'Bell',
        'CombinedController',
        'Reverser'
    ]


class Class360DSDModel(BaseDSDModel):

    important_controls = [
        'AWSReset',
        'DRAButton',
        'Horn',
        'Reverser',
        'ThrottleAndBrake'
    ]

    def on_time_change(self, new, _):
        current_tab = self.raildriver.get_current_controller_value('ThrottleAndBrake')
        current_tab += .001 if random.randrange(0, 2) else -.001
        self.raildriver.set_controller_value('ThrottleAndBrake', current_tab)
        super(Class360DSDModel, self).on_time_change(new, _)
