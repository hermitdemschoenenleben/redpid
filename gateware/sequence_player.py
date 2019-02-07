from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter


class SequencePlayer(Module, AutoCSR):
    def __init__(self, is_clock, N_bits=14, N_points=16384):
        allowed_N_points = [
            1 << shift
            for shift in range(16)
            if shift > 0
        ]
        assert N_points in allowed_N_points, \
            'invalid N_points, allowed: %s' % allowed_N_points

        self.is_clock = is_clock
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

        self.init_counter()

        if self.is_clock:
            self.dcycle = CSRStorage(bits_for(self.N_points - 1))
            self.clock_max = CSRStorage(N_bits)
            self.play_clock()
        else:
            # initialize buffer for feed forward
            self.specials.feedforward = Memory(N_bits * 2, int(N_points / 2), name='feedforward')

            self.ff_rdport = self.feedforward.get_port()
            self.ff_wrport = self.feedforward.get_port(write_capable=True)

            self.specials += self.ff_rdport, self.ff_wrport

            # initialize buffer for recorded output
            self.specials.recorded = Memory(self.N_bits, N_points, name='recorded')
            self.rec_rdport = self.recorded.get_port()
            self.rec_wrport = self.recorded.get_port(write_capable=True)

            self.specials += self.rec_rdport, self.rec_wrport

            self.read_input_data()
            self.replay_data()
            self.record_output()
            self.readout_output()

    def init_counter(self):
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

    def read_input_data(self):
        self.data_in = CSRStorage(self.N_bits * 2)
        self.data_addr = CSRStorage(bits_for(int(self.N_points / 2) - 1))
        #self.data_write = CSRStorage(1)

        self.sync += [
            #self.ff_wrport.we.eq(self.data_write.storage),
            self.ff_wrport.we.eq(1),
            self.ff_wrport.adr.eq(self.data_addr.storage),
            self.ff_wrport.dat_w.eq(self.data_in.storage),
        ]

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

    def replay_data(self):
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
        self.output = Signal((self.N_bits, True))

        self.recording = CSRStorage()

        self.sync += [
            self.rec_wrport.we.eq(self.recording.storage),
            self.rec_wrport.adr.eq(self.counter),
            self.rec_wrport.dat_w.eq(self.output)
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

    def readout_output(self):
        self.data_out = CSRStatus(self.N_bits)
        self.data_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.sync += [
            self.rec_rdport.adr.eq(self.data_out_addr.storage),
            self.data_out.status.eq(self.rec_rdport.dat_r),
        ]