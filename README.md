simulating elevators - [inspiration](https://youtu.be/xOayymoIl8U)


# Features
- Fully featured test suite to run automated tests
- Easy to use GUI to allow for manual testing and bug fixing
- Extensible framework to implement new algorithms and tests
- Ability to export and import artefacts for debugging or reproducible testing
- Adjustable simulation speed*

> *Simulation speed might not be as relative as one might expect. For example, the jump from 100 to 200 might not be double the speed as there might be other factors such as code computation affecting the slower execution.

## Development

Both the GUI and the Test Suite control the same managers and algorithms in the backend. However, there are wrappers to allow for the difference in concurrency type (threading/multiprocessing).

![overview](images/overview.svg)

| File | Description |
| --- | --- |
| [app.py](/app.py) | GUI handler |
| [suite](/suite) | Test suite |
| [models](/models) | Data models for custom classes |
| [constants.py](/constants.py) | Various enums and constants |
| [utils.py](/utils.py) | Utility functions |
| [errors.py](/errors.py) | Custom errors |

### Dependencies
- wxPython===4.2.0 ([PyPi](https://pypi.org/project/wxPython/4.2.0/), [official website](https://wxpython.org/pages/downloads/index.html))

### Custom Algorithms

A custom algorithm can be made by subclassing [ElevatorAlgorithm](/models.py) in a file in the `algorithms` folder.

The name of the file is unimportant. 2 attributes need to be defined in the file, `__name__` (str) and `__algorithm__` (object) as shown.

When debugging, `algorithm.name` will be the `__name__` attribute.

```python
class MyAlgorithm(ElevatorAlgorithm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # custom init code here

    def get_new_destination(self, elevator: Elevator) -> int:
        # return a integer for the new destination floor
        pass


__name__ = "My Custom Algorithm"
__algorithm__ = MyAlgorithm
```

There are various events exposed for subclasses but the only required function is `get_new_destination`. Exposed events are listed below.

```python
def pre_tick(self):
def post_tick(self):
def on_load_load(self, load, elevator):
def on_load_unload(self, load, elevator):
def on_elevator_move(self, elevator):
def on_elevator_added(self, elevator):
def on_elevator_removed(self, elevator):
def on_floors_changed(self):
def on_load_added(self, load):
def on_load_removed(self, load):
```

There are also 2 check functions that should return a boolean. If the check fails, the load will not be loaded/unloaded.
```python
def pre_load_check(self, load, elevator) -> bool:
def pre_unload_check(self, load, elevator) -> bool:
```

### The Cycle

![cycle](images/cycle.svg)

> GUI events will be triggered upon every configuration change and every tick. Refer to [GUI](#gui) and [ElevatorManager](/models.py) > `send_event` for more information.

## GUI

### End User

The script `app.py` exposes a [WXPython](https://www.wxpython.org/) GUI to allow end users to interact with the elevator simulator. 

![preview](images/preview.gif)

### Development

The GUI uses a multithreaded approach as per the following explanation:
| Thread | Description |
| --- | --- |
| Main Thread | Manages the GUI and user input |
| Manager Thread | Manages the elevators and all backend related tasks |

Upon any changes in the manager thread, a [wx event](https://docs.wxpython.org/events_overview.html) is fired to allow for the main thread to update the GUI. This can happen *very very* often (multiple times per tick) hence it is important to keep the event handlers as lightweight as possible and perform as little layout changes.

## Test Suite


### End User

The test suite exposes a `TestSuite` class that takes in `TestSettings`. This allows the end user to create reproducible tests and feed them in programmatically. Refer to the source code for exact arguments.

Further options can also be fed into the `TestSuite` class. Refer to the source code for exact arguments.

It is recommended for the `name` to not be distinguishable to the algorithm and multiple tests (with different algorithms) to have identical names.

Source Code: [suite.py](/suite.py)    
Examples: [test_json.py](/test_json.py) ([test.example.json](/test.example.json)), [test_benchmark.py](/test_benchmark.py)

### Development

The test suite runs using a multiprocess approach as per the following explanation:
| Process | Description |
| --- | --- |
| Main Process | Manages all processes and does final saving of results |
| Background Process | Handles errors raised by test processes and exports artefacts |
| `N` Test Processes | Runs the test and raises errors to the background process, reports back to main process |

The number of test processes (`N`) are determined by the following formula:
- <= the given `max_processes` kwarg
- <= (CPU Count - 1)
- <= Number of total iterations

The processes are then spawned and iterations are run concurrently. Upon any errors raised by the algorithm, it will be passed to the Background Process and the iteration will be skipped. A new process will be spawned to continue the test suite.

Tests are *mostly replicable* with the given seed. The initial state should be the same but there might be small kinks that could result in slightly varied outcomes. Note that for each seed, the iteration count is also attached to it.

#### Benchmark Example

Rough example of what the test suite is capable of. This ran in under 3 minutes (10 iterations each) on a 4 physical core CPU.

```
BUSY                  NUM  TICK               WAIT               TIL            OCC
--------------------  ---  -----------------  -----------------  -------------  -------------
Rolling               10   352.70 (353.00)    122.02 (117.45)    33.64 (27.20)  61.91 (85.33)
LOOK                  10   338.30 (342.50)    108.49 (98.50)     29.21 (25.30)  55.91 (68.67)
Destination Dispatch  10   473.10 (471.50)    118.12 (101.70)    26.90 (23.45)  36.78 (21.33)
Scatter               10   673.57 (648.00)    176.93 (165.07)    68.45 (48.14)  67.06 (92.38)
FCFS                  10   2581.40 (2570.50)  1081.34 (1060.90)  46.50 (39.40)  11.86 (0.67)
NStepLOOK             10   5885.90 (5919.50)  1190.78 (747.15)   30.50 (26.35)  3.39 (0.00)

SLOW                  NUM  TICK               WAIT               TIL            OCC
--------------------  ---  -----------------  -----------------  -------------  -------------
LOOK                  10   29.90 (30.00)      8.80 (8.50)        3.84 (3.35)    33.19 (30.67)
Rolling               10   34.30 (35.00)      10.37 (9.30)       4.52 (3.85)    35.89 (31.00)
Scatter               10   41.30 (40.50)      10.57 (8.65)       7.11 (5.70)    51.62 (56.67)
Destination Dispatch  10   43.80 (44.50)      12.28 (10.45)      5.89 (4.80)    38.45 (37.67)
FCFS                  10   115.50 (114.00)    49.13 (49.05)      5.88 (5.15)    14.22 (8.33)
NStepLOOK             10   150.90 (139.00)    32.16 (14.50)      4.06 (3.60)    7.32 (0.67)
```