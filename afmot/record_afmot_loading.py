import pickle
import numpy as np

from time import time, sleep
from gain_camera.utils import img2count, crop_imgs
from gain_camera.connection import Connection
from matplotlib import pyplot as plt
from multiprocessing import Process, Pipe
from utils import N_BITS, LENGTH, MAX_STATE, N_STATES, ONE_ITERATION, ITERATIONS_PER_SECOND, \
    ONE_SECOND, ONE_MS, COOLING_PIN, CAM_TRIG_PIN, REPUMPING_PIN, END_DELAY


def start_acquisition_process(old_style=False):
    pipe, child_pipe = Pipe()

    if old_style:
        acquiry_process = Process(target=record_afmot_loading_old_style, args=(child_pipe,))
    else:
        acquiry_process = Process(target=record_afmot_loading_new_style, args=(child_pipe,))

    acquiry_process.start()

    # wait until acquiry process is ready
    pipe.recv()
    print('child is ready!')

    return acquiry_process, pipe


def program_old_style_detection(rp, init_ttl, mot_loading_time, states):
    pid_on = int(mot_loading_time * ONE_ITERATION)
    pid_off = int(pid_on + END_DELAY)

    cooling_off = pid_on
    cooling_on_again = int(cooling_off + 2 * ONE_MS)

    repumping_on = cooling_off
    repumping_off = int(repumping_on + 2000 * ONE_SECOND)

    camera_trigger = int(cooling_off + 2 * ONE_MS)

    # TTL1: turn off cooling laser (it's inverse!)
    # do3_en (Kanal 4) ist cooling laser
    init_ttl(2, cooling_off, cooling_on_again)
    rp.pitaya.set(COOLING_PIN, states('ttl_ttl2_out'))

    # TTL2: turn on repumping laser
    # do5_en (Kanal 6) ist repumper!
    init_ttl(3, repumping_on, repumping_off)
    rp.pitaya.set(REPUMPING_PIN, states('ttl_ttl3_out'))

    # TTL4: trigger camera
    # do4_en (Kanal 5) ist cam trigger gpio_n_do4_en
    init_ttl(4, int(camera_trigger), int(camera_trigger + ONE_SECOND))
    cam_trig_ttl = states('ttl_ttl4_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    return pid_on, pid_off, cam_trig_ttl


def do_old_style_detection(rp, force, null, cam_trig_ttl, mot_loading_time):
    # Trigger the cam on repeatedly for recording the AF-MOT loading curve
    start_time = time()
    target_time = mot_loading_time / ITERATIONS_PER_SECOND

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
    sleep(20)

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
    return data


def record_afmot_loading_old_style(pipe=None):
    c = Connection()
    c.connect()
    # important: using -12 or -12 leads to overexposed images for some reason...
    exposure = -11
    c.set_exposure_time(exposure)
    c.enable_trigger(True)
    c.run_continuous_acquisition()

    AFMOT = 0
    MOT = 1

    d = {}
    last_time = time()
    times = []
    atom_numbers = []

    def wait_for_frame():
        while True:
            c.parameters.call_listeners()

            if c.image_data is not None:
                image_data = c.image_data
                c.image_data = None
                return time(), image_data

    for j in [AFMOT, MOT]:
        print('AMOT' if j == AFMOT else 'MOT')
        for img_number in range(10000000):
            print('record image number', img_number, end='\r')

            new_time, imgs = wait_for_frame()
            times.append(new_time)

            atom_number = np.mean(
                [img2count(img, exposure) for img in imgs]
            )
            atom_numbers.append(atom_number)

            if new_time - last_time > 1 and img_number > 0:
                #for img in imgs:
                #    plt.pcolormesh(img)
                #    plt.show()
                if j == AFMOT:
                    d['N_afmot'] = atom_number
                    d['img_afmot_live'] = crop_imgs(last_imgs)
                    d['img_afmot_after'] = crop_imgs(imgs)
                else:
                    d['N_mot'] = atom_number
                    d['img_mot'] = crop_imgs(imgs)

                break

            last_time = new_time
            last_imgs = imgs

    times = [_ - times[0] for _ in times]

    #plt.plot(times, atom_numbers)
    #plt.grid()
    #plt.show()

    d.update({
        'times': times,
        'atom_numbers': atom_numbers,
    })

    #data.append(d)

    #plt.plot([_['N_afmot'] for _ in data])
    #plt.plot([_['N_mot'] for _ in data])
    #plt.grid()
    #plt.show()
    if pipe is not None:
        pipe.send(pickle.dumps(d))

    return d


def program_new_style_detection(rp, init_ttl, mot_loading_time, states):
    repumping_time = 2 * ONE_MS
    cooling_again_after = 3 * ONE_MS
    camera_trigger_after = 2 * ONE_MS

    pid_on = int(mot_loading_time * ONE_ITERATION)
    pid_off = int(pid_on + END_DELAY)

    afmot_detection = pid_on
    mot_detection = int(afmot_detection + (mot_loading_time * ONE_ITERATION))

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

    repumping_on_again = int(mot_start)
    repumping_off_again = int(mot_detection + repumping_time)

    # this is after detection, just for checking how the MOT looks like
    final_repumping = int(mot_detection + ONE_SECOND)
    final_repumping_end = int(final_repumping + END_DELAY)

    camera_trigger_2 = int(mot_detection + camera_trigger_after)

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
    init_ttl(5, int(camera_trigger_1), int(camera_trigger_1 + ONE_SECOND))
    init_ttl(6, int(camera_trigger_2), int(camera_trigger_2 + ONE_SECOND))
    cam_trig_ttl = states('ttl_ttl5_out', 'ttl_ttl6_out')
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    return pid_on, pid_off, cam_trig_ttl


def new_style_record_background(rp, force, null):
    # record one frame for background
    rp.pitaya.set(CAM_TRIG_PIN, force)
    sleep(.05)
    rp.pitaya.set(CAM_TRIG_PIN, null)


def do_new_style_detection(rp, cam_trig_ttl, pipe):
    sleep(1)
    # now, internal FPGA should control the camera trigger
    rp.pitaya.set(CAM_TRIG_PIN, cam_trig_ttl)

    # everything is controlled by FPGA, we don't have to do anything
    data = pickle.loads(pipe.recv())
    return data


def record_afmot_loading_new_style(pipe=None):
    c = Connection()
    c.connect()
    exposure = -8
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

    d['img_background'] = background
    d['img_afmot'] = afmot
    d['img_mot'] = mot

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
