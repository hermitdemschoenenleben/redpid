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
    new_style_record_background, program_new_style_detection_aom


FOLDER = '/media/depot/data/fake-afmot/atom-numbers/'
FILENAME = 'test.pickle'
TARGET_FREQUENCY = BASE_FREQ
TUNING_TIME = 10e-6
TUNING_TIME = 1e-6

assert TUNING_TIME > 0, 'for some reason it may not be 0 --> DEBUG!'

DECIMATION = 0
RELATIVE_LENGTH = 1
current_freq = lambda: BASE_FREQ / (2**DECIMATION) / RELATIVE_LENGTH
# determine decimation
while current_freq() > TARGET_FREQUENCY:
    DECIMATION += 1

# determine relative length
RELATIVE_LENGTH = current_freq() / TARGET_FREQUENCY
RELATIVE_TUNING_TIME = TUNING_TIME * TARGET_FREQUENCY

print(DECIMATION, RELATIVE_LENGTH)
MOT_LOADING_TIME = int(1 * BASE_FREQ / N_STATES / RELATIVE_LENGTH)
OLD_STYLE_DETECTION = False


if __name__ == '__main__':
        all_data = load_old_data(FOLDER, FILENAME)
        #cooling_duty_cycles = [.05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9, .95]
        cooling_duty_cycles = [.5, .7]
        for cooling_duty_cycle in cooling_duty_cycles:
            print('----         DUTY CYCLE %.2f        ----' % cooling_duty_cycle)

            for iteration in range(1):
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
                    N_zones=4,
                    relative_length=RELATIVE_LENGTH,
                    zone_edges=[
                        1 - cooling_duty_cycle - RELATIVE_TUNING_TIME,
                        1 - cooling_duty_cycle,
                        1 - RELATIVE_TUNING_TIME
                    ],
                    target_frequencies=[1,1,1,1]
                    #curvature_filtering_starts=[16383, 16383, 16383, 16383]
                )

                rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

                # we always want to use the reference frequency corresponding to cooling
                rp.pitaya.set('gpio_n_do0_en', null)
                rp.pitaya.set('gpio_n_do1_en', force)

                pid_on, pid_off, cam_trig_ttl = program_new_style_detection_aom(
                    rp, init_ttl, MOT_LOADING_TIME, states,
                    BASE_FREQ / TARGET_FREQUENCY
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

                # TTL5: announcer
                # do2 (Kanal 3) ist announcer
                init_ttl(1, int(pid_on - ONE_MS), int(pid_on - ONE_MS + ONE_SECOND))
                rp.pitaya.set('gpio_n_do2_en', states('ttl_ttl1_out'))

                rp.enable_channel_b_pid(True, p=200, i=25, d=0, reset=False)

                rp.set_max_state(MAX_STATE)
                rp.set_algorithm(0)
                rp.set_enabled(0)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

                # ---------------------------- START ALGORITHM ----------------------------
                acquiry_process, pipe = start_acquisition_process(old_style=False)

                new_style_record_background(rp, force, null)

                rp.set_enabled(1)
                rp.set_algorithm(1)
                rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

                data = do_new_style_detection(rp, cam_trig_ttl, pipe)

                iteration_data = all_data.get(cooling_duty_cycle, [])
                iteration_data.append(data)
                all_data[cooling_duty_cycle] = iteration_data

                with open(FOLDER + FILENAME, 'wb') as f:
                    pickle.dump(all_data, f)