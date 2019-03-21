import numpy as np
import pickle

from time import sleep, time
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH
from registers import Pitaya


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    #rp.set_curvature_filtering_starts([10, 15, 10, 10])
    #asd

    decimation = 5
    max_state = 4
    N_states = max_state + 1

    osci_trigger_pin = 'gpio_n_do4_en'
    #rp.pitaya.set(osci_trigger_pin, rp.pitaya.states('force'))
    #sleep(1)
    #rp.pitaya.set(osci_trigger_pin, rp.pitaya.states())
    #ASD
    rp.pitaya.set(osci_trigger_pin, rp.pitaya.states('ttl_ttl0_out'))

    delays = np.arange(0, 16001, 300)
    data = {
        'control_signals': [],
        'delays': delays
    }

    for i, delay in enumerate(delays):
        print('delay', delay)

        extra_factor = 2
        rp.init(
            decimation=decimation,
            N_zones=4,
            relative_length=extra_factor * 1 / (2**decimation),
            zone_edges=[0.25, .5, .75],
            target_frequencies=[6000, 250, 1370, 4000],
            curvature_filtering_starts=[9, 15, 5, 10]
        )

        one_iteration = 16384 * N_states
        iterations_per_second = 7629.394531249999 / N_states
        one_second = one_iteration * iterations_per_second
        one_ms = one_second / 1000

        actual_length = int(extra_factor * LENGTH / (2**decimation))
        rp.set_max_state(max_state)

        rp.set_algorithm(0)
        rp.set_enabled(0)
        rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

        #arm_osci()
        sleep(.1)

        first_feed_forward = np.array([0] * actual_length)
        rp.set_feed_forward(first_feed_forward)
        rp.sync()

        one_iteration = 16384 * N_states
        iterations_per_second = 7629.394531249999 / N_states
        one_second = one_iteration * iterations_per_second

        trigger_start = int(delay * one_iteration)
        rp.pitaya.set('ttl_ttl0_start', trigger_start)
        rp.pitaya.set('ttl_ttl0_end', int(trigger_start + one_second))

        rp.schedule_recording_after(delay)

        rp.set_enabled(1)
        rp.set_algorithm(1)

        rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)
        print('los!')

        sleep(1 + N_states * delay / iterations_per_second)
        print('next!')

        sleep(1000)

        """if i == 0:
            sleep(3)
        else:
            sleep(15)"""

        #
        # control = rp.read_control_signal(list(range(actual_length)))
        #data['control_signals'].append(control)
        #with open('/media/depot/data-2019/afmot/jump-generation-dual-species/control-signal-dual-species.pickle', 'wb') as f:
        #    pickle.dump(data, f)

        #save_osci('%d.csv' % delay)
