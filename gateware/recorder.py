from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux

from .utils import create_memory
from .constants import STATE_REPLAY, STATE_REPLAY_RECORD_COUNT, \
    STATE_REPLAY_ADJUST, STATE_REPLAY_FILTER_DIRECTION


class Recorder(Module):
    def __init__(self, parent, N_bits=14, N_points=16384, N_zones=4):
        self.parent = parent

        self.N_bits = N_bits
        self.N_points = N_points
        self.N_zones = N_zones

        self.clone_signals(parent)

        self.create_memory()
        self.start_and_stop_recording()
        self.do_recording()
        # communication with CPU via the bus
        self.feedforward_to_bus()

    def clone_signals(self, parent):
        # inputs
        self.state = Signal.like(parent.state)
        self.current_zone = Signal.like(parent.current_zone)
        self.request_recording = Signal.like(parent.request_recording.storage)
        self.counter = Signal.like(parent.counter)
        self.run_algorithm = Signal.like(parent.run_algorithm.storage)#
        self.data_out_addr = Signal.like(parent.data_out_addr.storage)
        self.error_signal_out_addr = Signal.like(parent.error_signal_out_addr.storage)
        self.max_state = Signal.like(parent.max_state.storage)
        self.iteration_counter = Signal.like(parent.iteration_counter)
        self.record_after = Signal.like(parent.record_after.storage)

        # outputs
        self.data_out = Signal.like(parent.data_out.status)
        self.error_signal_out = Signal.like(parent.error_signal_out.status)

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

    def start_and_stop_recording(self):
        """Checks whether to start recording."""
        self.recording = Signal()
        self.recording_finished = Signal()

        is_at_last_point = self.counter == self.N_points - 1
        is_at_last_point_in_last_state = \
            (self.state == self.max_state) \
            & is_at_last_point

        # handle requests for immediate recording
        self.sync += [
            If(self.request_recording & (~self.recording_finished)[0] & is_at_last_point_in_last_state,
                self.recording.eq(1)
            )
        ]

        # handle requests for recording after specific algorithm iteration
        is_at_right_iteration = self.iteration_counter == self.record_after - 1
        self.sync += [
            If((self.record_after > 0) & is_at_last_point_in_last_state & is_at_right_iteration,
                self.recording.eq(1)
            )
        ]

        # stop recording at last point
        self.sync += [
            If(self.recording & is_at_last_point,
                self.recording.eq(0),
                self.recording_finished.eq(1)
            ),
            If((~self.request_recording)[0],
                self.recording_finished.eq(0)
            )
        ]

    def do_recording(self):
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

        current_error_signal_counter = self.error_signal_counters[self.current_zone]

        self.sync += [
            # record control signal
            self.rec_wrport.we.eq(self.recording),
            self.rec_wrport.adr.eq(self.counter),
            self.rec_wrport.dat_w.eq(self.control_signal),

            # record error signal
            self.rec_error_signal_wrport.we.eq(
                self.recording | (self.state == STATE_REPLAY_RECORD_COUNT)
            ),
            self.rec_error_signal_wrport.adr.eq(self.counter),
            self.rec_error_signal_wrport.dat_w.eq(self.error_signal),

            If(self.state == STATE_REPLAY_RECORD_COUNT,
               # update the sum over the error signal
                current_error_signal_counter.eq(
                    current_error_signal_counter + self.error_signal
                )
            ).Elif(self.state == STATE_REPLAY,
                # reset all error signal counters
                *[
                    es_counter.eq(0)
                    for es_counter in self.error_signal_counters
                ]
            )
        ]

    def feedforward_to_bus(self):
        """Writes the current feed forward to the bus."""
        self.sync += [
            self.rec_rdport.adr.eq(self.data_out_addr),
            self.data_out.eq(self.rec_rdport.dat_r),

            If(~self.run_algorithm,
                self.rec_error_signal_rdport.adr.eq(self.error_signal_out_addr),
                self.error_signal_out.eq(self.rec_error_signal_rdport.dat_r),
            )
        ]