import pickle
import numpy as np
from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .feed_forward import FeedForwardPlayer, STATE_REPLAY, STATE_REPLAY_RECORD_COUNT


def convert_number(n, N_bits):
    max_pos = (1 << (N_bits - 1)) - 1
    if n > max_pos:
        return n - 2 * (max_pos + 1)
    return n


class Laser:
    def __init__(self, N_points, targets, zone_edges, delay):
        self.N_points = N_points
        self.targets = targets
        self.zone_edges = zone_edges
        self.delay = delay
        self.reset()

    def reset(self):
        self.current = 0
        self.frequency = 0
        self.queue = [0] * self.delay

    def set_current(self, current):
        self.queue.append(current)

    def next_tick(self):
        self.current = self.queue.pop(0)
        diff = self.current - self.frequency
        self.frequency += diff / 100

    def get_error_signal(self, counter):
        target = None
        for zone, end in enumerate(self.zone_edges):
            if counter < end:
                target = self.targets[zone]
                break

        if target is None:
            target = self.targets[-1]

        # noise = randint(0, 5) - 2
        noise = np.random.normal(scale=2.0)

        return 1 if (self.frequency + noise) < target else -1


def write_log(log):
    with open('log-test2.pickle', 'wb') as f:
        pickle.dump(log, f)


def testbench(player: FeedForwardPlayer, N_bits: int, N_points: int):
    #zone_edges = (int((N_points / 4) - 1), int((N_points / 2) - 1), int((3 * N_points / 4) - 1))
    zone_edges = (int((N_points / 2) - 1), N_points + 1, N_points + 1)
    delay = int(N_points/160)
    #l = Laser(N_points, (2500, 2400, -200, -600), zone_edges, delay)
    #l = Laser(N_points, (500, -500, -200, -600), zone_edges, delay)
    l = Laser(N_points, (30, -30, -200, -600), zone_edges, delay)

    log_data = []

    print('delay', delay)
    yield from player.keep_constant_at_end.write(0)
    yield from player.step_size.write(4)
    yield from player.decrease_step_size_after.write(25)
    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.state.eq(3)
    yield from player.zone_edge_0.write(zone_edges[0])
    yield from player.zone_edge_1.write(zone_edges[1])
    yield from player.zone_edge_2.write(zone_edges[2])
    yield from player.ff_direction_0.write(-1)
    yield from player.ff_direction_1.write(1)

    N_runs = 0
    while True:
        state = yield player.state
        counter = yield player.counter

        """if counter == 0:
            l.reset()"""

        current = yield player.value
        l.set_current(current)
        frequency = l.frequency
        yield player.error_signal.eq(l.get_error_signal(counter))
        l.next_tick()
        yield


        if state == STATE_REPLAY_RECORD_COUNT:
            if counter == 0:
                frequencies = []

            frequencies.append(frequency)

        if state == STATE_REPLAY and counter == 0:
            N_runs += 1
            print('RUN', N_runs)

            if N_runs % 10 == 0:
            #if True:
                step_size = yield player.actual_step_size
                print('step size', step_size)
                ff = []
                es = []
                for point in range(N_points):
                    ff_i = yield player.feedforward[point]
                    ff.append(convert_number(ff_i, N_bits))
                    es_i = yield player.recorded_error_signal[point]
                    es.append(convert_number(es_i, 2))

                log_data.append({
                    'N': N_runs,
                    'feed_forward': ff,
                    'error_signal': es,
                    'frequencies': frequencies
                })
                write_log(log_data)

            if N_runs == 50000:
                break
                """ff = []
                es = []
                for point in range(N_points):
                    ff_i = yield player.feedforward[point]
                    ff.append(ff_i)
                    es_i = yield player.recorded_error_signal[point]
                    es.append(convert_number(es_i, 2))

                from matplotlib import pyplot as plt
                plt.plot(ff)
                plt.plot(frequencies)
                plt.plot(es)
                plt.show()"""

        #if N_runs == 1000:
        #    break



N_bits = 14
#N_points =16384
N_points = 1024
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, testbench(player, N_bits, N_points))#, vcd_name="laser_control.vcd")
