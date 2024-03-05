from serialOM import serialOM
from machine import UART
from time import sleep

'''
    MicroPython Test loop with `uart()`
'''

OMkeys = {'FFF':['network'], 'CNC':['network'], 'Laser':['network']}

rrf = UART(0)
rrf.init(baudrate=57600)
#log = open('rawlog.log','a')
OM = serialOM(rrf, OMkeys,rawLog=None)
print('controller is in "' + OM.model['state']['machineMode'] + '" mode')
print('> M122')
response = OM.getResponse('M122')
for line in response[:3] + ['<truncated>']:
    print('>> ' + line)

while True:
    print(OM.model['network']['name'] + ' :: state: '
          + OM.model['state']['status'] + ', up: '
          + str(OM.model['state']['upTime']),end='')
    if OM.model['state']['displayMessage']:
        print(', message: ' + OM.model['state']['displayMessage'],end='')
    print()
    sleep(6)
    OM.update()
