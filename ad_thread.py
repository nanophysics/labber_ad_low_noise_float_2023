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

ADD_PRE_POST_SAMPLE = True
"""
Add a sample before the falling edge and a sample after the raising edge.
If not set, IN_disable looks very boring... (all samples are 0)
"""

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
        return Capturer.find_first(array_of_bool=array_of_bool, value_to_find=0)

    @staticmethod
    def find_first1(array_of_bool: np.ndarray) -> typing.Optional[int]:
        return Capturer.find_first(array_of_bool=array_of_bool, value_to_find=1)

    @staticmethod
    def find_first(
        array_of_bool: np.ndarray,
        value_to_find: int,
    ) -> typing.Optional[int]:
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
            logger.info(
                f"TOBE REMOVE find_first({len(array_of_bool)} value_to_find={value_to_find})"
            )
        if len(array_of_bool) == 0:
            if TODO_REMOVE:
                logger.info(
                    f"TOBE REMOVE find_first({len(array_of_bool)}) value_to_find={value_to_find}) A"
                )
            return None

        # Find first '0'
        array_nonzero = np.nonzero(array_of_bool == value_to_find)[0]
        if len(array_nonzero) == 0:
            if TODO_REMOVE:
                logger.info(
                    f"TOBE REMOVE find_first({len(array_of_bool)}) value_to_find={value_to_find}) B"
                )
            return None

        idx0_first = int(array_nonzero[0])
        if TODO_REMOVE:
            logger.info(
                f"TOBE REMOVE find_first({len(array_of_bool)}) value_to_find={value_to_find}) C idx0_first0={idx0_first}"
            )
        return idx0_first

    def limit_begin(self, idx0: int) -> None:
        self.IN_disable = self.IN_disable[idx0:]
        self.IN_t = self.IN_t[idx0:]
        self.IN_voltage = self.IN_voltage[idx0:]

    def limit_end(self, idx0: int) -> None:
        self.IN_disable = self.IN_disable[:idx0]
        self.IN_t = self.IN_t[:idx0]
        self.IN_voltage = self.IN_voltage[:idx0]


