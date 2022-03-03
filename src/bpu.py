class BPU:
    def __init__(self, indexing_bits=4, init_counter=2) -> None:
        self.indexing_bits = indexing_bits
        self.counter = [init_counter] * (1 << indexing_bits)

    def update(self, pc, taken: bool) -> None:
        self.counter[pc % (1 << self.indexing_bits)] = bimodal_update(
            self.counter[pc % (1 << self.indexing_bits)], taken)

    def predict(self, pc) -> bool:
        return self.counter[pc % (1 << self.indexing_bits)] >= 2

    def set_counter(self, pc, val: int) -> None:
        self.counter[pc % (1 << self.indexing_bits)] = val

    def __str__(self) -> str:
        res = "Index | Counter\n"
        res += "------|--------\n"
        for i in range(len(self.counter)):
            res += "   {:02} | {:01}\n".format(i, self.counter[i])
        return res


class SimpleBPU:
    def __init__(self, counter=2) -> None:
        self.counter: int = counter

    def update(self, taken: bool) -> None:
        self.counter = bimodal_update(self.counter, taken)

    def predict(self) -> bool:
        return self.counter >= 2

    def __str__(self) -> str:
        return str(self.counter)

# this is a 2bit counter, not a 2bit saturating counter!


def bimodal_update(state: int, taken: bool) -> int:
    if taken is True:
        return 1 if state == 0 else 3
    else:
        return 2 if state == 3 else 0


def bimodal_prediction(state: int) -> bool:
    return True if state >= 2 else False
