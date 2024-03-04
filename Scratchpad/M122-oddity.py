# C-Python
#import serial
#rrf = serial.Serial('dev\ttyACM0',57600)

# Micropython
import machine
rrf = machine.UART(0)
rrf.init(57600,rxbuf=4096)

# M503 works OK.

while True:
    _ = rrf.write('M122\n')
    while True:
        byte = rrf.readline()
        if byte:
            print(byte.decode(),end='')