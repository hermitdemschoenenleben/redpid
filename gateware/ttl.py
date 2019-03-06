from migen import Module, Signal, If, bits_for, Array
from misoc.interconnect.csr import CSRStorage, AutoCSR

class TTLPlayer(Module, AutoCSR):
    def __init__(self, N_ttls=10):
        self.counter = Signal(40)
        self.reset = Signal(1)

        self.sync += [
            If(self.reset,
                self.counter.eq(0)
            ).Else(
                self.counter.eq(
                    self.counter + 1
                )
            )
        ]

        self.starts = []
        self.ends = []
        self.outs = []

        for N in range(N_ttls):
            start = CSRStorage(40, name='ttl%d_start' % N)
            setattr(self, 'ttl%d_start' % N, start)
            end = CSRStorage(40, name='ttl%d_end' % N)
            setattr(self, 'ttl%d_end' % N, end)
            out = Signal(1, name='ttl%d_out' % N)

            self.sync += [
                If((self.counter > start.storage) & (self.counter < end.storage),
                    out.eq(1)
                ).Else(
                    out.eq(0)
                )
            ]

            self.starts.append(start)
            self.ends.append(end)
            self.outs.append(out)

        self.signal_in = []
        self.signal_out = []
        self.state_in = []
        self.state_out = self.outs