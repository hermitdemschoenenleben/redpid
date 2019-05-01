import pickle
import numpy as np

from time import time, sleep
from gain_camera.utils import img2count, crop_imgs
from gain_camera.connection import Connection
from matplotlib import pyplot as plt
from multiprocessing import Process, Pipe
from utils import N_BITS, LENGTH, MAX_STATE, N_STATES, ONE_ITERATION, ITERATIONS_PER_SECOND, \
    ONE_SECOND, ONE_MS, COOLING_PIN, CAM_TRIG_PIN, REPUMPING_PIN, END_DELAY, \
    AGILENT_NANOSPEED_PIN


def start_acquisition_process():
    pipe, child_pipe = Pipe()

    acquiry_process = Process(target=record_afmot_loading_new_style, args=(child_pipe,))
    acquiry_process.start()

    # wait until acquiry process is ready
    pipe.recv()
    print('child is ready!')

    return acquiry_process, pipe


def program_new_style_detection(
        rp, init_ttl, mot_loading_time, states, freq_correction=1,
        absorption_detection=False
    ):
    ONE_MS_CORRECTED = ONE_MS
    ONE_ITERATION_CORRECTED = ONE_ITERATION * freq_correction
    ONE_SECOND_CORRECTED = ONE_SECOND
    END_DELAY_CORRECTED = END_DELAY

    repumping_delay = .1 * ONE_MS_CORRECTED
    repumping_time = .1 * ONE_MS_CORRECTED
    nanospeed_after = (repumping_delay + repumping_time)
    if not absorption_detection:
        # we shouldn't do it too early because it may the PID 1ms 
        # to take over from AF-MOT operation
        camera_trigger_after = 1 * ONE_MS_CORRECTED
        cooling_again_after = 1.05 * ONE_MS_CORRECTED
    else:
        camera_trigger_after = int(nanospeed_after + (0.05 * ONE_MS_CORRECTED))
        cooling_again_after = 100 * ONE_MS_CORRECTED

    # record background image
    nanospeed_trigger_0 = int(nanospeed_after)
    camera_trigger_0 = int(camera_trigger_after)

    pid_on = int(mot_loading_time * ONE_ITERATION_CORRECTED)
    pid_off = int(pid_on + END_DELAY_CORRECTED)

    afmot_detection = pid_on
    mot_detection = int(afmot_detection + (mot_loading_time * ONE_ITERATION_CORRECTED))

    # AF-MOT detection

    cooling_off = afmot_detection
    cooling_on_again = int(afmot_detection + cooling_again_after)

    repumping_on = int(afmot_detection + repumping_delay)
    repumping_off = int(repumping_on + repumping_time)

    camera_trigger_1 = int(afmot_detection + camera_trigger_after)
    nanospeed_trigger_1 = int(afmot_detection + nanospeed_after)

    # MOT detection

    mot_start = afmot_detection + ONE_SECOND_CORRECTED

    cooling_off_again = mot_detection
    cooling_last_time = int(mot_detection + cooling_again_after)

    repumping_on_again = int(mot_start + repumping_delay)
    repumping_off_again = int(mot_detection + repumping_time)

    # this is after detection, just for checking how the MOT looks like
    final_repumping = int(mot_detection + ONE_SECOND_CORRECTED)
    final_repumping_end = int(final_repumping + END_DELAY_CORRECTED)

    camera_trigger_2 = int(mot_detection + camera_trigger_after)
    nanospeed_trigger_2 = int(mot_detection + nanospeed_after)

    # TTL1: turn off cooling laser (it's inverse!)
    # do3_en (Kanal 4) ist cooling laser
    init_ttl(2, cooling_off, cooling_on_again)
    init_ttl(3, cooling_off_again, cooling_last_time)
    rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out', 'ttl_ttl3_out'))

    # TTL2: turn on repumping laser
    # do5_en (Kanal 6) ist repumper!
    init_ttl(4, repumping_on, repumping_off)
    init_ttl(7, repumping_on_again, repumping_off_again)
    init_ttl(8, final_repumping, final_repumping_end)
    rp.pitaya.set(REPUMPING_PIN, states(
        'ttl_ttl4_out', 'ttl_ttl7_out', 'ttl_ttl8_out'
    ))

    # TTL4: trigger camera
    # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
    init_ttl(11, int(camera_trigger_0), int(camera_trigger_0 + ONE_SECOND_CORRECTED))
    init_ttl(5, int(camera_trigger_1), int(camera_trigger_1 + ONE_SECOND_CORRECTED))
    init_ttl(6, int(camera_trigger_2), int(camera_trigger_2 + ONE_SECOND_CORRECTED))
    cam_trig_ttl = states('ttl_ttl5_out', 'ttl_ttl6_out', 'ttl_ttl11_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    # Agilent
    init_ttl(10, int(nanospeed_trigger_0), int(nanospeed_trigger_0 + ONE_SECOND_CORRECTED))
    init_ttl(1, int(nanospeed_trigger_1), int(nanospeed_trigger_1 + ONE_SECOND_CORRECTED))
    init_ttl(9, int(nanospeed_trigger_2), int(nanospeed_trigger_2 + ONE_SECOND_CORRECTED))
    nanospeed_ttl = states('ttl_ttl1_out', 'ttl_ttl9_out', 'ttl_ttl10_out')
    rp.pitaya.set(AGILENT_NANOSPEED_PIN, nanospeed_ttl)

    return pid_on, pid_off, cam_trig_ttl, nanospeed_ttl


def program_new_style_detection_aom(rp, init_ttl, mot_loading_time, states, freq_correction):
    nicht_auf_neustem_stand()
    ONE_MS_CORRECTED = ONE_MS
    ONE_ITERATION_CORRECTED = ONE_ITERATION * freq_correction
    ONE_SECOND_CORRECTED = ONE_SECOND
    END_DELAY_CORRECTED = END_DELAY

    repumping_time = 1 * ONE_MS_CORRECTED
    cooling_again_after = 1.3 * ONE_MS_CORRECTED
    camera_trigger_after = 1.25 * ONE_MS_CORRECTED

    # we want to be always locked to the cooling transition
    pid_on = 0
    pid_off = int(pid_on + END_DELAY_CORRECTED)

    afmot_detection = int(mot_loading_time * ONE_ITERATION_CORRECTED)
    mot_detection = int(afmot_detection + (mot_loading_time * ONE_ITERATION_CORRECTED))

    # AF-MOT detection

    cooling_off = afmot_detection
    cooling_on_again = int(afmot_detection + cooling_again_after)

    repumping_on = afmot_detection
    repumping_off = int(repumping_on + repumping_time)

    camera_trigger_1 = int(afmot_detection + camera_trigger_after)

    # MOT detection

    mot_start = afmot_detection + ONE_SECOND_CORRECTED

    cooling_off_again = mot_detection
    cooling_last_time = int(mot_detection + cooling_again_after)
    cooling_last_time_end = int(cooling_last_time + END_DELAY_CORRECTED)

    repumping_on_again = int(mot_start)
    repumping_off_again = int(mot_detection + repumping_time)

    # this is after detection, just for checking how the MOT looks like
    final_repumping = int(mot_detection + ONE_SECOND_CORRECTED)
    final_repumping_end = int(final_repumping + END_DELAY_CORRECTED)

    camera_trigger_2 = int(mot_detection + camera_trigger_after)

    # TTL1: turn on cooling laser
    # do3_en (Kanal 4) ist cooling laser
    init_ttl(2, cooling_on_again, cooling_off_again)
    init_ttl(3, cooling_last_time, cooling_last_time_end)

    rp.pitaya.set(COOLING_PIN, states(
        'control_loop_clock_2', 'ttl_ttl2_out', 'ttl_ttl3_out'
    ))

    # TTL2: turn on repumping laser
    # do5_en (Kanal 6) ist repumper!
    init_ttl(4, repumping_on, repumping_off)
    init_ttl(7, repumping_on_again, repumping_off_again)
    init_ttl(8, final_repumping, final_repumping_end)
    rp.pitaya.set(REPUMPING_PIN, states(
        'control_loop_clock_0', 'ttl_ttl4_out', 'ttl_ttl7_out', 'ttl_ttl8_out'
    ))

    # TTL4: trigger camera
    # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
    init_ttl(5, int(camera_trigger_1), int(camera_trigger_1 + ONE_SECOND_CORRECTED))
    init_ttl(6, int(camera_trigger_2), int(camera_trigger_2 + ONE_SECOND_CORRECTED))
    cam_trig_ttl = states('ttl_ttl5_out', 'ttl_ttl6_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    return pid_on, pid_off, cam_trig_ttl


def do_new_style_detection(rp, cam_trig_ttl, nanospeed_ttl, pipe):
    sleep(1)
    # now, internal FPGA should control the camera trigger
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)
    rp.pitaya.set(AGILENT_NANOSPEED_PIN, nanospeed_ttl)

    # everything is controlled by FPGA, we don't have to do anything
    data = pickle.loads(pipe.recv())
    return data


def record_afmot_loading_new_style(pipe=None):
    c = Connection()
    c.connect()
    exposure = -11
    c.set_exposure_time(exposure)
    c.enable_trigger(True)
    c.run_continuous_acquisition()

    d = {}

    def wait_for_frame():
        while True:
            c.parameters.call_listeners(no_timer=True)

            if c.image_data is not None:
                image_data = c.image_data
                c.image_data = None
                return time(), image_data

    c.parameters.call_listeners(no_timer=True)
    sleep(1)
    c.parameters.call_listeners(no_timer=True)
    # reset image data
    c.image_data = None

    # tell the main thread that we're ready
    pipe.send(True)

    start_time = time()

    background_time, background = wait_for_frame()
    print('bg image at', background_time - start_time)

    afmot_time, afmot = wait_for_frame()
    print('recorded afmot image at', afmot_time - start_time)
    assert afmot_time - start_time > 10

    mot_time, mot = wait_for_frame()
    print('recorded mot image at', mot_time - start_time)
    assert mot_time - afmot_time > 10

    d['img_background'] = crop_imgs(background)
    d['img_afmot'] = crop_imgs(afmot)
    d['img_mot'] = crop_imgs(mot)

    for key, imgs in (('N_background', background), ('N_afmot', afmot), ('N_mot', mot)):
        atom_number = np.mean(
            [img2count(img, exposure) for img in imgs]
        )
        d[key] = atom_number

    """plt.pcolormesh(d['img_background'][0])
    plt.show()
    plt.pcolormesh(d['img_afmot'][0])
    plt.show()
    plt.pcolormesh(d['img_mot'][0])
    plt.show()"""
    #plt.plot([_['N_afmot'] for _ in data])
    #plt.plot([_['N_mot'] for _ in data])
    #plt.grid()
    #plt.show()

    print('ratio', (d['N_afmot'] - d['N_background']) / (d['N_mot'] - d['N_background']))

    if pipe is not None:
        pipe.send(pickle.dumps(d))

    return d
