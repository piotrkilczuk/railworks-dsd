import datetime
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

    machine = None

    raildriver_controller_values = None
    raildriver_mock = None
    raildriver_patcher = None

    def setUp(self):
        self.beeper = mock.patch('dsd.sound.Beeper')
        self.beeper_mock = self.beeper.start().return_value
        self.raildriver_patcher = mock.patch('raildriver.RailDriver')
        self.raildriver_controller_values = {
            'Reverser': 0,
        }
        self.raildriver_mock = self.raildriver_patcher.start().return_value
        self.raildriver_mock.get_controller_list.return_value = [
            # this has to have all the controls listed in the 'Default' machine
            (10, 'AWSReset'), (20, 'Bell'), (30, 'Horn'), (40, 'Regulator'), (50, 'Reverser'), (60, 'TrainBrakeControl')
        ]
        self.raildriver_mock.get_current_controller_value.side_effect = self.raildriver_controller_values.get
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30)
        self.raildriver_mock.get_loco_name.return_value = ['DTG', 'Class 55', 'Class 55 BR Blue']

    def tearDown(self):
        self.raildriver_patcher.stop()
        self.machine.close()

    def test_initially_no_loco(self):
        """
        Do not initialize model until loco is loaded
        """
        self.raildriver_mock.get_loco_name.return_value = None
        self.machine = dsd.DSDMachine()
        self.assertFalse(self.machine.needs_restart)
        self.assertIsNone(self.machine.model)

    def test_initially_loco_explicit_model(self):
        """
        If initially there is already a loco active don't set needs_restart flag.
        Use the explicit model if available.
        """
        Class55DSDModel = type('Class55DSDModel', (dsd.machine.models.BaseDSDModel,), {})
        with mock.patch('dsd.machine.MODEL_MAPPING', {
            'DTG.Class 55': Class55DSDModel,
            'Default': dsd.machine.models.GenericDSDModel,
        }):
            self.machine = dsd.DSDMachine()
            self.assertIsInstance(self.machine.model, Class55DSDModel)
            self.assertFalse(self.machine.needs_restart)

    def test_initially_loco_default_model(self):
        """
        If initially there is already a loco active don't set needs_restart flag.
        Use the default model if explicit model is not available.
        """
        self.machine = dsd.DSDMachine()
        self.assertFalse(self.machine.needs_restart)
        self.assertIsInstance(self.machine.model, dsd.MODEL_MAPPING['Default'])

    def test_initial_state_is_inactive(self):
        """
        Initially the DSD should be Inactive.
        """
        self.raildriver_mock.get_current_controller_value.return_value = 0
        self.machine = dsd.DSDMachine()
        self.assertEqual(self.machine.current_state.name, 'inactive')

    def test_initial_reverser_fwd(self):
        """
        If in the initial state the reverser is in FWD, move immediately into 'needs depress' state.
        """
        self.raildriver_controller_values['Reverser'] = 1.0
        self.machine = dsd.DSDMachine()
        self.assertEqual(self.machine.current_state.name, 'needs_depress')

    def test_initial_reverser_rev(self):
        """
        If in the initial state the reverser is in REV, move immediately into 'needs depress' state.
        """
        self.raildriver_controller_values['Reverser'] = -1.0
        self.machine = dsd.DSDMachine()
        self.assertEqual(self.machine.current_state.name, 'needs_depress')

    def test_inactive_to_needs_depress_fwd(self):
        """
        If while 'inactive' reverser is moved to FWD, change to 'needs depress'
        """
        self.machine = dsd.DSDMachine()
        self.raildriver_controller_values['Reverser'] = 1.0
        self.machine.raildriver_listener._execute_bindings('on_reverser_change', 1.0, 0)
        self.assertEqual(self.machine.current_state.name, 'needs_depress')

    def test_inactive_to_needs_depress_rev(self):
        """
        If while 'inactive' reverser is moved to REV, change to 'needs depress'
        """
        self.machine = dsd.DSDMachine()
        self.raildriver_controller_values['Reverser'] = -1
        self.machine.raildriver_listener._execute_bindings('on_reverser_change', -1.0, 0)
        self.assertEqual(self.machine.current_state.name, 'needs_depress')

    def test_inactive_important_control_change_does_not_bump_timeout(self):
        """
        Moving 'important control' should only change 'react_by' when in idle.
        """
        self.machine = dsd.DSDMachine()
        self.assertIsNone(self.machine.model.react_by)
        self.machine.raildriver_listener._execute_bindings('on_regulator_change', 0, 0.5)
        self.assertIsNone(self.machine.model.react_by)

    def test_needs_depress_enter_beep(self):
        """
        Entering 'needs depress' state should sound the beeper
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('needs_depress')
        self.beeper_mock.start.assert_called_with()

    def test_needs_depress_to_idle(self):
        """
        Depressing the footpedal in 'needs depress' state changes state to 'idle'
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('needs_depress')
        self.machine.usb.execute_bindings('on_depress')
        self.beeper_mock.stop.assert_called_with()
        self.assertEqual(self.machine.current_state.name, 'idle')

    def test_needs_depress_6_passed_emergency_brake(self):
        """
        If pedal is not depressed during the 6 seconds period, trigger the EB but don't change the state.
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('needs_depress')
        self.machine.raildriver_listener._execute_bindings('on_time_change',
                                                           datetime.time(12, 30, 6), datetime.time(12, 30, 5))
        self.raildriver_mock.set_controller_value.assert_called_with('EmergencyBrake', 1)

    def test_needs_depress_important_control_change_does_not_bump_timeout(self):
        """
        Moving 'important control' should only change 'react_by' when in idle.
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('needs_depress')
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 30, 6))
        self.machine.raildriver_listener._execute_bindings('on_regulator_change', 1, 0.5)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 30, 6))

    def test_idle_enter_no_beep(self):
        """
        Entering 'idle' silences the beeper
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.beeper_mock.stop.assert_called_with()

    def test_idle_enter_set_timer(self):
        """
        Entering 'idle' should set the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31))

    def test_idle_aws_reset_resets_timer(self):
        """
        When AWS Reset button is used, reset the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        self.machine.raildriver_listener._execute_bindings('on_awsreset_change', 0, 1)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_bell_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        self.machine.raildriver_listener._execute_bindings('on_bell_change', 0, 1)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_horn_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        self.machine.raildriver_listener._execute_bindings('on_horn_change', 0, 1)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_regulator_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        self.machine.raildriver_listener._execute_bindings('on_regulator_change', 0, 1)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_train_brake_control_resets_timer(self):
        """
        When Bell button is used, reset the timer to now + 60 seconds
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_time.return_value = datetime.time(12, 30, 30)
        self.machine.raildriver_listener._execute_bindings('on_trainbrakecontrol_change', 0, 1)
        self.assertEqual(self.machine.model.react_by, datetime.time(12, 31, 30))

    def test_idle_pedal_released_fwd(self):
        """
        When pedal is unexpectedly released in 'idle' instantly trigger EB but only if reverser is not in neutral
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_controller_values['Reverser'] = 1.0
        self.machine.usb.execute_bindings('on_release')
        self.assertEqual(self.machine.current_state.name, 'needs_depress')
        self.raildriver_mock.set_controller_value.assert_called_with('EmergencyBrake', 1)

    def test_idle_pedal_released_neutral(self):
        """
        When pedal is released in 'idle' don't trigger EB when the reverser is in neutral

        Transition from 'idle' to 'inactive' should happen in 'on_reverser_changed'
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_controller_values['Reverser'] = 0  # explicit is better than implicit
        self.machine.usb.execute_bindings('on_release')
        self.assertEqual(self.machine.current_state.name, 'idle')

    def test_idle_60_seconds_passed_to_needs_depress(self):
        """
        When 60 seconds pass since the timer was last reset change state to 'needs depress'
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.machine.raildriver_listener._execute_bindings('on_time_change',
                                                           datetime.time(12, 31), datetime.time(12, 30, 59))
        self.assertEqual(self.machine.current_state.name, 'needs_depress')

    def test_idle_reverser_neutral(self):
        """
        When while 'idle' reverser is moved to NEU, move to 'inactive'
        """
        self.machine = dsd.DSDMachine()
        self.machine.set_state('idle')
        self.raildriver_mock.get_current_controller_value.return_value = 0
        self.machine.raildriver_listener._execute_bindings('on_reverser_change', 0, 1)
        self.assertEqual(self.machine.current_state.name, 'inactive')

    def test_reinitialize_model_on_loconame_change(self):
        """
        When loco changes it's better to reinitialize the machine as controls might have changed
        """
        self.machine = dsd.DSDMachine()
        self.assertTrue(self.machine.raildriver_listener.running)
        self.raildriver_mock.get_loco_name.return_value = ['DTG', 'Class 55', 'Class 55 BR Blue']
        self.machine.raildriver_listener._execute_bindings('on_loconame_change', 'Class 55 BR Blue', 'Class 43 FGW')
        self.assertTrue(self.machine.needs_restart)
