from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter


class SequencePlayer(Module, AutoCSR):
    def __init__(self, N_bits=14, N_points=16384):
        allowed_N_points = [
            1 << shift
            for shift in range(16)
            if shift > 0
        ]
        assert N_points in allowed_N_points, \
            'invalid N_points, allowed: %s' % allowed_N_points

        self.N_bits = N_bits
        self.N_points = N_points

        self.enabled = CSRStorage()
        self.reset_sequence = Signal()
        self.value_internal = Signal((self.N_bits, True))
        self.value = Signal((self.N_bits, True))

        self.comb += [
            self.value.eq(
                Mux(
                    self.enabled.storage & ((~self.reset_sequence) & 0b1),
                    self.value_internal,
                    0
                )
            )
        ]

        self.run_counter()

    def run_counter(self):
        self.counter = Signal(bits_for(self.N_points - 1))

        self.sync += [
            If(self.enabled.storage & ((~self.reset_sequence) & 0b1),
                self.counter.eq(
                    self.counter + 1
                ),
            ).Else(
                self.counter.eq(0)
            )
        ]
