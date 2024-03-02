from serialOM import serialOM
from machine import UART
from time import sleep
from datetime import timedelta

'''
    MicroPython Test loop with `uart()`
'''

OMkeys = {'FFF':['network'], 'CNC':['network'], 'Laser':['network']}

rrf = UART(0)
rrf.init(baudrate=57600,timeout=50,timeout_char=25)

OM = serialOM(rrf, OMkeys)

print('controller is in "' + OM.model['state']['machineMode'] + '" mode')
print('> M122')
response = OM.getResponse('M122')
for line in response[:8] + ['<truncated>']:
    print('>> ' + line)

while True:
    print(OM.model['network']['name'] + ' :: state: '
          + OM.model['state']['status'] + ', up: '
          + str(timedelta(seconds=OM.model['state']['upTime'])),end='')
    if OM.model['state']['displayMessage']:
        print(', message: ' + OM.model['state']['displayMessage'],end='')
    print()
    sleep(6)
    OM.update()
