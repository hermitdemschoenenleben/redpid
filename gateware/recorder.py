from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux

from .utils import create_memory
from .constants import STATUS_REPLAY, STATUS_REPLAY_RECORD_COUNT, \
    STATUS_REPLAY_ADJUST, STATUS_REPLAY_FILTER_DIRECTION


class Recorder(Module):
    def __init__(self, parent, N_bits=14, N_points=16384, N_zones=4):
        self.parent = parent

        self.N_bits = N_bits
        self.N_points = N_points
        self.N_zones = N_zones

        self.status = Signal.like(parent.status)
        self.sync += [
            self.status.eq(parent.status)
        ]

        self.create_memory()
        self.record_output()
        # communication with CPU via the bus
        self.feedforward_to_bus()

    def create_memory(self):
        # initialize buffer for recorded output
        self.rec_rdport, self.rec_wrport = create_memory(
            self, self.N_bits, self.N_points, 'recorded'
        )

        # initialize buffer for recorded input
        self.rec_error_signal_rdport, self.rec_error_signal_wrport = create_memory(
            self, 2, self.N_points, 'recorded_error_signal'
        )

        self.specials += [
            self.rec_rdport, self.rec_wrport,
            self.rec_error_signal_wrport, self.rec_error_signal_rdport
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

        current_error_signal_counter = self.error_signal_counters[self.parent.clock.current_zone]

        self.sync += [
            # record control signal
            self.rec_wrport.we.eq(self.parent.recording.storage),
            self.rec_wrport.adr.eq(self.parent.counter),
            self.rec_wrport.dat_w.eq(self.control_signal),

            # record error signal
            self.rec_error_signal_wrport.we.eq(
                self.parent.recording.storage | (self.status == STATUS_REPLAY_RECORD_COUNT)
            ),
            self.rec_error_signal_wrport.adr.eq(self.parent.counter),
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
            If(self.parent.recording.storage,
                If(self.parent.counter == 0,
                    self.end_counter.eq(self.end_counter + 1)
                )
            ).Else(
                self.end_counter.eq(0)
            )
        ]

        self.comb += [
            If(self.parent.recording.storage,
                If(self.end_counter == 2,
                    self.parent.recording.storage.eq(0)
                )
            )
        ]

    def feedforward_to_bus(self):
        """Writes the current feed forward to the bus."""
        self.sync += [
            self.rec_rdport.adr.eq(self.parent.data_out_addr.storage),
            self.parent.data_out.status.eq(self.rec_rdport.dat_r),

            If(~self.parent.run_algorithm.storage,
                self.rec_error_signal_rdport.adr.eq(self.parent.error_signal_out_addr.storage),
                self.parent.error_signal_out.status.eq(self.rec_error_signal_rdport.dat_r),
            )
        ]