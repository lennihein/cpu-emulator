class BPU:
    def __init__(self, config) -> None:
        self.indexing_bits = config["BPU"]["index_bits"]
        self.counter = [(config["BPU"]["init_counter"])] * (1 << self.indexing_bits)

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
    def __init__(self, config) -> None:
        try:
            self.counter: int = config["BPU"]["init_counter"]
        except KeyError:
            self.counter: int = 2

    def update(self, pc, taken: bool) -> None:
        self.counter = bimodal_update(self.counter, taken)

    def predict(self, pc) -> bool:
        return self.counter >= 2

    def set_counter(self, pc, val: int) -> None:
        self.counter = val

    def __str__(self) -> str:
        return str(self.counter)

# this is a 2bit counter, not a 2bit saturating counter!


def bimodal_update(state: int, taken: bool) -> int:
    if taken is True:
        return min(state + 1, 3)
    else:
        return max(state - 1, 0)


def bimodal_prediction(state: int) -> bool:
    return True if state >= 2 else False
