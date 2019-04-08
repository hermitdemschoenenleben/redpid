import numpy as np
import pickle
import subprocess

from time import sleep, time
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, arm_osci, N_BITS, LENGTH
from registers import Pitaya

from record_afmot_loading import record_afmot_loading_old_style, \
    record_afmot_loading_new_style

from multiprocessing import Process, Pipe

def reset_fpga():
    ssh_cmd='sshpass -p zeilinger ssh root@rp-f012ba.local'
    reset_cmd="/bin/bash /reset.sh"
    p = subprocess.Popen(' '.join([ssh_cmd, reset_cmd]).split(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    p.wait()


COOLING_PIN = 'gpio_n_do3_en'
CAM_TRIG_PIN = 'gpio_n_do4_en'
REPUMPING_PIN = 'gpio_n_do5_en'
FOLDER = '/media/depot/data/afmot/atom-numbers/'
FILENAME = 'test.pickle'
OLD_STYLE_DETECTION = True
DECIMATION = 5
MAX_STATE = 4
N_STATES = MAX_STATE + 1
ONE_ITERATION = 16384 * N_STATES
ITERATIONS_PER_SECOND = 7629.394531249999 / N_STATES
ONE_SECOND = ONE_ITERATION * ITERATIONS_PER_SECOND
ONE_MS = ONE_SECOND / 1000

MOT_LOADING_TIME = int(30 * 2000)
END_DELAY = 2000 * ONE_SECOND

if __name__ == '__main__':
    all_data = []

    #    for duty_cycle in [.4, .5, .6, .7, .8, .85, .9, .95]:
    for duty_cycle in [.8]:
        print('----         DUTY CYCLE %.2f        ----' % duty_cycle)

        iteration_data = []
        all_data.append(iteration_data)

        for iteration in range(3):
            print('----         ITERATION %d        ----' % iteration)

            reset_fpga()
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

            cooling_duty_cycle = duty_cycle

            rp.init(
                decimation=DECIMATION,
                N_zones=2,
                relative_length=1 / (2**DECIMATION),
                zone_edges=[1-cooling_duty_cycle, 1, None],
                target_frequencies=[6000, 150, None, None],
                curvature_filtering_starts=[15, 15, None, None]
                #curvature_filtering_starts=[16383, 16383, 16383, 16383]
            )

            rp.pitaya.set('control_loop_sequence_player_stop_zone', 1)

            if OLD_STYLE_DETECTION:
                pid_on = int(MOT_LOADING_TIME * ONE_ITERATION)
                pid_off = int(pid_on + END_DELAY)

                cooling_off = pid_on
                cooling_on_again = int(cooling_off + 2 * ONE_MS)

                repumping_on = cooling_off
                repumping_off = int(repumping_on + 2000 * ONE_SECOND)

                camera_trigger = int(cooling_off + 2 * ONE_MS)

                # TTL1: turn off cooling laser (it's inverse!)
                # do3_en (Kanal 4) ist cooling laser
                init_ttl(2, cooling_off, cooling_on_again)
                #rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out'))

                # TTL2: turn on repumping laser
                # do5_en (Kanal 6) ist repumper!
                init_ttl(3, repumping_on, repumping_off)
                #rp.pitaya.set(REPUMPING_PIN, states('ttl_ttl3_out'))

                # TTL4: trigger camera
                # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
                init_ttl(4, int(camera_trigger), int(camera_trigger + ONE_SECOND))
                cam_trig_ttl = states('ttl_ttl4_out')
                #rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)
            else:
                repumping_time = 2 * ONE_MS
                cooling_again_after = 3 * ONE_MS
                camera_trigger_after = 2 * ONE_MS

                pid_on = int(MOT_LOADING_TIME * ONE_ITERATION)
                pid_off = int(pid_on + END_DELAY)

                afmot_detection = pid_on
                mot_detection = int(afmot_detection + MOT_LOADING_TIME)

                # AF-MOT detection

                cooling_off = afmot_detection
                cooling_on_again = int(afmot_detection + cooling_again_after)

                repumping_on = afmot_detection
                repumping_off = int(repumping_on + repumping_time)

                camera_trigger_1 = int(afmot_detection + camera_trigger_after)

                # MOT detection

                mot_start = afmot_detection + ONE_SECOND

                cooling_off_again = mot_detection
                cooling_last_time = int(mot_detection + cooling_again_after)

                repumping_on_again = mot_start
                repumping_off_again = int(mot_detection + repumping_time)

                camera_trigger_2 = int(mot_detection + camera_trigger_after)

                # TTL1: turn off cooling laser (it's inverse!)
                # do3_en (Kanal 4) ist cooling laser
                init_ttl(2, cooling_off, cooling_on_again)
                init_ttl(3, cooling_off_again, cooling_last_time)
                rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out', 'ttl_ttl3_out'))

                # TTL2: turn on repumping laser
                # do5_en (Kanal 6) ist repumper!
                init_ttl(4, repumping_on, repumping_off)
                rp.pitaya.set(REPUMPING_PIN, states('ttl_ttl4_out'))

                # TTL4: trigger camera
                # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
                init_ttl(5, int(camera_trigger_1), int(camera_trigger_1 + ONE_SECOND))
                init_ttl(6, int(camera_trigger_2), int(camera_trigger_2 + ONE_SECOND))
                cam_trig_ttl = states('ttl_ttl5_out', 'ttl_ttl6_out')
                rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)


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

            actual_length = int(LENGTH / (2**DECIMATION))
            rp.set_max_state(4)

            rp.set_algorithm(0)
            rp.set_enabled(0)
            rp.pitaya.set('control_loop_sequence_player_start_clocks', 0)

            #first_feed_forward = np.array([0] * actual_length)
            #rp.set_feed_forward(first_feed_forward)
            rp.sync()


            # ---------------------------- START ALGORITHM ----------------------------
            if iteration == 0:
                input('ready?')
            pipe, child_pipe = Pipe()

            if OLD_STYLE_DETECTION:
                acquiry_process = Process(target=record_afmot_loading_old_style, args=(child_pipe,))
            else:
                acquiry_process = Process(target=record_afmot_loading_new_style, args=(child_pipe,))

            acquiry_process.start()
            sleep(2)

            rp.set_enabled(1)
            rp.set_algorithm(1)
            rp.pitaya.set('control_loop_sequence_player_start_clocks', 1)

            if OLD_STYLE_DETECTION:
                # Trigger the cam on repeatedly for recording the AF-MOT loading curve
                start_time = time()
                target_time = MOT_LOADING_TIME / ITERATIONS_PER_SECOND

                # stop the continuous triggering 2 seconds before the AF-MOT atom number
                # is determined
                while time() - start_time < target_time - 5:
                    rp.pitaya.set(CAM_TRIG_PIN, force)
                    sleep(.05)
                    rp.pitaya.set(CAM_TRIG_PIN, null)
                    sleep(.05)

                # now, internal FPGA should control the camera trigger
                rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

                print('waiting 5 seconds')
                sleep(10)

                # record MOT loading curve
                start_time = time()
                while time() - start_time < 30:
                    rp.pitaya.set(CAM_TRIG_PIN, force)
                    sleep(.05)
                    rp.pitaya.set(CAM_TRIG_PIN, null)
                    sleep(.05)

                print('waiting again')
                sleep(1.5)

                rp.pitaya.set(CAM_TRIG_PIN, force)
                sleep(.05)
                rp.pitaya.set(CAM_TRIG_PIN, null)
                sleep(.05)
                data = pickle.loads(pipe.recv())
            else:
                # everything is controlled by FPGA, we don't have to do anything
                data = pickle.loads(pipe.recv())

            #plt.plot(data['times'], data['atom_numbers'])
            #plt.grid()
            #plt.show()

            iteration_data.append(data)

            with open(FOLDER + FILENAME, 'wb') as f:
                pickle.dump(all_data, f)

            asd