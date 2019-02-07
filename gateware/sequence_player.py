from migen import Module, Signal, If, bits_for, Array, Memory, ClockDomainsRenamer, Mux
from misoc.interconnect.csr import CSRStorage, AutoCSR, CSRStatus
from migen.genlib.cdc import MultiReg, GrayCounter


class SequencePlayer(Module, AutoCSR):
    def __init__(self, N_bits=14, N_points=16384):
        allowed_N_points = [
            1 << shift
            for shift in range(16)
        ]
        assert N_points in allowed_N_points, \
            'invalid N_points, allowed: %s' % allowed_N_points

        self.N_bits = N_bits
        self.N_points = N_points

        # initialize buffer for feed forward
        # TODO: using initial values may be helpful
        self.specials.feedforward = Memory(N_bits, N_points, name='feedforward')

        self.ff_rdport = self.feedforward.get_port()
        self.ff_wrport = self.feedforward.get_port(write_capable=True)

        self.specials += self.ff_rdport, self.ff_wrport

        # initialize buffer for recorded output
        self.specials.recorded = Memory(N_bits, N_points, name='recorded')
        self.rec_rdport = self.recorded.get_port()
        self.rec_wrport = self.recorded.get_port(write_capable=True)

        self.specials += self.rec_rdport, self.rec_wrport

        self.read_input_data()
        self.replay_data()
        self.record_output()
        self.readout_output()

    def read_input_data(self):
        # TODO: use the full width of the BUS
        self.data_in = CSRStorage(self.N_bits)
        self.data_addr = CSRStorage(bits_for(self.N_points - 1))
        #self.data_write = CSRStorage(1)

        self.comb += [
            #self.ff_wrport.we.eq(self.data_write.storage),
            self.ff_wrport.we.eq(1),
            self.ff_wrport.adr.eq(self.data_addr.storage),
            self.ff_wrport.dat_w.eq(self.data_in.storage),
        ]

    def replay_data(self):
        self.reset_sequence = Signal()
        self.replay_counter = Signal(bits_for(self.N_points - 1))
        self.value_internal = Signal((self.N_bits, True))
        self.value = Signal((self.N_bits, True))
        self.enabled = CSRStorage()

        self.comb += [
            self.ff_rdport.adr.eq(self.replay_counter),
            self.value_internal.eq(self.ff_rdport.dat_r),
            self.value.eq(
                Mux(
                    self.enabled.storage & ~self.reset_sequence,
                    self.value_internal,
                    0
                )
            )
        ]

        self.sync += [
            If(self.enabled.storage,
                self.replay_counter.eq(
                    self.replay_counter + 1
                ),
            ).Else(
                self.replay_counter.eq(0)
            )
        ]

    def record_output(self):
        self.output = Signal((self.N_bits, True))

        self.recording = CSRStorage()

        self.comb += [
            # FIXME: OUTPUT SOLLTE ECHTER OUTPUT SEIN!!
            self.rec_wrport.we.eq(self.recording.storage),
            self.rec_wrport.adr.eq(self.replay_counter),
            self.rec_wrport.dat_w.eq(self.output),
        ]

        self.end_counter = Signal(2)

        self.sync += [
            # FIXME: Length - 1
            If(self.recording.storage,
                If(self.replay_counter == 0,
                    self.end_counter.eq(self.end_counter + 1)
                ),
                If(self.end_counter == 2,
                    self.recording.storage.eq(0)
                )
            ).Else(
                self.end_counter.eq(0)
            )
        ]

    def readout_output(self):
        self.data_out = CSRStatus(self.N_bits)
        self.data_out_addr = CSRStorage(bits_for(self.N_points - 1))

        self.comb += [
            self.rec_rdport.adr.eq(self.data_out_addr.storage),
            self.data_out.status.eq(self.rec_rdport.dat_r),
        ]
