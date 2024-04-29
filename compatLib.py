from time import sleep,time

'''
    Provides compatibility for serialOM between CPython and microPython

    zip_longest(), repeat() and reduce() are in the standard
        CPython libs, but not microPython

    ticks_ms(), ticks_diff() and sleep_ms() emulate the standard microPython
        timing functions which prefers int(ms) to float(seconds)
'''

def repeat(object, times=None):
    # repeat(10, 3) --> 10 10 10
    if times is None:
        while True:
            yield object
    else:
        for i in range(times):
            yield object

def reduce(function, iterable, initializer=None):
    it = iter(iterable)
    if initializer is None:
        value = next(it)
    else:
        value = initializer
    for element in it:
        value = function(value, element)
    return value

def ticks_ms():
    return int(time() * 1000)

def ticks_diff(first,second):
    # This should 'just work' in CPython3
    # int()'s can be as 'long' as they need to be, with no need for
    # the 'rollover' protection provided by the microPython equivalent
    return int(first-second)

def sleep_ms(ms):
    sleep(ms/1000)

