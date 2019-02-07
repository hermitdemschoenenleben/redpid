from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from sequence_player import SequencePlayer


def data_storage_testbench(dut, N_bits, N_points):
    # read in data
    for i in range(N_points):
        if i % 2:
            new = 3
        else:
            new = 0

        print(new)
        yield from dut.data_in.write(new)
        yield from dut.data_addr.write(i)
        #yield from dut.data_write.write(1)
        #yield
        #yield from dut.data_write.write(0)
        yield


def sequence_player_testbench(dut, N_bits, N_points):
    for i in range(N_points):
        yield dut.feedforward[i].eq(i)
    #test_data = 0

    #for i in range(N_points):
    #    test_data += i << (i * N_bits)

    #yield dut.data.status.eq(test_data)
    yield
    yield
    yield

    # replay data and record data
    yield from dut.enabled.write(1)
    yield dut.reset_sequence.eq(0)

    for i in range(4):
        if i == 1:
            yield from dut.recording.write(1)

        for i in range(N_points):
            yield dut.output.eq(dut.value)
            yield

    # test readout

    for i in range(N_points):
        yield from dut.data_out_addr.write(i)
        yield


N_bits = 2
N_points = 8
sp = SequencePlayer(N_bits, N_points)
run_simulation(sp, data_storage_testbench(sp, N_bits, N_points), vcd_name="data_storage.vcd")
N_points = 8
N_bits = 14
sp = SequencePlayer(N_bits=N_bits, N_points=N_points)
run_simulation(sp, sequence_player_testbench(sp, N_bits, N_points), vcd_name="sequence_player.vcd")
