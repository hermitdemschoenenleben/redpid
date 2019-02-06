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
    #rp.start_clock(.5)
    #rp.set_feed_forward([0])

    """    from random import randint
    for channel in ('b',):
        rp.pitaya.set('fast_%s_sequence_player_enabled' % channel, 1)

        for i in range((1<<12) - 1):
            print(i)
            i += 1<<12
            rp.pitaya.set('fast_%s_sequence_player_data_addr' % channel, i)
            rp.pitaya.set('fast_%s_sequence_player_data_in' % channel, 8191)
            rp.pitaya.set('fast_%s_sequence_player_data_write' % channel, 1)
            rp.pitaya.set('fast_%s_sequence_player_data_write' % channel, 0)

        rp.pitaya.set('fast_%s_sequence_player_enabled' % channel, 1)

    asd"""

    length = 16381
    rp.start_clock(length, .5)
    asd
    """ff = [0] * length
    rp.set_feed_forward(ff)
    """

    """
    datas = []
    raw_datas = []

    r.scope.decimation = DECIMATION
    r.scope.input1 = 'out1'
    r.scope.input2 = 'out2'

    remote('prepare.py', measure_rp)
    remote('reset_int.py 1', measure_rp)
    sleep(1)

    # this applies decimation
    """
    last_proportional = 0

    for i in range(38):
        if i in PROPORTIONAL:
            rp.set_proportional(PROPORTIONAL[i])
            last_proportional = PROPORTIONAL[i]

        print('---- I=%d ----' % i)
        remote('reset_int.py 0', measure_rp)
        #remote('reset_int.py', measure_rp)
        sleep(.5)

        if i == 0:
            input('ok?')

        if False:
            fine_lock_and_save_osci(str(i))

        x_axis, data = record_control()
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