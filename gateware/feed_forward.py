from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter
from .clock import ClockPlayer


STATUS_REPLAY = 0
STATUS_REPLAY_RECORD_COUNT = 1
STATUS_REPLAY_ADJUST = 2
STATUS_REPLAY_FILTER_DIRECTION = 3


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

        self.max_pos = (1<<(self.N_bits - 1)) - 1
        self.max_neg = -1 * self.max_pos - 1

        self.enabled = CSRStorage()
        self.reset_sequence = Signal()
        self.value_internal = Signal((self.N_bits, True))
        self.value = Signal.like(self.value_internal)
        self.request_stop = CSRStorage()
        self.stop_zone = CSRStorage(bits_for(N_zones))

        self.run_algorithm = CSRStorage()
        self.status = Signal(10)
        self.max_status = CSRStorage(10, reset=3)

        self.zone_ends = []
        for N in range(N_zones - 1):
            # we make it 1 bit wider than needed in order to make it possible
            # to disable a zone (i.e. zone border > N_points)
            name = 'zone_end_%d' % N
            storage = CSRStorage(1 + bits_for(N_points - 1), name=name)
            setattr(self, name, storage)
            self.zone_ends.append(storage.storage)

        self.tuning_directions = []
        for N in range(N_zones):
            name = 'tuning_direction_%d' % N
            storage = CSRStorage(2, name=name)
            setattr(self, name, storage)
            self.tuning_directions.append(storage.storage)

        self.comb += [
            self.value.eq(
                Mux(
                    self.enabled.storage & ((~self.reset_sequence) & 0b1),
                    self.value_internal,
                    0
                )
            )
        ]

        self.submodules.clock = ClockPlayer(self, N_points=N_points, N_zones=N_zones)

        self.counter = Signal.like(self.clock.counter)
        self.leading_counter = Signal.like(self.clock.leading_counter)
        self.comb += [
            self.clock.enabled.eq(self.enabled.storage),
            self.clock.reset_sequence.eq(self.reset_sequence),
            self.clock.request_stop.eq(self.request_stop.storage & (self.status == STATUS_REPLAY)),
            self.clock.stop_zone.eq(self.stop_zone.storage),

            self.counter.eq(self.clock.counter),
            self.leading_counter.eq(self.clock.leading_counter),

            *[
                self.clock.zone_ends[i].eq(self.zone_ends[i])
                for i in range(self.N_zones - 1)
            ]
        ]

        self.init_memories()

        self.update_status()
        self.replay_feedforward()
        self.record_output()
        self.adjust_feedforward()
        self.filter_direction()

        # communication with CPU via the bus
        self.bus_to_feedforward()
        self.feedforward_to_bus()

    def init_memories(self):
        """Initializes memories."""
        def create_memory(N_bits, N_points, name):
            setattr(self.specials, name, Memory(N_bits, N_points, name=name))
            mem = getattr(self, name)

            rdport = mem.get_port()
            wrport = mem.get_port(write_capable=True)

            return rdport, wrport

        # initialize buffer for feed forward
        self.ff_rdport, self.ff_wrport = create_memory(
            self.N_bits, self.N_points, 'feedforward'
        )

        # initialize buffer for recorded output
        self.rec_rdport, self.rec_wrport = create_memory(
            self.N_bits, self.N_points, 'recorded'
        )

        # initialize buffer for recorded input
        self.rec_error_signal_rdport, self.rec_error_signal_wrport = create_memory(
            2, self.N_points, 'recorded_error_signal'
        )

        # register all the ports
        self.specials += [
            self.ff_rdport, self.ff_wrport, self.rec_rdport, self.rec_wrport,
            self.rec_error_signal_wrport, self.rec_error_signal_rdport
        ]

    def update_status(self):
        """Updates the status of the state machine when one cycle is completed."""
        self.sync += [
            If(self.run_algorithm.storage,
                If(self.counter == self.N_points - 1,
                    If(self.status == self.max_status.storage,
                        self.status.eq(STATUS_REPLAY)
                    ).Else(
                        self.status.eq(self.status + 1)
                    )
                )
            ).Else(
                self.status.eq(STATUS_REPLAY)
            )
        ]

    def replay_feedforward(self):
        self.sync += [
            self.ff_rdport.adr.eq(self.leading_counter),
            self.value_internal.eq(self.ff_rdport.dat_r)
        ]

    def adjust_feedforward(self):
        current_error_signal = Signal((2, True))

        current_error_signal_counter = self.error_signal_counters[self.clock.current_zone]

        self.step_size = CSRStorage(14, reset=1, write_from_dev=True)
        self.decrease_step_size_after = CSRStorage(16)
        self.adjustment_counter = Signal(16)
        self.keep_constant_at_end = CSRStorage(14)
        constant_signal = Signal(14)

        step_size_shift = Signal(6)
        self.actual_step_size = Signal(14)

        self.sync += [
            self.actual_step_size.eq(self.step_size.storage >> step_size_shift),
            # read error signal from memory
            If(self.run_algorithm.storage,
                self.rec_error_signal_rdport.adr.eq(self.leading_counter),
                current_error_signal.eq(self.rec_error_signal_rdport.dat_r),
            ),

            If(self.run_algorithm.storage,
                self.ff_wrport.we.eq((self.status == STATUS_REPLAY_ADJUST) | (self.status == STATUS_REPLAY_FILTER_DIRECTION)),
                If(self.status == STATUS_REPLAY_ADJUST,
                    If(self.counter == self.N_points - 1,
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
                    If(self.counter <= self.clock.current_zone_end - self.keep_constant_at_end.storage,
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

                    If(self.counter == self.clock.current_zone_end - self.keep_constant_at_end.storage,
                        constant_signal.eq(self.ff_wrport.dat_w)
                    )
                )
            )
        ]

    def filter_direction(self):
        initial = 1 << self.N_bits
        self.zone_bounds = [
            Signal((self.N_bits+2, True), name='zone_bound_%d' % N, reset=initial)
            for N in range(self.N_zones)
        ]
        current_zone_bound = Array(self.zone_bounds)[self.clock.current_zone]
        self.current_tuning_direction = Signal((2, True))
        self.comb += [
            self.current_tuning_direction.eq(
                Array(self.tuning_directions)[self.clock.current_zone]
            )
        ]
        sign = self.current_tuning_direction

        self.sync += [
            If((self.status == STATUS_REPLAY_FILTER_DIRECTION - 1) & (self.counter == self.N_points - 1),
                *[
                    zone_bound.eq(initial)
                    for zone_bound in self.zone_bounds
                ]
            ),
            If((self.status == STATUS_REPLAY_FILTER_DIRECTION),
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

    def record_output(self):
        """Records error and control signal over one cycle.

        Recording is activated if `recording` is True."""
        # the error signal at the current timestamp
        self.error_signal = Signal((2, True))
        # the control signal at the current timestamp
        self.control_signal = Signal((self.N_bits, True))

        # we are going to save the summed error signal over one cycle in this
        # signal
        self.error_signal_counters = Array([
            Signal((bits_for(self.N_points * 3), True), name='error_signal_counter_%d' % N)
            for N in range(self.N_zones)
        ])

        # is recording enabled?
        self.recording = CSRStorage()

        current_error_signal_counter = self.error_signal_counters[self.clock.current_zone]

        self.sync += [
            # record control signal
            self.rec_wrport.we.eq(self.recording.storage),
            self.rec_wrport.adr.eq(self.counter),
            self.rec_wrport.dat_w.eq(self.control_signal),

            # record error signal
            self.rec_error_signal_wrport.we.eq(
                self.recording.storage | (self.status == STATUS_REPLAY_RECORD_COUNT)
            ),
            self.rec_error_signal_wrport.adr.eq(self.counter),
            self.rec_error_signal_wrport.dat_w.eq(self.error_signal),

            If(self.status == STATUS_REPLAY_RECORD_COUNT,
               # update the sum over the error signal
                current_error_signal_counter.eq(
                    current_error_signal_counter + self.error_signal
                )
            ).Elif(self.status == STATUS_REPLAY,
                # reset all error signal counters
                *[
                    es_counter.eq(0)
                    for es_counter in self.error_signal_counters
                ]
            )
        ]

        self.end_counter = Signal(2)

        self.sync += [
            If(self.recording.storage,
                If(self.counter == 0,
                    self.end_counter.eq(self.end_counter + 1)
                )
            ).Else(
                self.end_counter.eq(0)
            )
        ]

        self.comb += [
            If(self.recording.storage,
                If(self.end_counter == 2,
                    self.recording.storage.eq(0)
                )
            )
        ]

    def bus_to_feedforward(self):
        """Loads a feed forward signal from CPU."""
        self.data_in = CSRStorage(self.N_bits)
        self.data_addr = CSRStorage(bits_for(self.N_points - 1))
        #self.data_write = CSRStorage(1)

        self.sync += [
            #self.ff_wrport.we.eq(self.data_write.storage),
            If(~self.run_algorithm.storage,
                # TODO: this should be set externally
                self.ff_wrport.we.eq(1),
                self.ff_wrport.adr.eq(self.data_addr.storage),
                self.ff_wrport.dat_w.eq(self.data_in.storage),
            )
        ]

    def feedforward_to_bus(self):
        """Writes the current feed forward to the bus."""
        self.data_out = CSRStatus(self.N_bits)
        self.data_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.error_signal_out = CSRStatus(1)
        self.error_signal_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.sync += [
            self.rec_rdport.adr.eq(self.data_out_addr.storage),
            self.data_out.status.eq(self.rec_rdport.dat_r),

            If(~self.run_algorithm.storage,
                self.rec_error_signal_rdport.adr.eq(self.error_signal_out_addr.storage),
                self.error_signal_out.status.eq(self.rec_error_signal_rdport.dat_r),
            )
        ]