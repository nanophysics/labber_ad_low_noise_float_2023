from __future__ import annotations
import time
import enum
import logging
import threading
import dataclasses
import typing

import numpy as np

from ad_low_noise_float_2023.ad import (
    AdLowNoiseFloat2023,
    LOGGER_NAME,
    MeasurementSequence,
)
from ad_low_noise_float_2023.constants import PcbParams, RegisterFilter1
from ad_utils import CHANNEL_VOLTAGE, CHANNEL_T, CHANNEL_DISABLE

TICK_INTERVAL_S = 0.5
SAMPLE_COUNT_PRE_POST = 1

TODO_REMOVE = False

logger = logging.getLogger("LabberDriver")
logger_ad = logging.getLogger(LOGGER_NAME)

LOCK = threading.Lock()


class State(enum.IntEnum):
    ARMED = enum.auto()
    CAPTURING = enum.auto()


def synchronized(func):
    def wrapper(*args, **kwargs):
        with LOCK:
            try:
                return func(*args, **kwargs)
            except:  # pylint: disable=bare-except
                logger.exception('Exception in method "HeaterThread.%s"', func.__name__)
                raise

    return wrapper


@dataclasses.dataclass
class Capturer:
    IN_voltage: list[np.array]
    IN_disable: list[np.array]
    IN_t: list[np.array]

    def append(self, measurements: MeasurementSequence) -> None:
        self.IN_voltage = np.concatenate((self.IN_voltage, measurements.adc_value_V))
        self.IN_disable = np.concatenate((self.IN_disable, measurements.IN_disable))
        self.IN_t = np.concatenate((self.IN_t, measurements.IN_t))

    def stop(self, measurements: MeasurementSequence, idx0_end: int) -> None:
        self.IN_voltage = np.concatenate(
            (self.IN_voltage, measurements.adc_value_V[:idx0_end])
        )
        self.IN_disable = np.concatenate(
            (self.IN_disable, measurements.IN_disable[:idx0_end])
        )
        self.IN_t = np.concatenate((self.IN_t, measurements.IN_t[:idx0_end]))

        assert len(self.IN_voltage) == len(self.IN_disable)
        assert len(self.IN_voltage) == len(self.IN_t)

    @staticmethod
    def find_first0(array_of_bool: np.ndarray) -> typing.Optional[int]:
        """
        Returns the index of the first '0'.
        Returns None if no '0' found.

        import numpy as np
        >>> high_low_high = np.array([1, 1, 0, 0, 1], bool)
        >>> low = np.nonzero(high_low_high == 0)[0]
        >>> low
        array([2, 3])
        >>> low[0]
        2
        """
        if TODO_REMOVE:
            logger.info(f"TOBE REMOVE find_first0({len(array_of_bool)})")
        if len(array_of_bool) == 0:
            if TODO_REMOVE:
                logger.info(f"TOBE REMOVE find_first0({len(array_of_bool)}) A")
            return None

        # Find first '0'
        array0 = np.nonzero(array_of_bool == 0)[0]
        if len(array0) == 0:
            if TODO_REMOVE:
                logger.info(f"TOBE REMOVE find_first0({len(array_of_bool)}) B")
            return None

        idx0_first0 = int(array0[0])
        if TODO_REMOVE:
            logger.info(
                f"TOBE REMOVE find_first0({len(array_of_bool)}) C idx0_first0={idx0_first0}"
            )
        return idx0_first0

    @staticmethod
    def find_first1(array_of_bool: np.ndarray) -> typing.Optional[int]:
        """
        Returns the index of the first '1'.
        Returns None if no '1' found.
        """
        # find first '1'
        array1 = np.nonzero(array_of_bool == 1)[0]
        if len(array1) == 0:
            if TODO_REMOVE:
                logger.info(f"TOBE REMOVE find_first1({len(array_of_bool)}) D")
            return None

        # Raising edge detected
        idx0_first1 = int(array1[0])
        if TODO_REMOVE:
            logger.info(
                f"TOBE REMOVE find_first1({len(array_of_bool)}) D idx0_first1={idx0_first1}"
            )
        return idx0_first1

    def limit_begin(self, idx0: int) -> None:
        self.IN_disable = self.IN_disable[idx0:]
        self.IN_t = self.IN_t[idx0:]
        self.IN_voltage = self.IN_voltage[idx0:]

    def limit_end(self, idx0: int) -> None:
        self.IN_disable = self.IN_disable[:idx0]
        self.IN_t = self.IN_t[:idx0]
        self.IN_voltage = self.IN_voltage[:idx0]

    def insert_begin(self, pre: Capturer) -> None:
        assert isinstance(pre, Capturer)

        len_pre = len(pre.IN_disable)
        len_previous = len(self.IN_disable)
        self.IN_voltage = np.concatenate((pre.IN_voltage, self.IN_voltage))
        self.IN_disable = np.concatenate((pre.IN_disable, self.IN_disable))
        self.IN_t = np.concatenate((pre.IN_t, self.IN_t))
        len_after = len(self.IN_disable)
        assert len_pre + len_previous == len_after, (len_pre, len_previous, len_after)

    def get_slice(self, from_idx0: int, to_idx0: int) -> Capturer:
        assert isinstance(from_idx0, int)
        assert isinstance(to_idx0, int)
        return Capturer(
            IN_voltage=self.IN_voltage[from_idx0:to_idx0],
            IN_disable=self.IN_disable[from_idx0:to_idx0],
            IN_t=self.IN_t[from_idx0:to_idx0],
        )


