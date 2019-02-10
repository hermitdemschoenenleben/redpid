from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter
from .sequence_player import SequencePlayer


STATUS_REPLAY = 0
STATUS_REPLAY_RECORD = 1
STATUS_REPLAY_COUNT = 2
STATUS_REPLAY_ADJUST = 3


class FeedForwardPlayer(SequencePlayer):
    def __init__(self, N_bits=14, N_points=16384):
        super().__init__(N_bits=N_bits, N_points=N_points)

        self.init_memories()

        self.update_status()
        self.receive_feedforward()
        self.replay_feedforward()
        self.record_output()
        self.send_output()

    def init_memories(self):
        # initialize buffer for feed forward
        self.ff_rdport, self.ff_wrport = self.create_memory(
            self.N_bits * 2, int(self.N_points / 2), 'feedforward'
        )
        self.specials += self.ff_rdport, self.ff_wrport

        # initialize buffer for recorded output
        self.rec_rdport, self.rec_wrport = self.create_memory(
            self.N_bits, self.N_points, 'recorded'
        )
        self.specials += self.rec_rdport, self.rec_wrport

        # initialize buffer for recorded input
        self.rec_error_signal_rdport, self.rec_error_signal_wrport = self.create_memory(
            1, self.N_points, 'recorded_error_signal'
        )
        self.specials += self.rec_error_signal_wrport, self.rec_error_signal_rdport

    def update_status(self):
        self.status = Signal(2)

        self.sync += [
            If(self.counter == self.N_points - 1,
                self.status.eq(self.status + 1)
            )
        ]

    def create_memory(self, N_bits, N_points, name):
        setattr(self.specials, name, Memory(N_bits, N_points, name=name))
        mem = getattr(self, name)

        rdport = mem.get_port()
        wrport = mem.get_port(write_capable=True)

        return rdport, wrport

    def receive_feedforward(self):
        self.data_in = CSRStorage(self.N_bits * 2)
        self.data_addr = CSRStorage(bits_for(int(self.N_points / 2) - 1))
        #self.data_write = CSRStorage(1)

        self.sync += [
            #self.ff_wrport.we.eq(self.data_write.storage),
            self.ff_wrport.we.eq(1),
            self.ff_wrport.adr.eq(self.data_addr.storage),
            self.ff_wrport.dat_w.eq(self.data_in.storage),
        ]

    def replay_feedforward(self):
        # we save two 14-bit values per register
        # -> we have to select the right one
        shift = ((self.counter ^ 0b1) & 0b1) * self.N_bits
        mask = ((1 << self.N_bits) - 1) << shift

        self.sync += [
            self.ff_rdport.adr.eq(self.counter >> 1),
            self.value_internal.eq(
                (self.ff_rdport.dat_r & mask) >> shift
            )
        ]

    def record_output(self):
        # TODO: hier könnte man auch 2 Werte pro Register speichern
        # is connected by FastChain
        self.error_signal = Signal((1, True))
        self.control_signal = Signal((self.N_bits, True))

        self.recording = CSRStorage()

        self.sync += [
            self.rec_wrport.we.eq(self.recording.storage),
            self.rec_wrport.adr.eq(self.counter),
            self.rec_wrport.dat_w.eq(self.control_signal),

            self.rec_error_signal_wrport.we.eq(self.recording.storage),
            self.rec_error_signal_wrport.adr.eq(self.counter),
            self.rec_error_signal_wrport.dat_w.eq(self.error_signal)
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

    def send_output(self):
        self.data_out = CSRStatus(self.N_bits)
        self.data_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.error_signal_out = CSRStatus(1)
        self.error_signal_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.sync += [
            self.rec_rdport.adr.eq(self.data_out_addr.storage),
            self.data_out.status.eq(self.rec_rdport.dat_r),

            self.rec_error_signal_rdport.adr.eq(self.error_signal_out_addr.storage),
            self.error_signal_out.status.eq(self.rec_error_signal_rdport.dat_r),
        ]