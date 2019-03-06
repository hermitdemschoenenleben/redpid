from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux, ClockDomain
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus

from .clock import ClockPlayer
from .utils import create_memory
from .recorder import Recorder
from .constants import STATE_REPLAY, STATE_REPLAY_RECORD_COUNT, \
    STATE_REPLAY_ADJUST, STATE_REPLAY_FILTER_DIRECTION, STATE_REPLAY_FILTER_CURVATURE


class FeedForwardPlayer(Module, AutoCSR):
    def __init__(self, N_bits=14, N_points=16384, N_zones=4):
        allowed_N_points = [
            1 << shift
            for shift in range(16)
            if shift > 0
        ]
        assert N_points in allowed_N_points, \
            'invalid N_points, allowed: %s' % allowed_N_points

        self.N_bits = N_bits
        self.N_points = N_points
        self.N_zones = N_zones
        self.N_address_bits = bits_for(self.N_points - 1)

        self.max_pos = (1<<(self.N_bits - 1)) - 1
        self.max_neg = -1 * self.max_pos - 1

        # CSR parameters

        # is the feed forward clock running and is the module outputting values?
        self.enabled = CSRStorage()
        # should the algorithm for continuous feed forward improvement run?
        self.run_algorithm = CSRStorage()
        self.stop_algorithm_after = CSRStorage(30, reset=(1<<30) - 1)
        self.algorithm_running = Signal()
        # up to which state should the state machine go in each cycle?
        self.max_state = CSRStorage(10, reset=STATE_REPLAY_FILTER_CURVATURE)
        self.last_point = CSRStorage(bits_for(N_points - 1), reset=N_points - 1)

        # request a stop at a specific zone
        self.request_stop = CSRStorage()
        self.stop_after = CSRStorage(30, reset=(1<<30) - 1)
        self.stop_zone = CSRStorage(bits_for(N_zones))

        # should the feed forward and error signal be recorded?
        # this starts recording immediately
        self.request_recording = CSRStorage()
        # if the recording should not be started immediately but after a
        # specific iteration of the algorithm, use this storage.
        self.record_after = CSRStorage(30)

        # communication with the bus
        self.data_out = CSRStatus(self.N_bits)
        self.data_out_addr = CSRStorage(self.N_address_bits)
        self.error_signal_out = CSRStatus(1)
        self.error_signal_out_addr = CSRStorage(self.N_address_bits)
        self.data_in = CSRStorage(self.N_bits)
        self.data_addr = CSRStorage(self.N_address_bits)
        self.data_write = CSRStorage(1)

        self.step_size = CSRStorage(14, reset=1, write_from_dev=True)
        self.decrease_step_size_after = CSRStorage(16)
        self.keep_constant_at_end = CSRStorage(14)

        self.zone_edges = []
        for N in range(N_zones - 1):
            name = 'zone_edge_%d' % N
            # we make it 1 bit wider than needed in order to make it possible
            # to disable a zone (i.e. zone edge = -1)
            storage = CSRStorage(1 + self.N_address_bits, name=name)
            setattr(self, name, storage)
            self.zone_edges.append(storage.storage)

        self.ff_directions = []
        for N in range(N_zones):
            name = 'ff_direction_%d' % N
            storage = CSRStorage(2, name=name)
            setattr(self, name, storage)
            self.ff_directions.append(storage.storage)

        self.ff_curvatures = []
        self.ff_curvature_filtering_starts = []
        for N in range(N_zones):
            name = 'ff_curvature_%d' % N
            storage = CSRStorage(2, name=name)
            setattr(self, name, storage)
            self.ff_curvatures.append(storage.storage)

            name = 'ff_curvature_filtering_start_%d' % N
            storage = CSRStorage(self.N_bits, name=name)
            setattr(self, name, storage)
            self.ff_curvature_filtering_starts.append(storage.storage)


        # Signals


        self.state = Signal(10)
        self.value_internal = Signal((self.N_bits, True))
        self.value = Signal.like(self.value_internal)
        self.comb += [
            self.value.eq(
                Mux(self.enabled.storage, self.value_internal, 0)
            )
        ]


        # Submodules
        # Connections to and from submodules

        self.submodules.clock = ClockPlayer(self, N_points=N_points, N_zones=N_zones)

        self.counter = Signal.like(self.clock.counter)
        self.leading_counter = Signal.like(self.clock.leading_counter)
        self.current_zone = Signal.like(self.clock.current_zone)
        self.counter_in_zone = Signal.like(self.clock.counter_in_zone)
        self.current_zone_edge = Signal.like(self.clock.current_zone_edge)
        self.iteration_counter = Signal.like(self.clock.iteration_counter)

        self.submodules.recorder = Recorder(self, N_bits=N_bits, N_points=N_points, N_zones=N_zones)

        self.comb += [
            self.algorithm_running.eq(
                self.run_algorithm.storage  & (
                    (self.iteration_counter <= self.stop_algorithm_after.storage)
                )
            ),

            # connections from clock
            self.counter.eq(self.clock.counter),
            self.leading_counter.eq(self.clock.leading_counter),
            self.current_zone.eq(self.clock.current_zone),
            self.counter_in_zone.eq(self.clock.counter_in_zone),
            self.current_zone_edge.eq(self.clock.current_zone_edge),
            self.iteration_counter.eq(self.clock.iteration_counter),

            # connections to clock
            self.clock.enabled.eq(self.enabled.storage),
            self.clock.request_stop.eq(
                (self.request_stop.storage & (self.state == STATE_REPLAY))
                | (self.iteration_counter > self.stop_after.storage)
            ) ,
            self.clock.stop_zone.eq(self.stop_zone.storage),
            self.clock.max_state.eq(self.max_state.storage),
            self.clock.last_point.eq(self.last_point.storage),
            *[
                self.clock.zone_edges[i].eq(self.zone_edges[i])
                for i in range(self.N_zones - 1)
            ],

            # connections to recorder
            self.recorder.current_zone.eq(self.current_zone),
            self.recorder.request_recording.eq(self.request_recording.storage),
            self.recorder.counter.eq(self.counter),
            self.recorder.run_algorithm.eq(self.algorithm_running),
            self.recorder.data_out_addr.eq(self.data_out_addr.storage),
            self.recorder.error_signal_out_addr.eq(self.error_signal_out_addr.storage),
            self.recorder.max_state.eq(self.max_state.storage),
            self.recorder.iteration_counter.eq(self.iteration_counter),
            self.recorder.record_after.eq(self.record_after.storage),
            self.recorder.last_point.eq(self.last_point.storage),

            # connections from recorder
            self.data_out.status.eq(self.recorder.data_out),
            self.error_signal_out.status.eq(self.recorder.error_signal_out)
        ]

        self.comb += [
            self.clock.state.eq(self.state),
            self.recorder.state.eq(self.state)
        ]

        self.init_memories()
        self.update_status()
        self.replay_feedforward()
        self.adjust_feedforward()
        self.ensure_correct_ff_slope_sign()
        self.ensure_correct_ff_curvature()

        # communication with CPU via the bus
        self.bus_to_feedforward()

        self.sync += [
            If(self.algorithm_running,
                self.ff_wrport.we.eq(
                    self.ff_adjustment_we
                    | self.ff_slope_filter_we
                    | self.ff_curvature_filter_we
                )
            )
        ]

    def init_memories(self):
        """Initializes memories."""
        # initialize buffer for feed forward
        self.ff_rdport, self.ff_wrport = create_memory(
            self, self.N_bits, self.N_points, 'feedforward'
        )

        # register all the ports
        self.specials += [
            self.ff_rdport, self.ff_wrport
        ]

    def update_status(self):
        """Updates the status of the state machine when one cycle is completed."""
        self.sync += [
            If(self.algorithm_running,
                If(self.counter == self.last_point.storage,
                    If(self.state == self.max_state.storage,
                        self.state.eq(STATE_REPLAY)
                    ).Else(
                        self.state.eq(self.state + 1)
                    )
                )
            ).Else(
                self.state.eq(STATE_REPLAY)
            )
        ]

    def replay_feedforward(self):
        self.sync += [
            self.ff_rdport.adr.eq(self.leading_counter),
            self.value_internal.eq(self.ff_rdport.dat_r)
        ]

    def adjust_feedforward(self):
        current_error_signal = Signal((2, True))

        current_error_signal_counter = self.recorder.error_signal_counters[self.current_zone]
        self.adjustment_counter = Signal(16)
        constant_signal = Signal(14)

        step_size_shift = Signal(6)
        self.actual_step_size = Signal(14)

        self.sync += [
            self.actual_step_size.eq(self.step_size.storage >> step_size_shift),
            # read error signal from memory
            If(self.algorithm_running,
                self.recorder.rec_error_signal_rdport.adr.eq(self.leading_counter),
                current_error_signal.eq(self.recorder.rec_error_signal_rdport.dat_r),
            ),

            If(self.algorithm_running,
                If(self.state == STATE_REPLAY_ADJUST,
                    If(self.counter == self.last_point.storage,
                        self.adjustment_counter.eq(self.adjustment_counter + 1),
                        If(self.adjustment_counter == self.decrease_step_size_after.storage,
                            self.adjustment_counter.eq(0),
                            If(self.actual_step_size > 1,
                                step_size_shift.eq(step_size_shift + 1)
                            )
                        )
                    ),
                    # write adjusted feed forward
                    self.ff_wrport.adr.eq(self.counter),
                    If(self.counter <= self.current_zone_edge - self.keep_constant_at_end.storage,
                        If (current_error_signal_counter > 0,
                            self.ff_wrport.dat_w.eq(
                                Mux(self.value_internal + self.actual_step_size <= self.max_pos,
                                    self.value_internal + self.actual_step_size,
                                    self.value_internal
                                )
                            )
                        ).Else(
                            self.ff_wrport.dat_w.eq(
                                Mux(self.value_internal - self.actual_step_size >= self.max_neg,
                                    self.value_internal - self.actual_step_size,
                                    self.value_internal
                                )
                            )
                        ),
                    ).Else(
                        self.ff_wrport.dat_w.eq(constant_signal)
                    ),

                    # subtract current error signal value from error signal counter
                    current_error_signal_counter.eq(
                        current_error_signal_counter - current_error_signal
                    ),

                    If(self.counter == self.current_zone_edge - self.keep_constant_at_end.storage,
                        constant_signal.eq(self.ff_wrport.dat_w)
                    )
                )
            )
        ]

        self.ff_adjustment_we = Signal()
        self.comb += [
            self.ff_adjustment_we.eq(
                self.state == STATE_REPLAY_ADJUST
            )
        ]

    def ensure_correct_ff_slope_sign(self):
        initial = 1 << self.N_bits
        self.zone_bounds = [
            Signal((self.N_bits+2, True), name='zone_bound_%d' % N, reset=initial)
            for N in range(self.N_zones)
        ]
        current_zone_bound = Array(self.zone_bounds)[self.current_zone]
        self.current_ff_direction = Signal((2, True))
        self.comb += [
            self.current_ff_direction.eq(
                Array(self.ff_directions)[self.current_zone]
            )
        ]
        sign = self.current_ff_direction

        self.sync += [
            If((self.state == STATE_REPLAY_FILTER_DIRECTION - 1) & (self.counter == self.last_point.storage),
                *[
                    zone_bound.eq(initial)
                    for zone_bound in self.zone_bounds
                ]
            ),
            If((self.state == STATE_REPLAY_FILTER_DIRECTION),
                self.ff_wrport.adr.eq(self.counter),
                If(current_zone_bound == initial,
                    current_zone_bound.eq(self.value),
                    self.ff_wrport.dat_w.eq(self.value)
                ).Else(
                    If(sign * self.value <= sign  * current_zone_bound,
                        self.ff_wrport.dat_w.eq(self.value),
                        current_zone_bound.eq(self.value)
                    ).Else(
                        self.ff_wrport.dat_w.eq(current_zone_bound)
                    )
                )
            )
        ]

        self.ff_slope_filter_we = Signal()
        self.comb += [
            self.ff_slope_filter_we.eq(
                self.state == STATE_REPLAY_FILTER_DIRECTION
            )
        ]

    def ensure_correct_ff_curvature(self):
        self.value_before_1 = Signal((self.N_bits, True))
        self.value_before_2 = Signal((self.N_bits, True))

        sum_ = Signal((self.N_bits+2, True))

        self.sync += [
            self.value_before_1.eq(self.value),
            self.value_before_2.eq(self.value_before_1),

            If(self.state == STATE_REPLAY_FILTER_CURVATURE,
                self.ff_wrport.adr.eq(self.counter - 2),
                sum_.eq((self.value + self.value_before_2) >> 1)
            )
        ]

        current_start = Signal.like(self.ff_curvature_filtering_starts[0])
        current_target_curvature = Signal((2, True))
        self.comb += [
            current_start.eq(
                Array(self.ff_curvature_filtering_starts)[self.current_zone]
            ),
            current_target_curvature.eq(
                Array(self.ff_curvatures)[self.current_zone]
            )
        ]

        sign = current_target_curvature
        point_causes_wrong_curvature = sign * self.value_before_2 > sign * sum_

        self.sync += [
            If(self.state == STATE_REPLAY_FILTER_CURVATURE,
                If(point_causes_wrong_curvature,
                    self.ff_wrport.dat_w.eq(sum_)
                ).Else(
                    self.ff_wrport.dat_w.eq(self.value_before_2)
                )
            )
        ]

        self.ff_curvature_filter_we = Signal()
        self.comb += [
            self.ff_curvature_filter_we.eq(
                (self.state == STATE_REPLAY_FILTER_CURVATURE)
                & (self.counter_in_zone > current_start + 3)
            )
        ]

    def bus_to_feedforward(self):
        """Loads a feed forward signal from CPU."""
        self.sync += [
            If((~self.algorithm_running)[0],
                self.ff_wrport.we.eq(
                    self.data_write.storage
                ),
                self.ff_wrport.adr.eq(self.data_addr.storage),
                self.ff_wrport.dat_w.eq(self.data_in.storage),
            )
        ]
