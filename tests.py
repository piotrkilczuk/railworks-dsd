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

    machine = None

    def setUp(self):
        self.machine = dsd.DSD()

    def assertIsState(self, state_instance):
        self.assertEqual(self.machine.state, state_instance.name)

    def test_initial_state_is_Inactive(self):
        """
        Initially the DSD should be Inactive.
        """
        self.assertIsState(dsd.Inactive)