@dataclasses.dataclass
class Acquistion:
    state: State = State.ARMED
    capturer: typing.Optional[Capturer] = None
    time_armed_start_s: float = time.monotonic()
    done_event = threading.Event()
    lock = threading.Lock()
    _sps: float = 1.0
    timeout_detected: bool = False
    enable_start_detected: bool = False
    enable_end_detected: bool = False
    enable_start_s: float = 0.0
    enable_s: float = 0.0
    _duration_max_s = 4.2
    _duration_max_sample = 42
    _IN_disable_first_measurement = 1
    idx0_start_capturing: int = 0

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

    def wait_for_acquisition(self, idx0_start_capturing: int) -> None:
        """
        We capture a new shot.
        Reset the last shot and get ready.
        """
        with self.lock:
            self.capturer = None
            self.timeout_detected = False
            self.enable_start_detected = False
            self.enable_end_detected = False
            self.enable_start_s = 0.0
            self.enable_s = 0.0
            self.time_armed_start_s: float = time.monotonic()
            self.state = State.CAPTURING
            self.idx0_start_capturing = idx0_start_capturing
            self.done_event.clear()
        self.done_event.wait()

        logger.info(f"    {len(self.capturer.IN_voltage)}samples")
        logger.info(f"    {self._sps:0.0f}SPS")
        logger.info(f"    timeout_detected={self.timeout_detected}")
        logger.info(
            f"    enable_start_detected={self.enable_start_detected} enable_start_s={self.enable_start_s:0.3f}s"
        )
        logger.info(
            f"    enable_end_detected={self.enable_end_detected} enable_s={self.enable_s:0.3f}s"
        )

    def append(self, measurements: MeasurementSequence) -> None:
        with self.lock:
            if self.capturer is None:
                idx0_start_capturing = self.idx0_start_capturing
                self.capturer = Capturer(
                    IN_voltage=measurements.adc_value_V[idx0_start_capturing:],
                    IN_disable=measurements.IN_disable[idx0_start_capturing:],
                    IN_t=measurements.IN_t[idx0_start_capturing:],
                )
                logger.info(
                    f"{self.state.name} append({len(self.capturer.IN_voltage)}) idx0_start_capturing={idx0_start_capturing} of {len(measurements.adc_value_V)}"
                )
                return

            self.capturer.append(measurements=measurements)
            logger.info(f"{self.state.name} append({len(measurements.adc_value_V)})")

    def found_raising_edge(self) -> bool:
        if TODO_REMOVE:
            logger.info(self.capturer.IN_disable)
        if not self.enable_start_detected:
            # No 'falling edge' (enable_start_detected) yet
            idx0 = self.capturer.find_first0(self.capturer.IN_disable)
            if idx0 is not None:
                # We found a falling edge
                self.capturer.limit_begin(idx0=idx0 - (1 if ADD_PRE_POST_SAMPLE else 0))
                # Change the value temporarely to allow triggering of the raising edge
                self._IN_disable_first_measurement = self.capturer.IN_disable[0]
                self.capturer.IN_disable[0] = False
                self.enable_start_detected = True
                self.enable_start_s = idx0 / self._sps
                logger.info(
                    f"enable_start_detected: idx0={idx0} self._sps={self._sps} self.enable_start_s={self.enable_start_s:0.3f}s"
                )
                return False
        else:
            # Falling edge (enable_start_detected), now look for raising edge (enable_end_detected)
            idx0 = self.capturer.find_first1(self.capturer.IN_disable)
            if idx0 is not None:
                # We found a raising edge
                self.capturer.IN_disable[0] = self._IN_disable_first_measurement
                self.capturer.limit_end(idx0=idx0 + (1 if ADD_PRE_POST_SAMPLE else 0))
                self.enable_end_detected = True
                self.enable_s = idx0 / self._sps
                logger.info(
                    f"enable_end_detected: idx0={idx0} self._sps={self._sps} self.enable_s={self.enable_s:0.3f}s"
                )
                with self.lock:
                    self.state = State.ARMED
                    self._done()
                return False

        self.timeout_detected = (
            len(self.capturer.IN_disable) > self._duration_max_sample
        )
        if self.timeout_detected:
            self.capturer.IN_disable[0] = self._IN_disable_first_measurement
            logger.info(
                f"TIMEOUT {len(self.capturer.IN_disable)}({self._duration_max_sample})samples {self.duration_max_s:0.3f}s {self._sps}SPS"
            )
            with self.lock:
                self.state = State.ARMED
                self._done()
            return True

        return False


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
                scale_factor=1.0, register_filter1=self.register_filter1, resolution22=True
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
            REQUIRED_VERSION = "ad_low_noise_float_2023(0.3.11)"
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

                        self._aquisition.append(measurements=measurements)
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
    def wait_startup(self) -> None:
        """
        Wait for pico to connect and read all configuration
        """
        if TODO_REMOVE:
            logger.info("TODO REMOVE wait_startup() ENTER")
        next_msg_s = time.monotonic() + 20.0
        while not self.ad.connected:
            if next_msg_s > time.monotonic():
                logger.info("Waiting to be connected...")
                next_msg_s += 10.0
            time.sleep(0.5)
        if TODO_REMOVE:
            logger.info("TODO REMOVE wait_startup() LEAVE")

    @synchronized
    def wait_measurements(self) -> None:
        """
        This method will until the measurements are acquired.
        """
        if TODO_REMOVE:
            logger.info("TODO REMOVE wait_measurements() ENTER")
        self._aquisition.wait_for_acquisition(idx0_start_capturing=self.ad.decoder.size())
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

        if quant.name == "timeout_detected":
            return self._aquisition.timeout_detected

        if quant.name == "enable_start_detected":
            return self._aquisition.enable_start_detected

        if quant.name == "enable_end_detected":
            return self._aquisition.enable_end_detected

        if quant.name == "enable_start_s":
            return self._aquisition.enable_start_s

        if quant.name == "enable_s":
            return self._aquisition.enable_s

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
