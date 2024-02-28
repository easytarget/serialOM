# serialOM.py
A RRF ObjectModel serial access class/library for Python3

Requirements:
* `PySerial` (https://pyserial.readthedocs.io/)
  * serialOM expects to be passed a PySerial object (but other serial/stream devices may work too).
* `timeStubs.py`: a local set of stubs for cross-python compatibility. Place this in the same folder as `serialOM.py`
* A suitable RRF USB/serial/UART device specified with '[M575](https://docs.duet3d.com/User_manual/Reference/Gcodes#m575-set-serial-comms-parameters)' in `config.g` to connect to.
  * For USB set `M575 P0 S2` in your config, this will set the USB port correctly.
  * Other UART ports should also use `S2` as the port mode (`S0` also works)
  * CRC/Checksum modes are *not* supported, this includes the default `S1` mode.

## Use:
`serialOM` requires a `serial.Serial()` object at init, and a dictionary with the OM keys to gather for each machine mode. It will connect and populate `serialOM.model` with the '`state`' OM key plus the per-mode keys.

A bare bones example of serialOM can be as simple as:
```python
from serialOM import serialOM
from serial import Serial

rrf = Serial('/dev/ttyACM0',57600)
OM  = serialOM(rrf, {'FFF':[],'CNC':[],'Laser':[]}, quiet=True)
print('state: ' + OM.model['state']['status']
     + ', up: ' + str(OM.model['state']['upTime']) + 's')
```
Try setting `quiet=False` for serialOM to see a lot more detail of the connecction progress.

If serialOM times out or otherwise fails to connect to the controller during initialisation `serialOM.machineMode` will be empty (`''`), otherwise this will reflect the controller mode; currently `'FFF'`, `'CNC'` or `'Laser'`.

Once connected calling `serialOM.update()` will refresh the model tree. It returns `True` if the update succeeded, `False` if it failed (response timeout). It deals gracefully with `machineMode` changes and `upTime` rollbacks (controller reboots) refreshing the entire model and (re)setting `serialOM.machineMode` as needed.

The provided 'miniDemo.py' script is more detailed and shows the use of `updating()` and `getResponse()` functions.

#### Blocking:
When being initialised, updated or making requests `serialOM` is blocking, it implements it's own request timeouts and will return if the connected device times out. The 'per request' timeout can be passed as an argument, during updates it will make 2 requests minimum, plus one request per additional mode OM key. During `init` additional requests occur to detect firmware and initial state.

The `Serial()` device neeeds to have it's blocking timeouts set lower than the overall Request timeout, this is done during init by `serialOM` itself and does not need to be specified when creating the serial object.

#### Exceptions:
`serialOM` catches all exceptions coming from `serial` devices during read and write operations and will raise it's own `serialOMError` exception in response, with the original exception in the body. This allows the calling script to retry/re-initialise the connection as needed (handy for USB serial which disconnects when the controller reboots).

#### Extras:
There are two public functions provided by `serialOM` for convenience:
* `sendGcode('code')` : Sends the specified `code` to the controller, has no return value.
* `getResponse('code')`: Sends `code` and waits for a response ending with `ok`, returns a list of recieved lines. Conforms to the request timeout as described above and returns an empty list if no valid response recieved.

## printPy demo:
`serialOM` comes with a full implementation of a datalogging script in the `printPy` folder. 
This uses the features above to implement a robust data gathering loop. This, in turn, calls an output class to process the data being gathered. In the demo this is a `text` implementation of the class which logs to the console, and optionally to a log file.
* See [printPy/README.md](printPy/README.md)
* The text output class serves as a template for writing classes to display ObjectModel info on I2C/SPI or any other external display/data feed.
* This will eventually be ported to microPython as the core of [PrintPy2040](https://github.com/easytarget/PrintPy2040/). Eventually.


## Operation:
Implements a RRF ObjectModel fetch/update cycle in Python, basically a CPython prototype of a microPython project.
* Uses `M409` commands to query the ObjectModel, parses the responses to a Dictionary structure for output
  * Uses the `seqs` sequence numbers to limit load on the controller by only making verbose requests as needed.
  * Traps all serial errors and provides it's own `serialOMError` exception that can be trapped to handle communications issues seamlessly.
    * The `printPY.py` demo demonstrates this.
  * Returns a `serialOM.model` structure (dict) with all currently known data
  * After initial connection has been made `serialOM.update()` can be called to update and refresh the local ObjectModel
  * Can fetch different sets of top level ObjectModel keys depending on the master machine mode `FFF`,`CNC` or `Laser`.
  * Rebuilds the ObjectModel if it detects either a machine mode change, or a restart of the controller
* Requires `pyserial`
  * Install your distros pyserial package: eg: `sudo apt install python-serial`, or `pip install --user pyserial`, or use a virtualenv (advanced users).
  * On linux make sure your user is in the 'dialout' group to access the devices
  * There is no reason why this wont run on Windows, but I have not tried this. You will need a Python 3 install with pyserial, and change the device path to the windows equivalent.
* Notes:
  * CPython; but I am trying to keep all the logic and data handling simple and low-memory for running on microPython.
    * Non micropython standard libs are discouraged unless they have a easy micropython equivalent/local lib.
    * All times are in `ms` (micropython uses `int(ms)` for it's timing basics rather than `float(seconds)`)
  * Tested and developed on a RaspberryPI connected to my Duet2 wifi via USB/serial
  * You can specify a 'raw' log file; this is handy when debugging but will fill very rapidly and should never be used 'in production'
