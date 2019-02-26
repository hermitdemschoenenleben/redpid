from migen import *
from migen.sim import Simulator, run_simulation

from .pid import PID

def test_p(dut, width):
    max_pos = (1 << (width - 1)) - 1
    max_neg = -1 * max_pos - 1

    def next_():
        yield
        yield
        yield
        yield
        yield

    # test neutral multiplication
    neutral_mult = 4096

    positive_in = 123
    yield dut.kp.storage.eq(neutral_mult)
    yield dut.input.eq(positive_in)

    yield from next_()

    out = yield dut.pid_out
    assert out == positive_in

    # test neutral multiplication with negative input
    negative_in = -123
    yield dut.input.eq(negative_in)
    yield dut.kp.storage.eq(neutral_mult)

    yield from next_()

    out = yield dut.pid_out
    assert out == negative_in

    # test sign swapping with negative kp
    yield dut.kp.storage.eq(-1 * neutral_mult)
    yield dut.input.eq(positive_in)

    yield from next_()

    out = yield dut.pid_out
    assert out == -1 * positive_in

    # test neutral multiplication with negative input
    yield dut.input.eq(negative_in)
    yield dut.kp.storage.eq(-1 * neutral_mult)

    yield from next_()

    out = yield dut.pid_out
    assert out == -1 * negative_in

    # test saturation
    yield dut.input.eq(8000)
    yield dut.kp.storage.eq(8000)
    yield from next_()
    out = yield dut.pid_out
    assert out == max_pos

    yield dut.input.eq(-8000)
    yield dut.kp.storage.eq(8000)
    yield from next_()
    out = yield dut.pid_out
    assert out == max_neg

    yield dut.input.eq(8000)
    yield dut.kp.storage.eq(-8000)
    yield from next_()
    out = yield dut.pid_out
    assert out == max_neg

    yield dut.input.eq(-8000)
    yield dut.kp.storage.eq(-8000)
    yield from next_()
    out = yield dut.pid_out
    assert out == max_pos


def test_i(dut, width):
    yield dut.kd.storage.eq(10)

    for i in range(20):
        yield dut.input.eq(i * 15)
        yield

        out = yield dut.pid_out

        print('out', out)


def test_d(dut, width):
    yield dut.kd.storage.eq(4096)

    for i in range(20):
        yield dut.input.eq(i ** 2)
        yield

        out = yield dut.pid_out

        print('out', out)



width = 14
pid = PID(width=width)
run_simulation(pid, test_p(pid, width))
pid = PID(width=width)
run_simulation(pid, test_i(pid, width))
pid = PID(width=width)
run_simulation(pid, test_d(pid, width))