from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .feed_forward import FeedForwardPlayer, STATUS_REPLAY_RECORD_COUNT, \
    STATUS_REPLAY


def convert_number(n, N_bits):
    max_pos = (1 << (N_bits - 1)) - 1
    if n > max_pos:
        return n - 2 * (max_pos + 1)
    return n


def testbench(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.status.eq(3)
    yield from player.clock.zone_end_0.write(3)
    yield from player.clock.zone_end_1.write(-1)
    yield from player.clock.zone_end_2.write(-1)

    points = list(range(N_points))

    def gen_val(i):
        return i

    yield player.error_signal.eq(1)

    for i in points:
        yield player.feedforward[i].eq(i)

    # this records the error signal and counts the error signal counter up
    for i in range(N_points):
        yield

    # this adjusts the feed forward
    for i in range(N_points):
        yield

    # this replays the adjusted version
    for i in range(2 * N_points):
        yield


def test_to_max(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.status.eq(3)
    yield from player.clock.zone_end_0.write(3)
    yield from player.clock.zone_end_1.write(-1)
    yield from player.clock.zone_end_2.write(-1)

    while True:
        status = yield player.status
        counter = yield player.counter
        if status == STATUS_REPLAY and counter == N_points - 1:
            break
        yield

    for i in range(2 * N_bits):
        # this records the error signal and counts the error signal counter up
        for i in range(N_points):
            if i < 4:
                yield player.error_signal.eq(1)
            else:
                yield player.error_signal.eq(-1)
            yield

        # this adjusts the feed forward
        for i in range(N_points):
            yield

        # this replays the adjusted version
        for i in range(2 * N_points):
            yield

    for i in range(N_points):
        value = yield player.feedforward[i]
        if i < 4:
            assert convert_number(value, N_bits) == 7
        else:
            assert convert_number(value, N_bits) == -8
        print('VAL', convert_number(value, N_bits))


def test_updown(player: FeedForwardPlayer, N_bits: int, N_points: int):
    print('updown')
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield

    # this records the error signal and counts the error signal counter up
    for i in range(N_points):
        #print('ERR', 1 if i < N_points - 9 else -1)
        es = 1 if i < N_points -2 else -1
        print('ES', es)
        yield player.error_signal.eq(es)
        yield

    # this adjusts the feed forward
    for i in range(N_points):
        yield

    # this replays the adjusted version
    for i in range(2 * N_points):
        yield

    for i in range(N_points):
        value = yield player.feedforward[i]
        print('NEW FF', convert_number(value, N_bits))



N_bits = 4
N_points = 8
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, testbench(player, N_bits, N_points), vcd_name="feedforward.vcd")


player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_to_max(player, N_bits, N_points), vcd_name="feedforward_to_max.vcd")

"""
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_updown(player, N_bits, N_points), vcd_name="feedforward_updown.vcd")
"""