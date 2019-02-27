import numpy as np

from time import sleep
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, N_BITS, LENGTH
from registers import Pitaya


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    #rp.enable_channel_b_pid(True, p=100, i=0, d=0, reset=False)
    #asd
    #asd
    decimation = 3

    datas = []

    delays = [1, 3, 5, 7, 10, 15, 25, 50, 100, 150, 200, 250, 400]

    #for wait in (3.5, 4.5, 5.5, 6.5):
    for decimation in (5,):
        for delay in (15,):
            rp.init(
                decimation=decimation,
                N_zones=2,
                relative_length=1 / (2**decimation),
                zone_edges=[.5, 1, None],
                target_frequencies=[6000, 150, None, None],
                curvature_filtering_starts=[delay, delay, None, None]
            )
            actual_length = int(LENGTH / (2**decimation))
            rp.set_max_state(4)

            print('decimation', decimation, 'delay', delay)

            rp.set_algorithm(0)
            rp.set_enabled(0)

            first_feed_forward = np.array([0] * actual_length)
            rp.set_feed_forward(first_feed_forward)
            rp.sync()
            rp.enable_channel_b_pid(False, reset=True)
            #rp.enable_channel_b_pid(True, p=100, i=2, d=0, reset=False)

            #rp.schedule_recording_after(delay)

            rp.set_enabled(1)
            rp.set_algorithm(1)

            sleep(20)
            #save_osci('decimation_%d_curvdelay_%d' % (decimation, delay))
            #continue

            #asd

            #sleep(delay / 1000)
            rp.record_now()
            sleep(1)
            d = rp.read_control_signal(addresses=list(range(actual_length)))
            datas.append(d)
            plt.plot(d, label=str(delay))
            plt.show()

    plt.legend()
    plt.show()