@dataclasses.dataclass
class Acquistion:
    state: State = State.ARMED
    capturer: typing.Optional[Capturer] = None
    capturer_pre: typing.Optional[Capturer] = None
    capturer_post: typing.Optional[Capturer] = None
    time_armed_start_s: float = time.monotonic()
    done_event = threading.Event()
    lock = threading.Lock()
    _sps: float = 1.0
    out_timeout: bool = False
    out_falling: bool = False
    out_raising: bool = False
    out_falling_s: float = 0.0
    out_enabled_s: float = 0.0
    _duration_max_s = 4.2
    _duration_max_sample = 42

    def set_SPS(self, register_filter1: RegisterFilter1) -> None:
        assert isinstance(register_filter1, RegisterFilter1)
        self._sps = register_filter1.SPS
        self._update_sps()

    def _update_sps(self) -> None:
        self._duration_max_sample = int(self._duration_max_s * self._sps)

    @property
    def duration_max_s(self) -> int:
        return self._duration_max_s

    @duration_max_s.setter
    def duration_max_s(self, value: int) -> None:
        self._duration_max_s = value
        self._update_sps()

    def _done(self) -> None:
        self.done_event.set()
        self.state = State.ARMED

    def wait_for_acquisition(self) -> None:
        """
        We capture a new shot.
        Reset the last shot and get ready.
        """
        with self.lock:
            self.capturer = None
            self.capturer_pre = None
            self.out_timeout = False
            self.out_falling = False
            self.out_raising = False
            self.out_falling_s = 0.0
            self.out_enabled_s = 0.0
            self.time_armed_start_s: float = time.monotonic()
            self.state = State.CAPTURING
            self.done_event.clear()
        self.done_event.wait()

        logger.info(f"    {len(self.capturer.IN_voltage)}samples")
        logger.info(f"    {self._sps:0.0f}SPS")
        logger.info(f"    out_timeout={self.out_timeout}")
        logger.info(
            f"    out_falling={self.out_falling} out_falling_s={self.out_falling_s:0.3f}s"
        )
        logger.info(
            f"    out_raising={self.out_raising} out_enabled_s={self.out_enabled_s:0.3f}s"
        )

    def append(self, measurements: MeasurementSequence, idx0_start: int) -> None:
        with self.lock:
            if self.capturer is None:
                self.capturer = Capturer(
                    IN_voltage=measurements.adc_value_V[idx0_start:],
                    IN_disable=measurements.IN_disable[idx0_start:],
                    IN_t=measurements.IN_t[idx0_start:],
                )
            else:
                self.capturer.append(measurements=measurements)
            logger.info(f"{self.state.name} append({len(measurements.adc_value_V)})")

    def found_raising_edge(self) -> bool:
        if self.capturer_pre is None:
            # No falling edge yet
            idx0 = self.capturer.find_first0(self.capturer.IN_disable)
            if idx0 is not None:
                # We found a falling edge
                self.capturer_pre = self.capturer.get_slice(
                    from_idx0=idx0 - SAMPLE_COUNT_PRE_POST,
                    to_idx0=idx0,
                )
                self.capturer.limit_begin(idx0=idx0)
                self.out_falling = True
                self.out_falling_s = idx0 / self._sps
                logger.info(
                    f"Falling edge: idx0={idx0} self._sps={self._sps} self.out_falling_s={self.out_falling_s:0.3f}s"
                )
                return False
        else:
            # Falling edge detected, now look for raising edge
            idx0 = self.capturer.find_first1(self.capturer.IN_disable)
            if idx0 is not None:
                # We found a raising edge
                self.capturer.limit_end(idx0=idx0 + SAMPLE_COUNT_PRE_POST)
                self.capturer.insert_begin(self.capturer_pre)
                self.out_raising = True
                self.out_enabled_s = idx0 / self._sps
                logger.info(
                    f"Raising edge: idx0={idx0} self._sps={self._sps} self.out_enabled_s={self.out_enabled_s:0.3f}s"
                )
                with self.lock:
                    self.state = State.ARMED
                    self._done()
                return False

        self.out_timeout = len(self.capturer.IN_disable) > self._duration_max_sample
        if self.out_timeout:
            logger.info(
                f"TIMEOUT {len(self.capturer.IN_disable)}({self._duration_max_sample})samples {self.duration_max_s:0.3f}s {self._sps}SPS"
            )
            with self.lock:
                self.state = State.ARMED
                self._done()
            return True
        return False

        # self.capturer.limit_begin(max(0, idx0-5))
        self.capturer.limit_begin(idx0)

        idx0 = self.capturer.find_first1(self.capturer.IN_disable)
        if idx0 is None:
            return False

        self.capturer.limit_end(idx0=idx0 + 5)
        with self.lock:
            self.state = State.ARMED
            self._done()
            logger.info(
                f"{self.state.name} stop({len(self.capturer.IN_voltage)}, idx0_end={idx0})"
            )
        logger.info(f"found_raising_edge idx0={idx0})")
        return True


