from PyRedPitaya.board import *

r = RedPitaya()

while True:
    data = input().replace('\n', '').split(' ')

    if len(data) == 1:
        print(r.read(int(data[0])))
    else:
        assert len(data) == 2
        addr, value = data
        addr = int(addr)
        value = int(value)

        r.write(addr, value)
