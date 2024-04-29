from time import sleep,time

'''
    Provides compatibility for serialOM between CPython and microPython

    ticks_ms(), ticks_diff() and sleep_ms() emulate the standard microPython
        timing functions which prefers int(ms) to float(seconds)
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

