from serialOM import serialOM
from serial import Serial
from time import sleep
from datetime import timedelta
from sys import argv

'''
    Bare-Bones demo of SerialOM for CPython
'''

if len(argv) != 2:
    print('serial device argument missing, eg: ' + argv[0]
          + ' /dev/ttyACM0')
    exit()
else:
    device = argv[1]

rrf = Serial(device,57600)
OM = serialOM(rrf, {'FFF':['network'],
                  'CNC':['network'],
                  'Laser':['network']})

print('controller is in "' + OM.model['state']['machineMode'] + '" mode')
print('> M122')
response = OM.getResponse('M122')
for line in response[:10] + ['<truncated>']:
    print('>> ' + line.strip('\n'))

while True:
    print(OM.model['network']['name'] + ' :: state: '
          + OM.model['state']['status'] + ', up: '
          + str(timedelta(seconds=OM.model['state']['upTime'])),end='')
    if OM.model['state']['displayMessage']:
        print(', message: ' + OM.model['state']['displayMessage'],end='')
    print()
    sleep(6)
    OM.update()
