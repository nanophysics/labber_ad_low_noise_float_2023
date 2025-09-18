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

logger = logging.getLogger("LabberDriver")
logger_ad = logging.getLogger(LOGGER_NAME)

LOCK = threading.Lock()


class State(enum.IntEnum):
    IDLE = enum.auto()
    ARMED = enum.auto()
    RECORD = enum.auto()


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
class Recorder:
    IN_voltage: list[np.array] = None
    # dataclasses.field(        default_factory=lambda: [np.array([], dtype=bool)]    )
    IN_disable: list[np.array] = None
    # dataclasses.field(        default_factory=lambda: [np.array([], dtype=bool)]    )
    IN_t: list[np.array] = None
    # dataclasses.field(        default_factory=lambda: [np.array([], dtype=float)]    )

    @staticmethod
    def start(measurements: MeasurementSequence, idx0_start: int) -> Recorder:
        return Recorder(
            IN_voltage=measurements.adc_value_V[idx0_start:],
            IN_disable=measurements.IN_disable[idx0_start:],
            IN_t=measurements.IN_t[idx0_start:],
        )

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

    def IN_disable_raising_edge(self) -> typing.Optional[int]:
        return self.find_raising_edge(self.IN_disable)

    @staticmethod
    def find_raising_edge(array_of_bool: np.ndarray) -> typing.Optional[int]:
        """
        Returns the first transition from 0 to 1. Returns the index of '1'.
        Returns None if no transition found.

        import numpy as np
        >>> high_low_high = np.array([1, 1, 0, 0, 1], bool)
        >>> low = np.nonzero(high_low_high == 0)[0]
        >>> low
        array([2, 3])
        >>> low[0]
        2
        """
        # Find first '0'
        array0 = np.nonzero(array_of_bool == 0)[0]
        if len(array0) == 0:
            return None
        idx0_first0 = array0[0]
        # From this position, find first '1'
        array1 = np.nonzero(array_of_bool[idx0_first0:])[0]
        if len(array1) == 0:
            return None
        idx0_first1 = array1[0]
        return idx0_first1


