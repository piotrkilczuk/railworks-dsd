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
