from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .decimation import Decimate

def testbench(decimate: Decimate):
    yield decimate.decimation.eq(2)

    for i in range(100):
        yield

d = Decimate(10)
run_simulation(d, testbench(d), vcd_name="decimation.vcd")