from machine import Pin

import time
import _thread


class CtxBase:
    def __init__(self, do_log: bool) -> None:
        self.do_log = do_log
        self.sleep_total_ms = 0

    def IN_disable(self, v):
        "Set logical state"
        assert isinstance(v, bool)

    def IN_t(self, v):
        "Set logical state"
        assert isinstance(v, bool)

    def IN_P_0V0(self) -> None:
        pass

    def IN_P_0V7(self) -> None:
        pass

    def IN_P_1V4(self) -> None:
        pass

    def wait_ms(self, ms):
        assert isinstance(ms, int)
        self.sleep_total_ms += ms

    def log(self, msg: str) -> None:
        if self.do_log:
            print(msg)


class Ctx(CtxBase):
    def IN_disable(self, v):
        "Set logical state"
        self.log(f"  IN_disable({v}")
        pin_IN_disable.value(v)

    def IN_t(self, v):
        "Set logical state"
        self.log(f"  IN_t({v}")
        pin_IN_t.value(v)

    def IN_P_0V0(self) -> None:
        self.log("  IN_P_0V0()")
        pin_spannung_0.value(0)
        pin_spannung_1.value(0)

    def IN_P_0V7(self) -> None:
        self.log("  IN_P_0V7()")
        pin_spannung_0.value(0)
        pin_spannung_1.value(1)

    def IN_P_1V4(self) -> None:
        self.log("  IN_P_1V4()")
        pin_spannung_0.value(1)
        pin_spannung_1.value(1)

    def wait_ms(self, ms):
        self.log(f"  sleep({ms}ms)")
        time.sleep(ms / 1000.0)


def scenario(ctx: CtxBase):
    ctx.log("Empty, may be overridden")


def run_scenario(run_synchron: bool, do_validate: bool, do_log: bool = False):
    assert isinstance(run_synchron, bool)
    assert isinstance(do_validate, bool)
    assert isinstance(do_log, bool)
    ctx = CtxBase(do_log=do_log) if do_validate else Ctx(do_log=do_log)
    ctx.log(f"run_scenario({run_synchron=}, {do_validate=})")
    if run_synchron:
        scenario(ctx=ctx)
    else:
        # Wait for maximum 10s
        for _ in range(10.0):
            try:
                _thread.start_new_thread(lambda: None, ())
                break
            except OSError as e:
                print(f"Wait for second core: {e}")
                time.sleep(1.0)

        _thread.start_new_thread(scenario, (ctx,))
    ctx.log("run_scenario() DONE")


pin_spannung_0 = Pin("GPIO16", Pin.OUT)
pin_spannung_1 = Pin("GPIO17", Pin.OUT)
pin_IN_disable = Pin("GPIO20", Pin.OUT)
pin_IN_t = Pin("GPIO21", Pin.OUT)

pin_spannung_0.value(0)
pin_spannung_1.value(0)
pin_IN_disable.value(0)
pin_IN_t.value(0)

