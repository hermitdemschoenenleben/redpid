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
    yield dut.ki.storage.eq(3000)
    yield dut.input.eq(1623)

    for i in range(500):
        yield

        out = yield dut.pid_out
        ki_mult = yield dut.ki_mult
        error = yield dut.error
        int_sum = yield dut.int_sum
        int_reg = yield dut.int_reg
        int_sum_sign = yield dut.int_sum[-1]
        int_sum_last = yield dut.int_sum[-2]
        print('sign', int_sum_sign, 'last', int_sum_last)
        print('int_sum', bin(int_sum))
        #print('int_reg', int_reg)
        print('out', out)
        print('int_reg', bin(int_reg))
        print('')

        if out < 0:
            break

width = 14
pid = PID(width=width)
run_simulation(pid, test_p(pid, width))
pid = PID(width=width)
run_simulation(pid, test_i(pid, width))