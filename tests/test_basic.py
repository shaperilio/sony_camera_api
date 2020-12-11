import unittest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
import pysony


class TestBasics(unittest.TestCase):

    def test_loadpysony(self):
        api = pysony.SonyAPI()
        self.assertEqual(api.QX_ADDR, 'http://10.0.0.1:10000')
