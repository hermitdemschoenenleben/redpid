from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from sequence_player import SequencePlayer


def data_storage_testbench(dut, N_bits, N_points):
    points = list(range(N_points))

    def gen_val(i):
        return i

    # read in data
    for address, [i1, i2] in enumerate(zip(points[0::2], points[1::2])):
        v1, v2 = gen_val(i1), gen_val(i2)

        yield from dut.data_addr.write(address)
        yield from dut.data_in.write(v1 + (v2 << N_bits))
        #yield from dut.data_write.write(1)
        #yield
        #yield from dut.data_write.write(0)
        yield


def sequence_player_testbench(dut, N_bits, N_points):
    points = list(range(N_points))

    def gen_val(i):
        return i
        #return -1 * (1 << (N_bits - 1))

    for address, [i1, i2] in enumerate(zip(points[0::2], points[1::2])):
        yield from dut.data_addr.write(address)
        yield from dut.data_in.write(gen_val(i1) + (gen_val(i2) << N_bits))
        yield

    #test_data = 0

    #for i in range(N_points):
    #    test_data += i << (i * N_bits)

    #yield dut.data.status.eq(test_data)
    yield
    yield
    yield

    # replay data and record data
    yield from dut.enabled.write(1)

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


def clock_testbench(dut, N_bits, N_points):
    yield from dut.dcycle.write(int(N_points/2))
    yield from dut.enabled.write(1)

    for i in range(N_points * 5):
        yield

    yield from dut.dcycle.write(int(N_points/10))

    for i in range(N_points * 3):
        yield

    for i in range(N_points * 3):
        yield


N_bits = 3
N_points = 8
sp = SequencePlayer(False, N_bits, N_points)
run_simulation(sp, data_storage_testbench(sp, N_bits, N_points), vcd_name="data_storage.vcd")

N_points = 8
N_bits = 3
sp = SequencePlayer(False, N_bits=N_bits, N_points=N_points)
run_simulation(sp, sequence_player_testbench(sp, N_bits, N_points), vcd_name="sequence_player.vcd")


N_points = 128
N_bits = 3
sp = SequencePlayer(True, N_bits=N_bits, N_points=N_points)
run_simulation(sp, clock_testbench(sp, N_bits, N_points), vcd_name="clock.vcd")

