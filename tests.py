import datetime
import time
import mock
import unittest
import winsound

import dsd


@mock.patch('winsound.PlaySound')
class BeeperTest(unittest.TestCase):

    beeper = None

    def setUp(self):
        self.beeper = dsd.Beeper()

    def tearDown(self):
        self.beeper.thread.join(timeout=0)

    def test_start_stop(self, mock_playsound):
        """
        Beeper.start and Beeper.stop should call winsound.PlaySound with correct parameters.

        Beeper.start and Beeper.stop should not be called separately or there will be issues with the beeper thread.
        """
        self.beeper.start()
        self.beeper.stop()
        self.beeper.thread.join(timeout=10)
        self.assertEqual(mock_playsound.mock_calls, [
            mock.call(mock.ANY, winsound.SND_ASYNC | winsound.SND_LOOP),
            mock.call(mock.ANY, winsound.SND_PURGE)
        ])


@mock.patch('dsd.usb.pywinusb', mock.MagicMock())
class DeviceTestCase(unittest.TestCase):

    def test_infinity_in_usb_2_depress(self):
        reader = dsd.USBReader(0x05f3, 0x00ff)
        depress_handler = mock.Mock()
        reader.on_depress(depress_handler)
        reader.device.raw_data_handler([0, 0, 0])
        reader.device.raw_data_handler([0, 1, 0])
        reader.device.raw_data_handler([0, 2, 0])
        reader.device.raw_data_handler([0, 4, 0])
        self.assertEqual(depress_handler.call_count, 1)

    def test_infinity_in_usb_2_release(self):
        reader = dsd.USBReader(0x05f3, 0x00ff)
        release_handler = mock.Mock()
        reader.on_release(release_handler)
        reader.device.raw_data_handler([0, 0, 0])
        reader.device.raw_data_handler([0, 1, 0])
        reader.device.raw_data_handler([0, 2, 0])
        reader.device.raw_data_handler([0, 4, 0])
        self.assertEqual(release_handler.call_count, 1)


@mock.patch('dsd.usb.pywinusb', mock.MagicMock())
class MachineTestCase(unittest.TestCase):

    beeper_mock = None
    beeper = None

    raildriver_mock = None
    raildriver_patcher = None

    def setUp(self):
        self.beeper = mock.patch('dsd.sound.Beeper')
        self.beeper_mock = self.beeper.start().return_value
        self.raildriver_patcher = mock.patch('raildriver.RailDriver')
        self.raildriver_mock = self.raildriver_patcher.start().return_value
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30)

    def tearDown(self):
        self.raildriver_patcher.stop()

    def test_initial_state_is_inactive(self):
        """
        Initially the DSD should be Inactive.
        """
        self.raildriver_mock.get_current_controller_value.return_value = 0
        machine = dsd.DSDMachine()
        self.assertEqual(machine.current_state.name, 'inactive')

    def test_initial_reverser_fwd(self):
        """
        If in the initial state the reverser is in FWD, move immediately into 'needs depress' state.
        """
        self.raildriver_mock.get_current_controller_value.return_value = 1.0
        machine = dsd.DSDMachine()
        self.assertEqual(machine.current_state.name, 'needs_depress')

    def test_initial_reverser_rev(self):
        """
        If in the initial state the reverser is in REV, move immediately into 'needs depress' state.
        """
        self.raildriver_mock.get_current_controller_value.return_value = -1.0
        machine = dsd.DSDMachine()
        self.assertEqual(machine.current_state.name, 'needs_depress')

    def test_needs_depress_enter_beep(self):
        """
        Entering 'needs depress' state should sound the beeper
        """
        machine = dsd.DSDMachine()
        machine.set_state('needs_depress')
        self.beeper_mock.start.assert_called_with()

    def test_needs_depress_to_idle(self):
        """
        Depressing the footpedal in 'needs depress' state changes state to 'idle'
        """
        machine = dsd.DSDMachine()
        machine.set_state('needs_depress')
        machine.usb.execute_bindings('on_depress')
        self.assertEqual(machine.current_state.name, 'idle')

    def test_needs_depress_6_passed_emergency_brake(self):
        """
        If pedal is not depressed during the 6 seconds period, trigger the EB but don't change the state.
        """
        machine = dsd.DSDMachine()
        machine.set_state('needs_depress')
        machine.raildriver_listener._execute_bindings('on_time_change',
                                                      datetime.time(12, 30, 6), datetime.time(12, 30, 5))
        self.raildriver_mock.set_controller_value.assert_called_with('EmergencyBrake', 1)

    def test_idle_enter_no_beep(self):
        """
        Entering 'idle' silences the beeper
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.beeper_mock.stop.assert_called_with()

    def test_idle_enter_set_timer(self):
        """
        Entering 'idle' should set the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.assertEqual(machine.model.react_by, datetime.time(12, 31))

    def test_idle_aws_reset_resets_timer(self):
        """
        When AWS Reset button is used, reset the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        machine.raildriver_listener._execute_bindings('on_awsreset_change', 0, 1)
        self.assertEqual(machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_bell_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        machine.raildriver_listener._execute_bindings('on_bell_change', 0, 1)
        self.assertEqual(machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_horn_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        machine.raildriver_listener._execute_bindings('on_horn_change', 0, 1)
        self.assertEqual(machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_regulator_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        machine.raildriver_listener._execute_bindings('on_regulator_change', 0, 1)
        self.assertEqual(machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_train_brake_control_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        machine.raildriver_listener._execute_bindings('on_trainbrakecontrol_change', 0, 1)
        self.assertEqual(machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_60_seconds_passed_to_needs_depress(self):
        """
        When 60 seconds pass since the timer was last reset change state to 'needs depress'
        """
        machine = dsd.DSDMachine()
        machine.set_state('idle')
        machine.raildriver_listener._execute_bindings('on_time_change', datetime.time(12, 31), datetime.time(12, 30, 59))
        self.assertEqual(machine.current_state.name, 'needs_depress')
