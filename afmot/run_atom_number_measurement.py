import numpy as np
import pickle

from time import sleep, time
from matplotlib import pyplot as plt
from devices import connect_to_device_service

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH, \
    reset_fpga, MAX_STATE, N_STATES, ONE_ITERATION, ITERATIONS_PER_SECOND, \
    ONE_SECOND, ONE_MS, COOLING_PIN, CAM_TRIG_PIN, REPUMPING_PIN, END_DELAY, \
    load_old_data, BASE_FREQ
from registers import Pitaya
from record_afmot_loading import start_acquisition_process, program_old_style_detection, \
    do_old_style_detection, program_new_style_detection, do_new_style_detection, \
    new_style_record_background


FOLDER = '/media/depot/data/afmot/atom-numbers/'
FILENAME = 'test.pickle'
OLD_STYLE_DETECTION = False
DECIMATION = 5
RELATIVE_LENGTH = 1 / (2**DECIMATION)
CURRENT_BEGIN = 130
MIN_CURRENT = 121.5
MAX_CURRENT = 150
CURRENT_STEP = 2
DETERMINE_CURRENTS = False
MOT_LOADING_TIME = int(30 * BASE_FREQ / N_STATES)


def analyze_tuning_time(data, start, stop, tuning_value):
    tuning_found = False

    idx = start

    while idx < stop:
        idx += 1
        val = data[idx]

        if val == tuning_value:
            tuning_found = True

        if val != tuning_value and tuning_found:
            break

    if idx == stop:
        # never reached...
        return 100000

    return idx - start


def determine_tuning_time_balance(rp, cooling_light_duty_cycle):
    #rp.record_now()
    #rp.set_max_state(0)
    #rp.set_enabled(0)
    rp.set_algorithm(0)
    #sleep(1)
    datas = []

    addresses = list(range(int(rp.N_points * RELATIVE_LENGTH) - 1))

    cooling_data = []
    repumping_data = []

    for i in range(20):
        data = rp.read_error_signal(addresses=addresses)
        data[data == 3] = 0
        rp.set_algorithm(1)
        sleep(.1)
        rp.set_algorithm(0)
        #data = rp.read_control_signal(addresses=addresses)

        mean_data = data
        """mean_data = []
        for idx in range(int(rp.N_points / 3)):
            try:
                mean_data.append(
                    int(np.mean([data[3*idx], data[3*idx+1], data[3*idx+2]]))
                )
            except IndexError:
                pass
        """
        datas.append(mean_data)

        repumping_end_idx = int(np.floor((1 - cooling_light_duty_cycle) * len(mean_data)))
        cooling_start_idx = int(np.ceil((1 - cooling_light_duty_cycle) * len(mean_data)))
        #print('cooling_start_idx', cooling_start_idx)
        repumping_tuning_time, cooling_tuning_time = (
            # repumping
            analyze_tuning_time(mean_data, 0, repumping_end_idx, 0),
            # cooling
            analyze_tuning_time(mean_data, cooling_start_idx, len(mean_data) - 1, 1)
        )

        cooling_data.append(cooling_tuning_time)
        repumping_data.append(repumping_tuning_time)

    #for data in datas[-5:]:
    #    plt.plot(data)
    """plt.plot(datas[0])
    plt.plot(datas[-2])
    plt.plot(datas[-1])

    plt.show()"""

    repumping_tuning_time = np.min(repumping_data)
    cooling_tuning_time = np.min(cooling_tuning_time)

    print('repumping', repumping_tuning_time, 'cooling', cooling_tuning_time)

    if repumping_tuning_time == cooling_tuning_time:
        return 0

    tuning_direction = -1 if repumping_tuning_time > cooling_tuning_time \
        else 1

    print('tuning direction', tuning_direction)

    return tuning_direction


