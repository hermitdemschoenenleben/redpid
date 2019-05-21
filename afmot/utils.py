import time
import numpy as np
import pickle
import subprocess
from os import path

LENGTH = 16384
N_BITS = 14
MAX_STATE = 4
N_STATES = MAX_STATE + 1
ONE_ITERATION = 16384 * N_STATES
BASE_FREQ = 7629.394531249999
ITERATIONS_PER_SECOND = BASE_FREQ / N_STATES
ONE_SECOND = ONE_ITERATION * ITERATIONS_PER_SECOND
ONE_MS = ONE_SECOND / 1000


def do(cmd):
    subprocess.call(cmd, shell=True)


def copy_file(fn, ip):
    pth = path.join(
        *path.split(path.abspath(__file__))[:-1],
        fn
    )
    do('sshpass -p "root" scp -r %s root@%s:/jumps/' % (pth, ip))


def reset_fpga(host, user, password):
    ssh_cmd='sshpass -p %s ssh %s@%s' % (password, user, host)
    reset_cmd="/bin/bash /reset.sh"
    p = subprocess.Popen(' '.join([ssh_cmd, reset_cmd]).split(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    p.wait()
