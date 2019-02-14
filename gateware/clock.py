from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter


class ClockPlayer(Module):
    def __init__(self, parent, N_zones=4, N_points=16384):
        self.parent = parent
        self.N_points = N_points
        self.N_zones = N_zones

        self.enabled = Signal()
        self.reset_sequence = Signal()
        self.zone_ends = [
            # we make it 1 bit wider than needed in order to make it possible
            # to disable a zone (i.e. zone border > N_points)
            Signal(1 + bits_for(N_points - 1))
            for N in range(N_zones - 1)
        ]

        self.run_counter()
        self.play_clock()

    def run_counter(self):
        self.leading_counter = Signal(bits_for(self.N_points - 1))
        self.counter = Signal.like(self.leading_counter)

        self.sync += [
            If(self.enabled & ((~self.reset_sequence) & 0b1),
                self.leading_counter.eq(self.leading_counter + 1),
                self.counter.eq(self.leading_counter - 2)
            ).Else(
                self.leading_counter.eq(0),
                self.counter.eq(0)
            )
        ]


    def play_clock(self):
        self.current_zone = Signal(bits_for(self.N_zones))

        self.current_zone_end = Array(
            self.zone_ends + [Signal(14, reset=self.N_points - 1)]
        )[self.current_zone]

        counter_is_at_zone_end = self.counter == self.current_zone_end
        counter_is_at_last_point = self.counter == self.N_points - 1

        self.sync += [
            If(self.reset_sequence | ((~self.enabled) & 0b1),
                self.current_zone.eq(0)
            ),
            If(counter_is_at_zone_end | counter_is_at_last_point,
                If(counter_is_at_last_point,
                    self.current_zone.eq(0)
                ).Else(
                    If(self.current_zone == self.N_zones - 1,
                        self.current_zone.eq(0)
                    ).Else(
                        self.current_zone.eq(
                            self.current_zone + 1
                        )
                    )
                )
            )
        ]

        self.outputs = []

        for i in range(self.N_zones):
            output = Signal()
            self.outputs.append(output)

            self.comb += [
                If(self.current_zone == i,
                    output.eq(1)
                ).Else(
                    output.eq(0)
                )
            ]