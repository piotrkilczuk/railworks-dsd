import unittest

import dsd


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
