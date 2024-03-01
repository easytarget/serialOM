# serialOM.py
A RepRapFirmware [ObjectModel](https://github.com/Duet3D/RepRapFirmware/wiki/Object-Model-Documentation) serial access tool for Python3

**serialOM** implements a fetch and update cycle using [`M409`](https://docs.duet3d.com/User_manual/Reference/Gcodes#m409-query-object-model) commands to query the ObjectModel on the controller, the responses are gathered and merged into a local Dictionary structure. That can be accessed to drive displays, loggers and more.

## Requirements:
* `PySerial` (https://pyserial.readthedocs.io/)
  * *serialOM* expects to be passed a PySerial object (but other serial/stream devices may work too).
* A suitable RRF USB/serial/UART device specified with '[M575](https://docs.duet3d.com/User_manual/Reference/Gcodes#m575-set-serial-comms-parameters)' in `config.g` to connect to.
  * For USB set `M575 P0 S2` in your config, this will set the USB port correctly.
  * Other UART ports should also use `S2` as the port mode (`S0` also works)
  * CRC/Checksum modes are *not* supported, this includes the default `S1` mode.
* `timeStubs.py`: Already provided; a local set of stubs for cross-python compatibility.
  * Keep this in the same folder as `serialOM.py`.

## Overview:
**serialOM()** takes a `Serial()` object at init, and a dictionary with the OM keys to gather for each machine mode. 

It returns a *serialOM* object, with the `model` property populated with the requested keys (and the 'state' key)

A bare bones example of *serialOM* can be as simple as:
```python
from serialOM import serialOM
from serial import Serial

rrf = Serial('/dev/ttyACM0',57600)
OM  = serialOM(rrf, {'FFF':[],'CNC':[],'Laser':[]}, quiet=True)
print('state: ' + OM.model['state']['status']
     + ', up: ' + str(OM.model['state']['upTime']) + 's')
```
This will quietly connect and display the current machine state and uptime. Try setting `quiet=False` in the `OM = serialOM()` init arguments to see a lot more detail of the connecction progress.

If *serialOM* times out or fails to detect a RRF controller during initialisation `OM.machineMode` will be empty (`''`), otherwise it will reflect the controller mode; currently `'FFF'`, `'CNC'` or `'Laser'`.

The provided 'miniDemo.py' script is more detailed and shows the use of the `OM.update()` and `OM.getResponse()` methods.

### Blocking:
When being initialised, updated or making requests *serialOM* is blocking, it implements it's own request timeouts and will return if the connected device times out. This 'per request' timeout can be passed  at init(). During update()s serialOM will make 2 requests minimum, plus one request per additional OM key.

The `Serial()` device neeeds to have it's blocking timeouts set lower than the overall Request timeout. This is done during init by *serialOM* itself and does not need to be specified when creating a PySerial  object. 
* If adapting for other serial classes than PySerial you need to set the blocking correctly; for instance the microPython `UART` class only allows timeouts to be set as init arguments.

### Exceptions:
*serialOM* catches all exceptions coming from `serial` devices during read and write operations and will raise it's own `serialOMError` exception in response, with the original exception in the body. This allows the calling script to retry/re-initialise the connection as needed (handy for USB serial which disconnects when the controller reboots).

## Use

### Init:
Import serialOM:
```python
from serialOM import serialOM
```
And create an instance of it with:
```python
OM = serialOM(rrf, omKeys, requestTimeout=500, rawLog=None, quiet=False)
```
where:
```console
rrf            = a pyserial.Serial object; or similar
omKeys         = per-mode lists of keys to sync, (dict, see below)
                 omKeys = {'machineMode':['OMkey1','OMkey2',..],etc..}
                          Empty lists [] are allowed.
                          At least one machineMode must be specified.
requestTimeout = Timeout for response after sending a request (int, ms)
rawLog         = raw log, or None (writable file object) 
quiet          = Suppress info messages (bool)
```
If the initial connection and update are successful the property `OM.machineMode` will be populated, otherwise it will return an empty string.

The fetched ObjectModel is returned in the `OM.model` property as a dictionary of keys that match the keys obtained from the controller.

### Methods and Properties:
The principle method is 
```python
OM.update()
```
This initiates a refresh and update of the *model* property from the controller. Returns `True` for success, `False` if timeouts occurred.

*OM.update()* deals gracefully with `machineMode` changes and `upTime` rollbacks (controller reboots); refreshing the entire model and (re)setting `OM.machineMode` as needed.

The `OM.model`property contains the fetched model as a dictionary.

`OM.machineMode` will be set to the machine mode, or an empty string if not connected.

#### There are two further methods provided by *serialOM* for convenience:
```python
serialOM.sendGcode('code')
```
Sends the specified `code` to the controller, has no return value.
```python
serialOM.getResponse('code')
```
Sends `code` and waits for a response ending with `ok`, returns a list of recieved lines. Conforms to the request timeout as described above and returns an empty list if no valid response recieved.

## Operation:
*serialOM* Implements a RRF ObjectModel fetch and update cycle based on using `[M409](https://docs.duet3d.com/User_manual/Reference/Gcodes#m409-query-object-model)` commands to query the ObjectModel on the controller, the responses are gathered and merged into a local Dictionary structure.
  * *serialOM* Uses the `seqs` sequence number mechanism to limit load on the controller by only making verbose requests as needed.
  * *serialOM* fetches different sets of top level ObjectModel keys depending on the master machine mode `FFF`,`CNC` or `Laser`.
    * This allows you to limit requests to only the keys you need for the mode.
    * The `printPY.py` demo demonstrates how to use this.
  * *serialOM* provides a `serialOM.model` structure (dict) with all currently known data.
   * Each key in *serialOM.model* represents the corresponding OM top level key. The contents of the key will be a structure (lists and dicts) matching the ObjectModel.
  * All low-level serial errors are trapped, and *serialOM* provides it's own `serialOMError` exception that can be independently trapped to make connections robust.
    * The `printPY.py` demo demonstrates this.
  * After initial connection has been made `serialOM.update()` can be called to update and refresh the local ObjectModel.
    * Calling update() will clean and re-populate the ObjectModel if either a machine mode change, or a restart of the controller is detected.
* Requires `pyserial`, or a compatible 'serial()' object
  * Install your distros pyserial package: eg: `sudo apt install python-serial`, or `pip install --user pyserial`, or use a virtualenv (advanced users).
  * On linux make sure your user is in the 'dialout' group to access the devices.
  * There is no reason why this would not run on Windows, but I have not tried this. You will need ai viable Python 3.7+ install with pyserial, and change the device path to the windows equivalent.

## Notes:
  * Written in CPython; but I am trying to keep all the logic and data handling simple and low-memory for porting to microPython.
    * Non micropython standard libs are discouraged unless they have a easy micropython equivalent/local lib.
    * All times are in `ms` (micropython uses `int(ms)` for it's timing basics rather than `float(seconds)`).
  * Tested and developed on a RaspberryPI connected to my Duet2 wifi via USB/serial,and python 3.9.
  * You can specify a 'raw' log file handle at init; this is handy when debugging but will fill very rapidly and should never be used 'in production'!
  * Published under the CC0 (Creative Commons Zero) Licence; use however you want! Dont blame me if it all goes wrong..

# printPy.py:
*serialOM* comes with a full implementation of a datalogging script in the `printPy` folder.
This uses the features above to implement a robust data gathering loop. This, in turn, calls an output class to process the data being gathered. 

In the demo this is a `text` implementation of the class which logs to the console, and optionally to a log file with timestamps.

See [printPy/README.md](printPy/README.md)
* The text output class serves as a template for writing classes to display ObjectModel info on I2C/SPI or any other external display/data feed.
* This will eventually be ported to microPython as the core of [PrintPy2040](https://github.com/easytarget/PrintPy2040/).

Here is an example of starting *printPy.py* with a 10s update time late into a very small and fast print (it's PC-ABS, hence the temps.)

```console
$ python printPy 10000
printPy.py is starting at: 2024-2-29 01:02:54 (device localtime)
starting output
device "/dev/ttyACM0" available
connected to: /dev/ttyACM0 @57600
serialOM is starting
checking for connected RRF controller
> M115
>> FIRMWARE_NAME: RepRapFirmware for Duet 2 WiFi/Ethernet FIRMWARE_VERSION: 3.4.6 ELECTRONICS: Duet WiFi 1.02 or later FIRMWARE_DATE: 2023-07-21 14:08:28
>> ok
controller is connected
making initial data set request
connected to ObjectModel
info: RepRapFirmware for Duet 2 WiFi/Ethernet v3.4.6 on Duet 2 WiFi
      Controller is in "FFF" mode
      Vin: 23.8V | mcu: 41.0C
status: processing | uptime: 8:45:57 | wifi: 10.0.0.30 | progress: 88.5% | bed: 100.1 (100.0) | e0: 280.2 (280.0) | message: Template_For_Diagrams.gcode
status: processing | uptime: 8:46:07 | wifi: 10.0.0.30 | progress: 92.5% | bed: 100.0 (100.0) | e0: 279.5 (280.0) | message: Template_For_Diagrams.gcode
status: processing | uptime: 8:46:17 | wifi: 10.0.0.30 | progress: 94.4% | bed: 100.0 (100.0) | e0: 280.2 (280.0) | message: Template_For_Diagrams.gcode
status: processing | uptime: 8:46:27 | wifi: 10.0.0.30 | progress: 95.9% | bed: 100.0 (0.0) | e0: 280.4 (0.0)
status: processing | uptime: 8:46:37 | wifi: 10.0.0.30 | progress: 95.9% | bed: 98.5 (0.0) | e0: 276.9 (0.0)
status: idle | uptime: 8:46:47 | wifi: 10.0.0.30 | bed: 96.8 (0.0) | e0: 268.2 (0.0)
status: idle | uptime: 8:46:57 | wifi: 10.0.0.30 | bed: 95.2 (0.0) | e0: 258.9 (0.0)
```
