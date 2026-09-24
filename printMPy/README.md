# This is the microPython port of serialOM

place all the `.py` files in this folder in the root of your microPython device along with `serialOM.py` from the repo root folder.

Currently has two working programs:
* `printMPy.py`  : microPython printPy fork
  * Settings are in `config.py`
  * A `lumen` class has been added to handle status LED's. It can also show a RGB 'mood'.
  * The `outputTXT.py` class is identical to the main printPy one, REPL console output and file logging works.
* `microDemo.py` : a re-work of the CPython miniDemo for microPython
