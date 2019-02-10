from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter
from .sequence_player import SequencePlayer


class ClockPlayer(SequencePlayer):
    def __init__(self, N_bits=14, N_points=16384):
        super().__init__(N_bits=N_bits, N_points=N_points)

        self.dcycle = CSRStorage(bits_for(self.N_points - 1))
        self.clock_max = CSRStorage(N_bits)
        self.play_clock()

    def play_clock(self):
        self.comb += [
            If(self.counter < self.dcycle.storage,
                self.value_internal.eq(
                    self.clock_max.storage
                )
            ).Else(
                self.value_internal.eq(0)
            )
        ]
