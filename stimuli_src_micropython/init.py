from machine import Pin

import time
import _thread

def wait_ms(ms):
    print(f"  sleep({ms}ms)")
    time.sleep(ms/1000.0)

def scenario():
    print("Empty, may be overridden")

def run_scenario():
    print("run_scenario()")
    scenario()
    print("run_scenario() DONE")

def run_scenario_on_second_thread():
    print("scenario_on_second_thread()")
    _thread.start_new_thread(run_scenario, ())

pin_spannung_0 = Pin('GPIO16', Pin.OUT) 
pin_spannung_1 = Pin('GPIO17', Pin.OUT)
pin_IN_disable = Pin('GPIO20', Pin.OUT) 
pin_IN_t = Pin('GPIO21', Pin.OUT) 

pin_spannung_0.value(0)
pin_spannung_1.value(0)
pin_IN_disable.value(0)
pin_IN_t.value(0)

IN_P_0V0 = (0, 0)
IN_P_0V7 = (0, 1)
IN_P_1V4 = (1, 1)

def IN_disable(v):
    print(f"  IN_disable({v}")
    pin_IN_disable.value(v)

def IN_t(v):
    print(f"  IN_t({v}")
    pin_IN_t.value(v)

def IN_P(list_v):
    print(f"  IN_P({list_v}")
    pin_spannung_0.value(list_v[0])
    pin_spannung_1.value(list_v[1])
