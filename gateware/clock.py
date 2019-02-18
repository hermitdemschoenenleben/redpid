from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from migen.genlib.cdc import MultiReg, GrayCounter
from .constants import STATUS_REPLAY, STATUS_REPLAY_RECORD_COUNT, \
    STATUS_REPLAY_ADJUST, STATUS_REPLAY_FILTER_DIRECTION


class ClockPlayer(Module):
    def __init__(self, parent, N_zones=4, N_points=16384):
        self.parent = parent
        self.N_points = N_points
        self.N_zones = N_zones

        self.clone_signals(parent)

        self.stopped = Signal()

        self.current_zone = Signal(bits_for(self.N_zones))
        self.current_zone_end = Array(
            self.zone_ends + [Signal(14, reset=self.N_points - 1)]
        )[self.current_zone]

        self.run_counter()
        self.play_clock()

    def clone_signals(self, parent):
        self.enabled = Signal.like(parent.enabled.storage)
        self.reset_sequence = Signal.like(parent.reset_sequence)
        self.zone_ends = [
            # we make it 1 bit wider than needed in order to make it possible
            # to disable a zone (i.e. zone border > N_points)
            Signal(1 + bits_for(self.N_points - 1))
            for N in range(self.N_zones - 1)
        ]
        self.request_stop = Signal.like(parent.request_stop.storage)
        self.stop_zone = Signal.like(parent.stop_zone.storage)

        self.comb += [
            self.enabled.eq(parent.enabled.storage),
            self.reset_sequence.eq(parent.reset_sequence),
            self.request_stop.eq(parent.request_stop.storage & (parent.status == STATUS_REPLAY)),
            self.stop_zone.eq(parent.stop_zone.storage),
        ]

    def run_counter(self):
        self.leading_counter = Signal(bits_for(self.N_points - 1))
        self.counter = Signal.like(self.leading_counter)

        self.sync += [
            If(self.request_stop & (self.current_zone == self.stop_zone) & (self.counter == self.current_zone_end - 3),
                self.stopped.eq(1)
            ),
            If(((~self.stopped) & 0b1),
                If(self.enabled & ((~self.reset_sequence) & 0b1),
                    self.leading_counter.eq(self.leading_counter + 1),
                    self.counter.eq(self.leading_counter - 2)
                ).Else(
                    self.leading_counter.eq(0),
                    self.counter.eq(0)
                )
            )
        ]

    def play_clock(self):
        counter_is_at_zone_end = self.counter == self.current_zone_end
        counter_is_at_last_point = self.counter == self.N_points - 1

        self.counter_in_zone = Signal(bits_for(self.N_points))

        self.sync += [
            If(self.reset_sequence | ((~self.enabled) & 0b1),
                self.current_zone.eq(0),
                self.counter_in_zone.eq(0),
            ),
            If(counter_is_at_zone_end | counter_is_at_last_point,
                self.counter_in_zone.eq(0),
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
            ).Else(
                self.counter_in_zone.eq(self.counter_in_zone + 1)
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