import unittest
from src import bpu


class BPUTests(unittest.TestCase):

    def test_simple_bpu(self):
        predictor = bpu.SimpleBPU()
        predictor.update(True)
        self.assertIs(predictor.predict(), True)
        predictor.update(False)
        self.assertIs(predictor.predict(), True)
        predictor.update(False)
        self.assertIs(predictor.predict(), False)
        predictor.update(True)
        self.assertIs(predictor.predict(), False)
        predictor.update(True)
        self.assertIs(predictor.predict(), True)

    def test_bpu(self):
        advanced_predictor = bpu.BPU()
        advanced_predictor.update(0, True)
        self.assertIs(advanced_predictor.predict(0), True)
        advanced_predictor.update(1, False)
        self.assertIs(advanced_predictor.predict(1), False)
        self.assertIs(advanced_predictor.predict(17), False)


if __name__ == '__main__':
    unittest.main()
