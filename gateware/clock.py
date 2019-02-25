from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from migen.genlib.cdc import MultiReg, GrayCounter
from .constants import STATE_REPLAY, STATE_REPLAY_RECORD_COUNT, \
    STATE_REPLAY_ADJUST, STATE_REPLAY_FILTER_DIRECTION


class ClockPlayer(Module):
    def __init__(self, parent, N_zones=4, N_points=16384):
        self.parent = parent
        self.N_points = N_points
        self.N_zones = N_zones

        self.clone_signals(parent)

        self.stopped = Signal()

        self.current_zone = Signal(bits_for(self.N_zones))
        self.current_zone_edge = Array(
            self.zone_edges + [Signal(14, reset=self.N_points - 1)]
        )[self.current_zone]

        self.run_counter()
        self.play_clock()

    def clone_signals(self, parent):
        self.enabled = Signal.like(parent.enabled.storage)
        self.zone_edges = [
            Signal.like(parent.zone_edges[0])
            for N in range(self.N_zones - 1)
        ]
        self.request_stop = Signal.like(parent.request_stop.storage)
        self.stop_zone = Signal.like(parent.stop_zone.storage)
        self.state = Signal.like(parent.state)
        self.max_state = Signal.like(parent.max_state.storage)
        self.last_point = Signal.like(parent.last_point.storage)

    def run_counter(self):
        self.leading_counter = Signal(bits_for(self.N_points - 1))
        self.counter = Signal.like(self.leading_counter)

        counter_before = Signal.like(self.leading_counter)
        counter_before_2 = Signal.like(self.leading_counter)

        self.sync += [
            If(self.request_stop & (self.current_zone == self.stop_zone) & (self.counter == self.current_zone_edge - 3),
                self.stopped.eq(1)
            ),
            If(((~self.stopped) & 0b1),
                If(self.enabled,
                    If(self.leading_counter == self.last_point,
                        self.leading_counter.eq(0)
                    ).Else(
                        self.leading_counter.eq(self.leading_counter + 1),
                    ),
                ).Else(
                    self.leading_counter.eq(0),
                )
            ),
            counter_before.eq(self.leading_counter),
            counter_before_2.eq(counter_before),
            self.counter.eq(counter_before_2)
        ]

    def play_clock(self):
        self.iteration_counter = Signal(20)

        counter_is_at_zone_edge = self.counter == self.current_zone_edge
        counter_is_at_last_point = self.counter == self.last_point

        self.counter_in_zone = Signal(bits_for(self.N_points))

        self.sync += [
            If(((~self.enabled) & 0b1),
                self.current_zone.eq(0),
                self.counter_in_zone.eq(0),
                self.iteration_counter.eq(0)
            ),
            If(counter_is_at_zone_edge | counter_is_at_last_point,
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
            ),

            # update iteration counter
            If(self.enabled & counter_is_at_last_point & (self.state == self.max_state),
                self.iteration_counter.eq(
                    self.iteration_counter + 1
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