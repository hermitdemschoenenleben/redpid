import numpy as np
import pickle

from time import sleep
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH
from registers import Pitaya


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    #rp.enable_channel_b_pid(True, p=100, i=0, d=0, reset=False)
    #asd
    #asd
    decimation = 3

    datas = []

    delays = list(int(_) for _ in np.arange(50, 15001, 50))

    decimation = 5
    max_state = 4
    N_states = max_state + 1

    for delay in delays:
        rp.init(
            decimation=decimation,
            N_zones=2,
            relative_length=1 / (2**decimation),
            zone_edges=[.5, 1, None],
            target_frequencies=[6000, 150, None, None],
            curvature_filtering_starts=[15, 15, None, None]
        )

        rp.pitaya.set('ttl_ttl0_start', delay * 16384 * N_states)
        rp.pitaya.set('ttl_ttl0_end', N_states * delay * 16384 + (16384*7000*2))
        rp.pitaya.set('gpio_n_do4_en', rp.pitaya.states('ttl_ttl0_out'))

        actual_length = int(LENGTH / (2**decimation))
        rp.set_max_state(4)

        print('delay', delay)

        rp.set_algorithm(0)
        rp.set_enabled(0)

        first_feed_forward = np.array([0] * actual_length)
        rp.set_feed_forward(first_feed_forward)
        rp.sync()
        rp.enable_channel_b_pid(False, reset=True)
        #rp.enable_channel_b_pid(True, p=100, i=2, d=0, reset=False)

        rp.schedule_recording_after(delay)


        #asd

        #sleep(20)
        arm_osci()
        #continue

        rp.set_enabled(1)
        rp.set_algorithm(1)

        save_osci('development_%d' % delay)

        #asd

        d = rp.read_control_signal(addresses=list(range(actual_length)))
        datas.append(d)
        #plt.plot(d, label=str(delay))
        #plt.show()

        with open('run.pickle', 'wb') as f:
            pickle.dump({
                'delays': delays,
                'control_signals': datas
            }, f)

        sleep(1)

    #plt.legend()
    #plt.show()
