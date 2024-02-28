from time import sleep,time

'''
    stub functions for CPython to emulate the micropython native time (nee.utime) lib
'''

def ticks_ms():
    return int(time() * 1000)

def ticks_diff(first,second):
    # This should 'just work' in CPython3
    # int()'s can be as 'long' as they need to be, with no need for
    # the 'rollover' protection provided by the microPython equivalent
    return int(first-second)

def sleep_ms(ms):
    sleep(ms/1000)