if __name__ == '__main__':
    #_ilx = connect_to_device_service('141.20.47.56', 'ilx')
    def set_current(current):
        print('dont set current!!')
        return
        assert current >= MIN_CURRENT
        assert current <= MAX_CURRENT
        print('set laser current', current)
        _ilx.root.set_laser_current(current)
        sleep(1)

    if DETERMINE_CURRENTS:

        last_current = float(MAX_CURRENT)
        currents = []

        #for cooling_duty_cycle in [.1, .2, .3, .4, .5, .6, .7, .8, .9]:
        for cooling_duty_cycle in np.arange(0.25, 0.95, 0.025):
        #for cooling_duty_cycle in [.5]:
            print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)
            print('currents', currents)

            did_turn = False
            current_before = last_current

            while True:
                reset_fpga('rp-f012ba.local', 'root', 'zeilinger')
                rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
                rp.connect()

                rp.init(
                    decimation=DECIMATION,
                    N_zones=2,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[1-cooling_duty_cycle, 1, None],
                    target_frequencies=[6000, 150, None, None],
                    curvature_filtering_starts=[15, 15, None, None]
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )
                rp.set_max_state(MAX_STATE)

                rp.pitaya.set('control_loop_sequence_player_step_size', 8)
                rp.pitaya.set('control_loop_sequence_player_decrease_step_size_after', 1000)

                set_current(CURRENT_BEGIN)
                sleep(1)
                set_current(last_current)
                sleep(1)

                rp.set_enabled(1)
                rp.set_algorithm(1)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

                sleep(10)
                tuning_direction = determine_tuning_time_balance(rp, cooling_duty_cycle)

                rp.set_enabled(0)
                rp.set_algorithm(0)

                if tuning_direction == 0:
                    last_current = last_current
                    currents.append(last_current)
                    break
                elif tuning_direction == -1:
                    if did_turn:
                        last_current -= float(CURRENT_STEP) / 8
                        set_current(last_current)
                        currents.append(last_current)
                        break

                    last_current -= float(CURRENT_STEP)

                    if last_current < MIN_CURRENT:
                        last_current = MIN_CURRENT
                        set_current(last_current)
                        currents.append(last_current)
                        break
                    else:
                        set_current(last_current)
                        continue
                else:
                    if not did_turn:
                        did_turn = True

                    if last_current < current_before:
                        last_current += float(CURRENT_STEP) / 4
                        set_current(last_current)
                        continue
                    else:
                        currents.append(last_current)
                        break

    else:
        all_data = load_old_data(FOLDER, FILENAME)
        #currents = [134.75, 134.75, 132.5, 130.75, 130.75, 130.5, 129.5, 128.5, 128.5, 126.5, 123, 123, 123, 123, 123, 123]
        #cooling_duty_cycles = [.15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9]
        #currents = [130.75, 130.75, 130.5, 129.5, 128.5, 128.5, 126.5, 123, 123, 123, 123, 123, 123, 123]
        #cooling_duty_cycles = [.3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9, .95]
        currents = [133.25, 133.25, 132.25, 132.25, 132.25, 132.25, 132.0, 130.25, 130.25, 130.25, 129.5, 129.0, 128.75, 128.75, 126.5, 126.5, 125.75, 124.5, 123.5, 123.5, 121.75, 121.75, 121.5, 121.5, 121.5, 121.5, 121.5]
        #cooling_duty_cycles = np.arange(0.25, 0.95, 0.025)
        cooling_duty_cycles = [.8]
        #    for duty_cycle in [.4, .5, .6, .7, .8, .85, .9, .95]:
        it = 0
        for current, cooling_duty_cycle in zip(currents, cooling_duty_cycles):
            print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)

            for iteration in range(2):
                print('----         ITERATION %d        ----' % iteration)

                reset_fpga('rp-f012ba.local', 'root', 'zeilinger')
                rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
                rp.connect()

                states = lambda *names: rp.pitaya.states(*names)
                force = states('force')
                null = states()

                _initialized_ttl = []
                def init_ttl(idx, start, stop):
                    assert idx not in _initialized_ttl, 'ttl already initialized'
                    _initialized_ttl.append(idx)
                    rp.pitaya.set('ttl_ttl%d_start' % idx, start)
                    rp.pitaya.set('ttl_ttl%d_end' % idx,  stop)

                rp.init(
                    decimation=DECIMATION,
                    N_zones=2,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[1-cooling_duty_cycle, 1, None],
                    target_frequencies=[6000, 150, None, None],
                    curvature_filtering_starts=[15, 15, None, None]
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )

                set_current(CURRENT_BEGIN)
                sleep(1)
                set_current(current)

                rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

                if OLD_STYLE_DETECTION:
                    pid_on, pid_off, cam_trig_ttl = program_old_style_detection(
                        rp, init_ttl, MOT_LOADING_TIME, states
                    )
                else:
                    pid_on, pid_off, cam_trig_ttl, nanospeed_ttl = program_new_style_detection(
                        rp, init_ttl, MOT_LOADING_TIME, states
                    )

                rp.pitaya.set(
                    'control_loop_sequence_player_stop_algorithm_after',
                    MOT_LOADING_TIME-1
                )
                rp.pitaya.set(
                    'control_loop_sequence_player_stop_after',
                    MOT_LOADING_TIME-1
                )

                # TTL0: enable PID
                init_ttl(0, pid_on, pid_off)
                rp.pitaya.set('control_loop_pid_enable_en', states('ttl_ttl0_out'))

                rp.enable_channel_b_pid(True, p=200, i=25, d=0, reset=False)

                rp.set_max_state(MAX_STATE)
                rp.pitaya.set('control_loop_sequence_player_step_size', 8)
                rp.pitaya.set('control_loop_sequence_player_decrease_step_size_after', 1000)

                rp.set_algorithm(0)
                rp.set_enabled(0)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

                #actual_length = int(LENGTH  * RELATIVE_LENGTH)
                #first_feed_forward = np.array([0] * actual_length)
                #rp.set_feed_forward(first_feed_forward)
                rp.sync()

                # ---------------------------- START ALGORITHM ----------------------------
                #if iteration == 0:
                #    input('ready?')

                if True:
                    rp.set_enabled(1)
                    rp.set_algorithm(1)
                    rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)
                    io

                acquiry_process, pipe = start_acquisition_process(old_style=OLD_STYLE_DETECTION)

                if not OLD_STYLE_DETECTION:
                    new_style_record_background(rp, force, null)

                rp.set_enabled(1)
                rp.set_algorithm(1)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

                if OLD_STYLE_DETECTION:
                    data = do_old_style_detection(rp, force, null, cam_trig_ttl, MOT_LOADING_TIME)
                else:
                    data = do_new_style_detection(rp, cam_trig_ttl, nanospeed_ttl, pipe)

                asd

                iteration_data = all_data.get(cooling_duty_cycle, [])
                iteration_data.append(data)
                all_data[cooling_duty_cycle] = iteration_data

                with open(FOLDER + FILENAME, 'wb') as f:
                    pickle.dump(all_data, f)