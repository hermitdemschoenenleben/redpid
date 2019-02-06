from PyRedPitaya.board import RedPitaya
from time import sleep

r = RedPitaya()

print('open PID before')

POWER_IN = '/sys/devices/soc0/amba_pl/83c00000.xadc_wiz/iio:device1/in_voltage9_vaux0_raw'
f = open(POWER_IN, 'r')

i = 0

while True:
    # this was the first try:
    # value = r.ams.aif1
    # however, this does not work if PID application wasn't started manually before
    # but if starting PID application, RP is going to crash
    # --> access the file directly
    f.seek(0)
    value = int(f.read().replace('\n', ''))
    i += 1

    if i == 10000:
        print(value)
        i = 0
    """print(value)
    from time import sleep
    sleep(.1)
    continue"""

    if value < 620:
        print('reset')
        r.pid11.reset = True
        r.pid11.proportional = 0
        r.pid11.derivative = 0
        r.pid11.integral = 0
        sleep(.01)
