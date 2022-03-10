import unittest
from src import bpu
from benedict import benedict as bd


class BPUTests(unittest.TestCase):

    def test_simple_bpu(self):
        predictor = bpu.SimpleBPU(bd.from_yaml('config.yml'))
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
        print(predictor)

    def test_bpu(self):
        advanced_predictor = bpu.BPU(bd.from_yaml('config.yml'))
        advanced_predictor.update(0, True)
        self.assertIs(advanced_predictor.predict(0), True)
        advanced_predictor.update(1, False)
        self.assertIs(advanced_predictor.predict(1), False)
        self.assertIs(advanced_predictor.predict(17), False)
        print(advanced_predictor)


if __name__ == '__main__':
    unittest.main()
