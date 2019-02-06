import numpy as np
from time import sleep, time

from csr import make_filter, PitayaLocal, PitayaSSH
from utils import LENGTH
from devices import RedPitaya


class Pitaya:
    def __init__(self, host=None, user=None, password=None):
        self.host = host
        self.user = user
        self.password = password
        self.scpi = RedPitaya(host, delay_scpi_connection=True)

        self._cached_data = {}
        self.parameters = {
            'decimation': 1,
            'p': 1
        }

    def connect(self):
        self.use_ssh = self.host is not None and self.host != 'localhost'

        if self.use_ssh:
            self.pitaya = PitayaSSH(
                ssh_cmd="sshpass -p %s ssh %s@%s" % (self.password, self.user, self.host)
            )
            # FIXME: das geht eleganter
            sleep(1)
        else:
            self.pitaya = PitayaLocal()

    def write_registers(self):
        new = dict(
            # channel A (PID channel)
            fast_a_brk=0,
            fast_a_mod_amp=0xeee,
            fast_a_mod_freq=0,
            fast_a_x_tap=0,
            fast_a_sweep_run=0,
            fast_a_sweep_step=100000,
            fast_a_y_tap=0,
            fast_a_dy_sel=self.pitaya.signal("scopegen_dac_a"),

            # channel B (channel for rect output)
            fast_b_brk=1,
            fast_b_dx_sel=self.pitaya.signal("zero"),
            fast_b_x_tap=0,
            fast_b_y_tap=0,
            fast_b_sweep_run=0,
            fast_b_sweep_step=100000,
            fast_b_dy_sel=self.pitaya.signal("scopegen_dac_b"),
            fast_b_mod_freq=0,
            fast_b_mod_amp=0x0,

            fast_a_relock_run=0,
            fast_a_relock_en=self.pitaya.states(),
            fast_a_y_hold_en=self.pitaya.states(),
            fast_a_y_clear_en=self.pitaya.states(),
            fast_a_rx_sel=self.pitaya.signal('zero'),
            fast_b_relock_run=0,
            fast_b_relock_en=self.pitaya.states(),
            fast_b_y_hold_en=self.pitaya.states(),
            fast_b_y_clear_en=self.pitaya.states(),
            fast_b_rx_sel=self.pitaya.signal('zero'),

            # trigger on GPIO trigger
            scopegen_external_trigger=0,
            scopegen_adc_b_sel=self.pitaya.signal("fast_b_x"),

            gpio_p_oes=0,
            gpio_n_oes=0,
            gpio_p_outs=0,
            gpio_n_outs=0,
            gpio_n_do0_en=self.pitaya.signal('zero'),
            gpio_n_do1_en=self.pitaya.signal('zero'),
        )

        # filter out values that did not change
        new = dict(
            (k, v)
            for k, v in new.items()
            if (
                (k not in self._cached_data)
                or (self._cached_data.get(k) != v)
            )
        )
        self._cached_data.update(new)

        for k, v in new.items():
            self.pitaya.set(k, int(v))
            print('SET', k, int(v))

        # clear
        self.pitaya.set('fast_b_x_clear_en', self.pitaya.states('force'))
        self.pitaya.set('fast_b_y_clear_en', self.pitaya.states('force'))

        # set PI parameters
        self.pitaya.set_iir("fast_a_iir_a", *make_filter('P', k=self.parameters['p']))

        # re-enable lock
        self.pitaya.set('fast_b_y_clear_en', self.pitaya.states())
        self.pitaya.set('fast_b_x_clear_en', self.pitaya.states())

    def start_clock(self, percentage):
        data = []

        for i in range(LENGTH):
            if i < percentage * LENGTH:
                data.append(0)
            else:
                data.append(1)

        out = self.scpi.fast_out[1]
        out.wave_form = 'ARBITRARY'
        out.waveform_data = data
        out.frequency = 7629.394531249999 / int(self.parameters['decimation'])
        out.enabled = True

    def set_feed_forward(self, feedforward):
        out = self.scpi.fast_out[0]
        out.wave_form = 'ARBITRARY'
        out.waveform_data = feedforward
        out.frequency = 7629.394531249999 / int(self.parameters['decimation'])
        out.enabled = True