class AdThread(threading.Thread):
    """
    EVERY communication between Labber GUI and visa_station is routed via this class!

    There are two problems to solve:
     - Concurrency
        - Labber GUI: 'labber thread'
        - This class: 'visa thread'

     - Synchronized access
       The two threads agree, that before accessing data, the 'LOCK' has to be aquired.
       This is implement using @synchronized.
       Convention: The Labber GUI ONLY accesses methods with '_synq' in its name.
    """

    def __init__(self):
        self.dict_values_labber_thread_copy = {}
        super().__init__(daemon=True)
        self.ad = AdLowNoiseFloat2023()
        self.register_filter1: RegisterFilter1 = RegisterFilter1.SPS_97656
        self.ad_needs_reconnect: bool = False
        self._aquisition = Acquistion()
        self._stopping = False

    def run(self):
        """
        import numpy as np
        >>> np.array([1, 1, 0, 1], bool)
        array([ True,  True, False,  True])
        >>> np.nonzero(a)
        (array([0, 1, 3]),)
        >>> np.nonzero(a == 1)
        (array([0, 1, 3]),)
        >>> np.nonzero(a == 0)
        (array([2]),)

        >>> b = np.array([0, 0, 0, 0], bool)
        >>> np.nonzero(b == 1)
        (array([], dtype=int64),)
        >>> len(y[0])
        0
        """
        while True:
            pcb_params = PcbParams(
                input_Vp=1.0, register_filter1=self.register_filter1, resolution22=True
            )
            if TODO_REMOVE:
                logger.info(
                    f"connect with input_Vp={pcb_params.input_Vp:0.1f}V, SPS={self.register_filter1.name}"
                )
            self.ad_needs_reconnect = False
            # Read the jumper settings
            if TODO_REMOVE:
                logger.info(
                    f"TODO REMOVE self.ad.decoder.size()={self.ad.decoder.size()} Bytes"
                )
            logger.info("connect(): Start reconnect to update SPS.")
            self.ad.connect(pcb_params=pcb_params)
            logger.info("connect(): Done reconnect to update SPS.")
            self._aquisition.set_SPS(pcb_params.register_filter1)
            settings_program = self.ad.pcb_status.settings["PROGRAM"]
            REQUIRED_VERSION = "ad_low_noise_float_2023(0.3.10)"
            if (settings_program < REQUIRED_VERSION) or (
                len(settings_program) < len(REQUIRED_VERSION)
            ):
                raise ValueError(
                    f"Found '{settings_program}' but required at least '{REQUIRED_VERSION}'!"
                )

            for measurements in self.ad.iter_measurements_V(
                pcb_params=pcb_params, do_connect=False
            ):
                if self._stopping:
                    return
                if self.ad_needs_reconnect:
                    break

                def handle_state(measurements: MeasurementSequence) -> None:

                    if self._aquisition.state is State.CAPTURING:
                        if TODO_REMOVE:

                            logger.info(
                                f"TODO REMOVE self.ad.decoder.size()={self.ad.decoder.size()} Bytes"
                            )

                        self._aquisition.append(
                            measurements=measurements,
                            idx0_start=self.ad.decoder.size(),
                        )
                        if self._aquisition.found_raising_edge():
                            return

                handle_state(measurements)
                # logger.info(f"TODO REMOVE handle_state({self._aquisition.state.name})")

                def log_IN_disable_t(measurements: MeasurementSequence) -> None:
                    msg = f"adc_value_V={measurements.adc_value_V[0]:5.2f}->{measurements.adc_value_V[-1]:5.2f}"
                    msg += f" IN_disable={measurements.IN_disable[0]:d}->{measurements.IN_disable[-1]:d}"
                    msg += f" IN_t={measurements.IN_t[0]:d}->{measurements.IN_t[-1]:d}"
                    msg += f" state={self._aquisition.state.name}"
                    msg += f" decoder.size()={self.ad.decoder.size()//3:5d} Samples"
                    if self._aquisition.state is State.CAPTURING:
                        msg += f" samples={len(self._aquisition.capturer.IN_voltage)}"
                    logger.info(msg)

                if False:
                    log_IN_disable_t(measurements)

                def log_errors(measurements: MeasurementSequence):
                    error_codes = self.ad.pcb_status.list_errors(
                        error_code=measurements.errors, inclusive_status=True
                    )
                    elements = []
                    elements.append(f"{measurements.adc_value_V[-1]:0.2f}V")
                    elements.append(f"{len(measurements.adc_value_V)}")
                    if measurements.IN_disable is not None:
                        elements.append(f"IN_disable={measurements.IN_disable[-1]}")
                    if measurements.IN_t is not None:
                        elements.append(f"IN_t={measurements.IN_t[-1]}")
                    elements.append(f"{int(measurements.errors):016b}")
                    elements.append(f"{error_codes}")
                    print(" ".join(elements))

                if False:
                    log_errors(measurements)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0)
        self.ad.close()

    @synchronized
    def _tick(self) -> None:
        """
        Called by the thread: synchronized to make sure that the labber GUI is blocked
        """
        # self._visa_station.tick()
        # Create a copy of all values to allow access for the labber thread without any delay.
        # self.dict_values_labber_thread_copy = self._visa_station.dict_values.copy()

    @synchronized
    def wait_measurements(self) -> None:
        """
        This method will until the measurements are acquired.
        """
        if TODO_REMOVE:
            logger.info("TODO REMOVE wait_measurements() ENTER")
        self._aquisition.wait_for_acquisition()
        if TODO_REMOVE:
            logger.info("TODO REMOVE wait_measurements() LEAVE")

        CHANNEL_DISABLE.data = self._aquisition.capturer.IN_disable
        CHANNEL_T.data = self._aquisition.capturer.IN_t
        CHANNEL_VOLTAGE.data = self._aquisition.capturer.IN_voltage

    @synchronized
    def set_quantity_sync(self, quant_name: str, value):
        """
        Returns the new value.
        Returns None if quant.name does not match.
        """
        if quant_name == "sample_rate_SPS":
            before = self.register_filter1
            self.register_filter1 = RegisterFilter1.factory(value)
            assert isinstance(self.register_filter1, RegisterFilter1)
            if before != self.register_filter1:
                logger.info(
                    f"SPS changed from {before.name} to {self.register_filter1.name}: Requires reconnect to the AD pico."
                )
                self.ad_needs_reconnect = True
            return value

        if quant_name == "duration_max_s":
            value = max(0.001, value)
            value = min(1000, value)
            self._aquisition.duration_max_s = value
            return value

        return None

    @synchronized
    def get_quantity_sync(self, quant):
        if quant.name == "Input range":
            return self.ad.pcb_status.gain_from_jumpers

        if quant.name == "sample_rate_SPS":
            return self.register_filter1.name

        if quant.name == "duration_max_s":
            return self._aquisition.duration_max_s

        if quant.name == "out_timeout":
            return self._aquisition.out_timeout

        if quant.name == "out_falling":
            return self._aquisition.out_falling

        if quant.name == "out_raising":
            return self._aquisition.out_raising

        if quant.name == "out_falling_s":
            return self._aquisition.out_falling_s

        if quant.name == "out_enabled_s":
            return self._aquisition.out_enabled_s

        return None


def main_standalone():
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)
    logger_ad.setLevel(logging.DEBUG)

    thread = AdThread()
    if False:
        thread.run()
    if True:
        thread.start()
        time.sleep(2.0)
        print(40 * "=")
        thread.wait_measurements()


if __name__ == "__main__":
    main_standalone()
