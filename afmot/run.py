import json
import numpy as np

from time import sleep
from matplotlib import pyplot as plt

from utils import do, copy_file, counter_measurement, save_osci, \
    REPLAY_SHIFT, N_BITS, LENGTH
from registers import Pitaya
from process_control import process_control_data


DECIMATION = 1
DURATION = 131.072e-6 * DECIMATION
# FREQUENCY_MULTIPLIER is not tested!
FREQUENCY_MULTIPLIER = 1
assert LENGTH % FREQUENCY_MULTIPLIER == 0


PROPORTIONAL = {
    0: 0.5,
    5: .2,
    7: .1,
    9: .025,
    10: .01
}


def save_data(control_data, error_data):
    with open(fn, 'w') as f:
        json.dump({
            'frequency_multiplier': FREQUENCY_MULTIPLIER,
            'duration': DURATION,
            'data': list(int(v) for v in control_data),
            'error_signal': list(int(v) for v in error_data),
            'decimation': DECIMATION
        }, f)


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()
    rp.write_registers()

    datas = []

    #rp.pitaya.set('control_loop_brk', 0)
    #rp.parameters['p'] = .01
    #rp.write_registers()
    #asd

    #for wait in (2, 2.5, 3, 3.5, 4, 4.5, 5):
    for wait in (3.5, 4.5, 5.5, 6.5):
        print('wait', wait)

        rp.pitaya.set('control_loop_sequence_player_run_algorithm', 0)
        rp.pitaya.set('control_loop_sequence_player_enabled', 0)

        first_feed_forward = np.array([0] * LENGTH)
        #rp.set_feed_forward(first_feed_forward, N_BITS)

        rp.sync()

        rp.start_clock(LENGTH, .5, 1, None)
        print('remove')
        rp.pitaya.set('control_loop_dy_sel', rp.pitaya.signal('zero'))
        #asd

        rp.pitaya.set('control_loop_sequence_player_max_status', 50)

        rp.pitaya.set('control_loop_sequence_player_enabled', 1)
        rp.pitaya.set('control_loop_sequence_player_keep_constant_at_end', 0)
        rp.pitaya.set('control_loop_sequence_player_run_algorithm', 1)
        sleep(100)

        #rp.pitaya.set('root_sync_sequences_en', 1)
        #rp.pitaya.set('root_sync_sequences_en', 0)
        sleep(wait)
        d = rp.record_control()
        datas.append(d)
        plt.plot(d, label=wait)

    plt.legend()
    plt.show()

    datas = []
    raw_control_datas = []
    endAlgorithm()

    for i in range(11):
        if i in PROPORTIONAL:
            rp.set_proportional(PROPORTIONAL[i])

        rp.sync()

        print('---- I=%d ----' % i)

        control_data = rp.record_control()
        raw_control_datas.append(control_data)
        error_signal = rp.record_error_signal()

        for fn in ('control_raw.json', 'control_raw_%d.json' % i):
            save_data(control_data, error_signal)

        processed_data = [
            int(_) for _ in process_control_data(plot=True, combine=True)
        ]
        datas.append(processed_data)

        rp.set_feed_forward(
            processed_data, N_BITS
        )

    for i, d in enumerate(datas):
        plt.plot(d, label=str(i))
        plt.legend()

    plt.grid()
    plt.show()