@dataclasses.dataclass
class Acquistion:
    state: State = State.IDLE
    recorder: Recorder | None = None
    time_armed_start_s: float = time.monotonic()
    done_event = threading.Event()
    lock = threading.Lock()

    def handle_timeout(self) -> bool:
        """
        Return True if timeout is over
        """
        duration_s = time.monotonic() - self.time_armed_start_s
        if duration_s > 5.0:
            logger.info(f"Timeout={duration_s:0.1f}s")
            self._done()
            return True
        return False

    def _done(self) -> None:
        self.done_event.set()
        self.state = State.IDLE

    def wait_for_acquisition(self) -> None:
        """
        We capture a new shot.
        Reset the last shot and get ready.
        """
        with self.lock:
            self.recorder = Recorder()
            self.time_armed_start_s: float = time.monotonic()
            self.state = State.ARMED
            self.done_event.clear()
        self.done_event.wait()

    def start(self, measurements: MeasurementSequence, idx0_start: int) -> None:
        with self.lock:
            self.state = State.RECORD
            self.recorder = Recorder.start(
                measurements=measurements, idx0_start=idx0_start
            )
            logger.info(
                f"{self.state.name} start({len(measurements.adc_value_V)}, idx0_start={idx0_start})"
            )

    def append(self, measurements: MeasurementSequence) -> None:
        with self.lock:
            self.recorder.append(measurements=measurements)
            logger.info(f"{self.state.name} append({len(measurements.adc_value_V)})")

    # def stop(self, measurements: MeasurementSequence, idx0_end: int) -> None:
    #     with self.lock:
    #         self.state = State.IDLE
    #         self.recorder.stop(measurements=measurements, idx0_end=idx0_end)
    #         self._done()
    #         logger.info(
    #             f"{self.state.name} stop({len(measurements.adc_value_V)}, idx0_end={idx0_end})"
    #         )

    def found_raising_edge(self) -> bool:
        idx = self.recorder.IN_disable_raising_edge()
        if idx is None:
            return False
        
        with self.lock:
            self.state = State.IDLE
            self._done()
            logger.info(
                f"{self.state.name} stop({len(measurements.adc_value_V)}, idx0_end={idx0_end})"
            )
        logger.info(f"found_raising_edge idx={idx})")
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
        self.duration_max_s = 5.0

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
            logger.info(
                f"connect with input_Vp={pcb_params.input_Vp:0.1f}V, SPS={self.register_filter1.name}"
            )
            self.ad_needs_reconnect = False
            # Read the jumper settings
            self.ad.connect(pcb_params=pcb_params)
            settings_program = self.ad.pcb_status.settings["PROGRAM"]
            REQUIRED_VERSION = "ad_low_noise_float_2023(0.3.6)"
            if settings_program < REQUIRED_VERSION:
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

                    if self._aquisition.state is State.ARMED:
                        logger.info("TODO REMOVE handle_state(ARMED)")
                        self._aquisition.start(
                            measurements=measurements,
                            idx0_start=self.ad.decoder.size(),
                        )
                        if False:
                            array_idx0_enabled = np.nonzero(measurements.IN_disable)[0]
                            if len(array_idx0_enabled) == 0:
                                logger.info(
                                    f"TODO REMOVE array_idx0_enabled={array_idx0_enabled}"
                                )
                                self._aquisition.handle_timeout()
                                return
                            idx0_enabled = array_idx0_enabled[0]
                            self._aquisition.start(
                                measurements=measurements,
                                idx0_start=idx0_enabled,
                            )
                        return

                    if self._aquisition.state is State.RECORD:
                        self._aquisition.append(measurements=measurements)
                        if self._aquisition.found_raising_edge():
                            return
                        self._aquisition.handle_timeout()
                        return
                        array_idx0_disabled = np.nonzero(measurements.IN_disable == 0)[
                            0
                        ]
                        if len(array_idx0_disabled) == 0:
                            self._aquisition.append(measurements=measurements)
                            self._aquisition.handle_timeout()
                            self._aquisition.found_raising_edge()
                            return

                        idx0_disabled = array_idx0_disabled[0]
                        self._aquisition.stop(
                            measurements=measurements,
                            idx0_end=idx0_disabled,
                        )

                handle_state(measurements)
                logger.info(f"TODO REMOVE handle_state({self._aquisition.state.name})")

                # l = self.ad.pcb_status.list_errors(error_code=errors, inclusive_status=True)
                # print(f"{adc_value_V[0]:0.2f}V, {int(errors):016b}, {l}")
                if False:
                    IN_disable = int(measurements.IN_disable[0])
                    IN_t = int(measurements.IN_t[0])
                    logger_ad.debug(
                        f"{int(measurements.errors):016b} measurements={len(measurements.adc_value_V):5d} IN_disable={IN_disable} IN_t={IN_t}"
                    )

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
        logger.info("TODO REMOVE wait_measurements() A")
        self._aquisition.wait_for_acquisition()
        logger.info("TODO REMOVE wait_measurements() C")

        CHANNEL_DISABLE.data = self._aquisition.recorder.IN_disable
        CHANNEL_T.data = self._aquisition.recorder.IN_t
        CHANNEL_VOLTAGE.data = self._aquisition.recorder.IN_voltage
        # dict_channels[]
        # for idx, channel in enumerate(dict_channels.values()):
        #     channel.data = np.array([1.0 * idx + i * 0.001 for i in range(12)])

    # @synchronized
    # def set_quantity_sync(self, quantity: Quantity, value):
    #     """
    #     Called by labber GUI
    #     """
    #     return self._visa_station.set_quantity(quantity=quantity, value=value)

    # @synchronized
    # def wait_till_ramped_sync(self):
    #     self._visa_station.wait_till_ramped()

    # def set_value(self, name: str, value):
    #     """
    #     Called by the tread (visa_station):
    #     Update a value which may be retrieved later by the labber GUI using 'get_quantity_sync'.
    #     """

    #     assert isinstance(name, str)
    #     quantity = Quantity(name)

    #     if quantity is Quantity.ControlWriteTemperatureAndSettle_K:
    #         return self._set_temperature_and_settle(quantity=quantity, value=value)

    #     return self.set_quantity_sync(quantity=quantity, value=value)

    # def _set_temperature_and_settle_obsolete(self, quantity: Quantity, value: float):
    #     assert quantity is Quantity.ControlWriteTemperatureAndSettle_K

    #     def block_until_settled():
    #         tick_count_before = self._visa_station.tick_count
    #         timeout_s = self._visa_station.time_now_s + self._visa_station.get_quantity(
    #             Quantity.ControlWriteTimeoutTime_S
    #         )
    #         while True:
    #             self._visa_station.sleep(TICK_INTERVAL_S / 2.0)
    #             if tick_count_before == self._visa_station.tick_count:
    #                 # Wait for a tick to make sure that the statemachine was called at least once
    #                 continue
    #             if not self._visa_station.hsm_heater.is_state(
    #                 HeaterHsm.state_connected_thermon_heatingcontrolled
    #             ):
    #                 # Unexpected state change
    #                 logger.info(
    #                     f"Waiting for 'ControlWriteTemperatureAndSettle_K'. Unexpected state change. Got '{self._visa_station.hsm_heater._state_actual}'!"
    #                 )
    #                 return
    #             if self._is_settled():
    #                 return
    #             if self._visa_station.time_now_s > timeout_s:
    #                 logger.info("Timeout while 'ControlWriteTemperatureAndSettle_K'")
    #                 return

    #     if abs(value - heater_wrapper.TEMPERATURE_SETTLE_OFF_K) < 1.0e-9:
    #         logger.warning(f"'{quantity.value}' set to {value:0.1f} K: SKIPPED")
    #         return

    #     self._visa_station.set_quantity(Quantity.ControlWriteTemperature_K, value)
    #     self._visa_station.hsm_heater.wait_temperature_and_settle_start()
    #     logger.warning(
    #         f"'{quantity.value}' set to {value:0.1f} K: Blocking. Timeout = {self._visa_station.get_quantity(Quantity.ControlWriteTimeoutTime_S)}s"
    #     )
    #     block_until_settled()
    #     self._visa_station.hsm_heater.wait_temperature_and_settle_over()
    #     logger.warning("Settle/Timeout time over")
    #     return heater_wrapper.TEMPERATURE_SETTLE_OFF_K

    @synchronized
    def set_quantity_sync(self, quant_name: str, value):
        """
        Returns the new value.
        Returns None if quant.name does not match.
        """
        if quant_name == "Sample rate SPS":
            self.register_filter1 = RegisterFilter1.factory(value)
            assert isinstance(self.register_filter1, RegisterFilter1)
            self.ad_needs_reconnect = True
            return value

        if quant_name == "duration max s":
            value = max(0.001, value)
            value = min(1000, value)
            self.duration_max_s = value
            return value

        return None

    @synchronized
    def get_quantity_sync(self, quant):
        if quant.name == "Input range":
            return self.ad.pcb_status.gain_from_jumpers

        if quant.name == "duration max s":
            return self.duration_max_s
        return None

    # def get_value(self, name: str):
    #     """
    #     This typically returns immedately as it accesses a copy of all values.
    #     Only in rare cases, it will delay for max 0.5s.
    #     """
    #     assert isinstance(name, str)
    #     quantity = Quantity(name)
    #     try:
    #         value = self.dict_values_labber_thread_copy[quantity]
    #     except KeyError:
    #         # Not all values are stored in the dictionary.
    #         # In this case we have to use the synchronized call.
    #         value = self.get_quantity_sync(quantity=quantity)
    #     if isinstance(value, enum.Enum):
    #         return value.value
    #     return value

    # @synchronized
    # def get_quantity_sync(self, quantity: Quantity):
    #     return self._visa_station.get_quantity(quantity=quantity)

    # @synchronized
    # def signal(self, signal):
    #     self._visa_station.signal(signal)

    # @synchronized
    # def expect_state(self, expected_meth):
    #     self._visa_station.expect_state(expected_meth=expected_meth)


def main_standalone():
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)
    logger_ad.setLevel(logging.DEBUG)

    thread = AdThread()
    thread.run()
    # adc = AdLowNoiseFloat2023()

    # pcb_params=PcbParams(input_Vp=1.0)

    # for _adc_value_V in adc.iter_measurements_V(pcb_params=pcb_params):
    #     pass
    #     # print(len(_adc_value_V))


if __name__ == "__main__":
    main_standalone()
