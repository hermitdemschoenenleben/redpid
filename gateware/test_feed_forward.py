from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .feed_forward import FeedForwardPlayer, STATE_REPLAY_RECORD_COUNT, \
    STATE_REPLAY, STATE_REPLAY_FILTER_DIRECTION, STATE_REPLAY_FILTER_CURVATURE


def convert_number(n, N_bits):
    max_pos = (1 << (N_bits - 1)) - 1
    if n > max_pos:
        return n - 2 * (max_pos + 1)
    return n


def testbench(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.state.eq(3)
    yield from player.zone_edge_0.write(3)
    yield from player.zone_edge_1.write(-1)
    yield from player.zone_edge_2.write(-1)

    points = list(range(N_points))

    def gen_val(i):
        return i

    yield player.recorder.error_signal.eq(1)

    for i in points:
        yield player.feedforward[i].eq(i)

    for i in range(2):
        # this records the error signal and counts the error signal counter up
        for i in range(N_points):
            yield

        # this adjusts the feed forward
        for i in range(N_points):
            yield

        # this replays the adjusted version
        for i in range(2 * N_points):
            yield


def test_recording(player: FeedForwardPlayer, N_bits: int, N_points: int):
    """Tests immediate recording via `request_recording`."""
    yield player.enabled.storage.eq(1)
    yield player.run_algorithm.storage.eq(1)
    yield player.state.eq(3)
    yield player.zone_edge_0.storage.eq(3)
    yield player.zone_edge_1.storage.eq(-1)
    yield player.zone_edge_2.storage.eq(-1)
    yield player.request_recording.storage.eq(1)
    yield player.max_state.storage.eq(6)
    yield player.state.eq(6)
    yield player.leading_counter.eq(N_points - 2)

    player.comb += [
        player.recorder.control_signal.eq(
            player.value
        )
    ]

    points = list(
        v + 1 for v in
        range(N_points)
    )

    for i, point in enumerate(points):
        yield player.feedforward[i].eq(point)

    # this records the error signal and counts the error signal counter up
    for i in range(3 * N_points):
        yield

    recorded_data = []
    for i in range(N_points):
        v = yield player.recorder.recorded[i]
        recorded_data.append(v)

    assert recorded_data == points

    # now replay some random stuff and check that recorded data is not
    # influenced any more
    for i in range(N_points):
        yield player.feedforward[i].eq(randint(0, 1))

    for i in range(N_points * 20):
        yield

    recorded_data = []
    for i in range(N_points):
        v = yield player.recorder.recorded[i]
        recorded_data.append(v)

    assert recorded_data == points


def test_planned_recording(player: FeedForwardPlayer, N_bits: int, N_points: int):
    """Tests planned recording via `record_after`."""
    yield player.enabled.storage.eq(1)
    yield player.run_algorithm.storage.eq(1)
    yield player.state.eq(3)
    yield player.zone_edge_0.storage.eq(3)
    yield player.zone_edge_1.storage.eq(-1)
    yield player.zone_edge_2.storage.eq(-1)
    yield player.max_state.storage.eq(0)
    yield player.state.eq(0)
    yield player.leading_counter.eq(N_points - 2)
    yield player.record_after.storage.eq(10)

    player.comb += [
        player.recorder.control_signal.eq(
            player.value
        )
    ]

    points = list(
        v + 1 for v in
        range(N_points)
    )

    for i, point in enumerate(points):
        yield player.feedforward[i].eq(point)

    # this records the error signal and counts the error signal counter up
    for i in range(2 * N_points):
        yield

    recorded_data = []
    for i in range(N_points):
        v = yield player.recorder.recorded[i]
        recorded_data.append(v)

    assert recorded_data == [0] * N_points

    for i in range(N_points * 20):
        yield

    recorded_data = []
    for i in range(N_points):
        v = yield player.recorder.recorded[i]
        recorded_data.append(v)


    assert recorded_data == points

    # now replay some random stuff and check that recorded data is not
    # influenced any more
    for i in range(N_points):
        yield player.feedforward[i].eq(randint(0, 1))

    for i in range(N_points * 20):
        yield

    recorded_data = []
    for i in range(N_points):
        v = yield player.recorder.recorded[i]
        recorded_data.append(v)

    assert recorded_data == points


def test_to_max(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    start_status = 5
    yield player.state.eq(start_status)
    yield from player.zone_edge_0.write(3)
    yield from player.zone_edge_1.write(-1)
    yield from player.zone_edge_2.write(-1)
    yield from player.max_state.write(start_status + 1)

    while True:
        status = yield player.state
        counter = yield player.counter
        if status == STATE_REPLAY and counter == N_points - 1:
            break
        yield

    for i in range(2 * N_bits):
        # this records the error signal and counts the error signal counter up
        for i in range(N_points):
            if i < 4:
                yield player.recorder.error_signal.eq(1)
            else:
                yield player.recorder.error_signal.eq(-1)
            yield

        # this adjusts the feed forward
        for i in range(N_points):
            yield

        # this replays the adjusted version
        for i in range(5 * N_points):
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
        yield player.recorder.error_signal.eq(es)
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


def test_direction_filtering(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield from player.zone_edge_0.write(3)
    yield from player.zone_edge_1.write(-1)
    yield from player.zone_edge_2.write(-1)
    yield from player.ff_direction_0.write(1)
    yield from player.ff_direction_1.write(-1)
    yield from player.ff_direction_2.write(1)
    yield from player.ff_direction_3.write(1)
    yield player.state.eq(STATE_REPLAY_FILTER_DIRECTION - 2)
    yield player.clock.leading_counter.eq(N_points - 1)

    for i in range(N_points):
        yield player.feedforward[i].eq(i)

    for i in range(3 * N_points):
        yield


def test_slope_filtering(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield player.enabled.storage.eq(1)
    yield player.run_algorithm.storage.eq(1)
    yield player.zone_edge_0.storage.eq(15)
    yield player.zone_edge_1.storage.eq(N_points - 1)
    #yield player.state.eq(STATE_REPLAY_FILTER_CURVATURE-1)
    #yield player.clock.leading_counter.eq(N_points - 1)
    yield player.state.eq(STATE_REPLAY_FILTER_CURVATURE-2)
    yield player.clock.leading_counter.eq(N_points - 5)
    yield player.max_state.storage.eq(100)

    yield player.ff_curvature_filtering_start_0.storage.eq(0)
    yield player.ff_curvature_filtering_start_1.storage.eq(0)

    yield from player.ff_direction_0.write(1)
    yield from player.ff_direction_1.write(-1)
    yield from player.ff_curvature_0.write(1)
    yield from player.ff_curvature_1.write(-1)

    while True:
        status = yield player.state
        counter = yield player.counter
        """start = [200,190,180,170,160,150,140,130,
                 120, 110, 100, 90, 80, 70, 60, 50]"""
        """start = [200, 190, 180, 171, 162, 154, 146, 139,
                 133, 128, 124, 121, 119, 117, 117, 117]"""
        start = [200, 190, 180, 178, 176, 150, 140, 139,
                 133, 128, 124, 121, 119, 117, 117, 117]

        start_neg = [-1 * _ for _ in start]

        start = start + start_neg

        for i in range(N_points):
            yield player.feedforward[i].eq(start[i])

        #if status == STATE_REPLAY_FILTER_CURVATURE:
        #    break
        if counter == 0:
            break

        yield

    for i in range(20 * N_points):
        yield

    new = []
    for i in range(N_points):
        v = yield player.feedforward[i]
        new.append(v)

    from matplotlib import pyplot as plt
    plt.plot(start)
    plt.plot([convert_number(_, N_bits) for _ in new])
    plt.show()




def test_stop(player: FeedForwardPlayer, N_bits: int, N_points: int):
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.state.eq(3)
    yield from player.zone_edge_0.write(N_points - 1)
    yield from player.zone_edge_1.write(-1)
    yield from player.zone_edge_2.write(-1)
    yield from player.stop_zone.write(1)
    yield from player.request_stop.write(1)

    points = list(range(N_points))

    def gen_val(i):
        return i

    yield player.recorder.error_signal.eq(1)

    for i in points:
        yield player.feedforward[i].eq(i)

    for i in range(2):
        # this records the error signal and counts the error signal counter up
        for i in range(N_points):
            yield

        # this adjusts the feed forward
        for i in range(N_points):
            yield

        # this replays the adjusted version
        for i in range(2 * N_points):
            yield


def test_planned_stop(player: FeedForwardPlayer, N_bits: int, N_points: int):
    # FIXME: test is not tested yet ;)
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.state.eq(3)
    yield from player.zone_edge_0.write(int(N_points / 2) - 1)
    yield from player.zone_edge_1.write(-1)
    yield from player.zone_edge_2.write(-1)
    yield from player.stop_zone.write(1)
    yield from player.stop_after.write(2)

    points = list(range(N_points))

    def gen_val(i):
        return i

    for i in points:
        yield player.feedforward[i].eq(i)

    for i in range(20):
        # this records the error signal and counts the error signal counter up
        for i in range(N_points):
            yield

        # this adjusts the feed forward
        for i in range(N_points):
            yield

        # this replays the adjusted version
        for i in range(2 * N_points):
            yield

N_bits = 4
N_points = 8

player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_planned_stop(player, N_bits, N_points), vcd_name="feedforward_planned_stop.vcd")

player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_recording(player, N_bits, N_points), vcd_name="feedforward_recording.vcd")

player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_planned_recording(player, N_bits, N_points), vcd_name="feedforward_planned_recording.vcd")

"""player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, testbench(player, N_bits, N_points), vcd_name="feedforward.vcd")


player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_to_max(player, N_bits, N_points), vcd_name="feedforward_to_max.vcd")
"""
"""
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_updown(player, N_bits, N_points), vcd_name="feedforward_updown.vcd")
"""
"""
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_direction_filtering(player, N_bits, N_points), vcd_name="feedforward_direction.vcd")
"""

"""
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_stop(player, N_bits, N_points), vcd_name="feedforward_stop.vcd")"""

"""N_bits = 10
N_points = 32
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, test_slope_filtering(player, N_bits, N_points), vcd_name="feedforward_slope.vcd")"""

