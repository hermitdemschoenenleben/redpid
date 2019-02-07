import json
import numpy as np

from time import sleep
from matplotlib import pyplot as plt

from utils import do, copy_file, \
    counter_measurement, \
    acquire, get_shifted, save_osci, replay_pyrpl, REPLAY_SHIFT
from process_control import process_control_data, replay_remote
from registers import Pitaya


DECIMATION = 1
DURATION = 131.072e-6 * DECIMATION
# FREQUENCY_MULTIPLIER is not tested!
FREQUENCY_MULTIPLIER = 1
LENGTH = 16384
assert LENGTH % FREQUENCY_MULTIPLIER == 0
N_REPETITIONS = 1


PROPORTIONAL = {
    0: -1000,
    1: -1000,
    30: -200,
    35: -100
}


def fine_lock_and_save_osci(name):
    print('saving osci')
    set_proportional(-10)
    sleep(1)
    try:
        save_osci(name)
    except:
        print('Exception at saving osci!!')
    set_proportional(last_proportional)
    sleep(.5)


def save_data(raw_datas, datas):
    with open('control_history.json', 'w') as f:
        json.dump({
            'raw': raw_datas,
            'data': datas
        }, f)


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()
    rp.write_registers()

    N_points = 16384
    N_bits = 14
    rp.pitaya.set('fast_a_sequence_player_enabled', 0)

    """rp.set_feed_forward([
        i - 8192
        for i in range(16384)
    ], N_bits)"""
    rp.set_feed_forward(
        ([-8191] * 4096) \
        + ([-7000] * 4096) \
        + ([-1] * 4096) \
        + ([8191] * 4096),
        N_bits
    )
    rp.sync()

    rp.start_clock(N_points, .5)

    rp.pitaya.set('fast_a_sequence_player_enabled', 1)
    rp.pitaya.set('fast_b_sequence_player_enabled', 1)

    rp.pitaya.set('root_sync_sequences_en', 1)
    rp.pitaya.set('root_sync_sequences_en', 0)


    from matplotlib import pyplot as plt
    data = rp.record_control()
    plt.plot(data)
    plt.show()

    for i in range(5):
        print('I', i)
        data = rp.record_control()
        plt.plot(data)
        rp.set_feed_forward(data, N_bits)

    plt.show()
    asd

    datas = []
    raw_datas = []
    last_proportional = 0

    for i in range(38):
        if i in PROPORTIONAL:
            rp.set_proportional(PROPORTIONAL[i])
            last_proportional = PROPORTIONAL[i]

        print('---- I=%d ----' % i)
        #remote('reset_int.py 0', measure_rp)
        #remote('reset_int.py', measure_rp)
        #sleep(.5)

        if i == 0:
            input('ok?')

        if False:
            fine_lock_and_save_osci(str(i))

        data = rp.record_control()
        raw_datas.append(data)

        with open('control_raw.json', 'w') as f:
            json.dump({
                'frequency_multiplier': FREQUENCY_MULTIPLIER,
                'duration': DURATION,
                'data': list(data),
                'decimation': DECIMATION
            }, f)

        print('process')
        processed_data = process_control_data(combine=(i>15))
        datas.append(processed_data)
        save_data(raw_datas, datas)

        print('replay')
        #plt.plot(get_shifted(processed_data, REPLAY_SHIFT))
        #plt.show()
        remote('reset_int.py 1', measure_rp)
        replay_pyrpl(r, get_shifted(processed_data, int(REPLAY_SHIFT/DECIMATION)), decimation=DECIMATION)

        #copy_pid(False)

    for i, d in enumerate(datas):
        #if i >= 12 and i % 3 == 0:
        print('PLOT ALL DATA!')
        #if True:
        if i % 5 == 0 or i in [29,30,31,32,33]:
            #plt.plot(x_axis, d, label=str(i))
            plt.plot(d, label=str(i))
            plt.legend()

    plt.savefig('control.svg')

    remote('reset_int.py 1', measure_rp)
    sleep(2)
    remote('reset_int.py 0', measure_rp)
    sleep(1)
    fine_lock_and_save_osci('end')
    set_proportional(-10)

    plt.grid()
    plt.show()