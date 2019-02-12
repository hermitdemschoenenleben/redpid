import pickle
from migen import *
from migen.fhdl import verilog
from migen.sim import Simulator
from random import randrange, randint
from misoc.interconnect.csr import CSRStorage

from .feed_forward import FeedForwardPlayer, STATUS_REPLAY, STATUS_REPLAY_RECORD_COUNT


def convert_number(n, N_bits):
    max_pos = (1 << (N_bits - 1)) - 1
    if n > max_pos:
        return n - 2 * (max_pos + 1)
    return n


class Laser:
    def __init__(self, N_points, targets, zone_ends, delay):
        self.N_points = N_points
        self.targets = targets
        self.zone_ends = zone_ends
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
        self.frequency += diff / 1000

    def get_error_signal(self, counter):
        target = None
        for zone, end in enumerate(self.zone_ends):
            if counter < end:
                target = self.targets[zone]
                break

        if target is None:
            target = self.targets[0]

        noise = randint(0, 5) - 2

        return 1 if (self.frequency + noise) < target else -1


def write_log(log):
    with open('log-continuous.pickle', 'wb') as f:
        pickle.dump(log, f)


def testbench(player: FeedForwardPlayer, N_bits: int, N_points: int):
    zone_ends = (511, N_points+1, N_points+1)
    l = Laser(N_points, (100, -100), zone_ends, 10)

    log_data = []

    yield from player.enabled.write(1)
    yield from player.run_algorithm.write(1)
    yield player.status.eq(3)
    yield from player.zone_end_0.write(zone_ends[0])
    yield from player.zone_end_1.write(zone_ends[1])
    yield from player.zone_end_2.write(zone_ends[2])

    N_runs = 0
    while True:
        status = yield player.status
        counter = yield player.counter

        """if counter == 0:
            l.reset()"""

        current = yield player.value
        l.set_current(current)
        frequency = l.frequency
        yield player.error_signal.eq(l.get_error_signal(counter))
        l.next_tick()
        yield


        if status == STATUS_REPLAY_RECORD_COUNT:
            if counter == 0:
                frequencies = []

            frequencies.append(frequency)

        if status == STATUS_REPLAY and counter == 0:
            N_runs += 1
            print('RUN', N_runs)

            if N_runs % 10 == 0:
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

            if N_runs == 3000:
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



N_bits = 9
N_points = 1024
player = FeedForwardPlayer(N_bits, N_points)
run_simulation(player, testbench(player, N_bits, N_points))#, vcd_name="laser_control.vcd")
