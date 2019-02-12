from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .clock import ClockPlayer


def clock_testbench(dut, N_bits, N_points):
    yield from dut.zone_end_0.write(3)
    yield from dut.zone_end_1.write(7)
    yield from dut.zone_end_2.write(11)

    yield from dut.enabled.write(1)

    for i in range(N_points * 5):
        yield

N_points = 16
N_bits = 3
clock = ClockPlayer(N_zones=4, N_bits=N_bits, N_points=N_points)
run_simulation(clock, clock_testbench(clock, N_bits, N_points), vcd_name="clock.vcd")

