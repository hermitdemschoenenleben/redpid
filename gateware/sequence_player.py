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

        # initialize memory
        # TODO: using initial values may be helpful
        self.specials.mem = Memory(N_bits, N_points, name='memory')

        self.mem_rdport = self.mem.get_port()
        self.mem_wrport = self.mem.get_port(write_capable=True)

        self.specials += self.mem_rdport, self.mem_wrport

        self.read_input_data()
        self.replay_data()

    def read_input_data(self):
        # TODO: use the full width of the BUS
        self.data_in = CSRStorage(self.N_bits)
        self.data_addr = CSRStorage(bits_for(self.N_points - 1))
        self.data_write = CSRStorage(1)

        self.comb += [
            self.mem_wrport.we.eq(self.data_write.storage),
            self.mem_wrport.adr.eq(self.data_addr.storage),
            self.mem_wrport.dat_w.eq(self.data_in.storage),
        ]

    def replay_data(self):
        self.reset_sequence = Signal()
        self.replay_counter = Signal(bits_for(self.N_points - 1))
        self.value_internal = Signal((self.N_bits, True))
        self.value = Signal((self.N_bits, True))
        self.enabled = CSRStorage()

        self.comb += [
            self.mem_rdport.adr.eq(self.replay_counter),
            self.value_internal.eq(self.mem_rdport.dat_r),
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
