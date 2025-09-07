from __future__ import annotations
import time
import logging
import threading
import typing
import enum
import re
import dataclasses
import serial
import serial.tools.list_ports

import ad_low_noise_float_2023_decoder
from constants_ad_low_noise_float_2023 import     RegisterFilter1,    RegisterMux


import numpy as np

import ad_utils

TICK_INTERVAL_S = 0.5

logger = logging.getLogger("LabberDriver")

LOCK = threading.Lock()


def synchronized(func):
    def wrapper(*args, **kwargs):
        with LOCK:
            try:
                return func(*args, **kwargs)
            except:  # pylint: disable=bare-except
                logger.exception('Exception in method "HeaterThread.%s"', func.__name__)
                raise

    return wrapper


class UsbThread(threading.Thread):
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
        # self._visa_station = AMI430_visa.VisaStation(station=station)
        # logger.info(f"LabberThread(config='{self.station.name}')")
        self._stopping = False
        # self._visa_station.open()
        self.start()

    # @property
    # def station(self) -> Station:
    #     return self._visa_station.station

    # @property
    # def visa_station(self) -> AMI430_visa.VisaStation:
    #     return self._visa_station

    def run(self):
        while not self._stopping:
            start_s = time.time()
            try:
                self._tick()
            except ad_utils.DriverAbortException as ex:
                logger.error(f"ad_utils.DriverAbortException(): {ex}")
                logger.exception(ex)
                raise

            except Exception as ex:
                # Log the error but keep running
                logger.exception(ex)

            elapsed_s = time.time() - start_s
            if elapsed_s > TICK_INTERVAL_S:
                logger.warning(
                    f"tick() took:{elapsed_s:0.3f}s. Expected <= {TICK_INTERVAL_S:0.3f}s"
                )
            time.sleep(TICK_INTERVAL_S)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0)

    @synchronized
    def _tick(self) -> None:
        """
        Called by the thread: synchronized to make sure that the labber GUI is blocked
        """
        self._visa_station.tick()
        # Create a copy of all values to allow access for the labber thread without any delay.
        # self.dict_values_labber_thread_copy = self._visa_station.dict_values.copy()

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

    # @synchronized
    # def set_quantity(self, quantity: Quantity, value):
    #     return self._visa_station.set_quantity(quantity=quantity, value=value)

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


RE_STATUS_BYTE_MASK = re.compile(r"STATUS_BYTE_MASK=0x(\w+)")


class OutOfSyncException(Exception):
    pass


@dataclasses.dataclass
class BcbStatus:
    """
    status: BEGIN=1
    status: PROGRAM=ad_low_noise_float_2023(0.3.3)
    status: REGISTER_FILTER1=0x02
    status: REGISTER_MUX=0x00
    status: SEQUENCE_LEN_MIN=1000
    status: SEQUENCE_LEN_MAX=30000
    status: ERROR_MOCKED=1
    status: ERROR_MOCKED=1
    status: ERROR_ADS127_MOD=2
    status: ERROR_ADS127_ADC=4
    status: ERROR_FIFO=8
    status: ERROR_ADS127_SPI=16
    status: ERROR_ADS127_POR=32
    status: ERROR_ADS127_ALV=64
    status: ERROR_OVLD=128
    status: ERROR_STATUS_J42=256
    status: ERROR_STATUS_J43=512
    status: ERROR_STATUS_J44=1024
    status: ERROR_STATUS_J45=2048
    status: ERROR_STATUS_J46=4096
    status: END=1
    """

    settings: dict[str, str] = dataclasses.field(default_factory=dict)
    error_codes: dict[int, str] = dataclasses.field(default_factory=dict)

    def add(self, line: str) -> None:
        key, value = line.split("=", 1)
        self.add_setting(key.strip(), value.strip())

    def add_setting(self, key: str, value: str) -> None:
        assert isinstance(key, str)
        assert isinstance(value, str)
        self.settings[key] = value

        if key.startswith("ERROR_"):
            try:
                value_int = int(value, 0)
                bit_position = 0
                while value_int > 1:
                    value_int >>= 1
                    bit_position += 1
                self.error_codes[bit_position] = key
            except ValueError:
                logger.warning(f"Invalid error code: {key}={value}")

    def validate(self) -> None:
        assert self.settings["BEGIN"] == "1"
        assert self.settings["END"] == "1"

    def list_errors(self, error_code: int, inclusive_status: bool) -> list[str]:
        """
        Returns a list of error messages for the given error code.
        """
        assert isinstance(error_code, int)
        # return a list of bit positions which are set in error_code
        error_bits = [i for i in range(32) if (error_code & (1 << i)) != 0]

        error_strings = [self.error_codes[bit_position] for bit_position in error_bits]
        if not inclusive_status:
            error_strings = [
                x for x in error_strings if not x.startswith("ERROR_STATUS_")
            ]
        return error_strings

    @property
    def gain_from_jumpers(self) -> float:
        status_J42_J46 = int(self.settings["STATUS_J42_J46"], 0)
        status_J42_J43 = status_J42_J46 & 0b11
        return {
            0: 1.0,
            1: 2.0,  # J42
            2: 5.0,  # J43
            3: 10.0,  # J42, J43
        }[status_J42_J43]


class Adc:
    PRINTF_INTERVAL_S = 10.0
    VID = 0x2E8A
    PID = 0x4242
    MEASURMENT_BYTES = 3
    COMMAND_START = "s"
    COMMAND_STOP = "p"
    COMMAND_MOCKED_ERROR = "e"
    COMMAND_MOCKED_CRC = "c"

    SEQUENCE_LEN_MAX = 30_000
    BYTES_PER_MEASUREMENT = 3
    DECODER_OVERFLOW_SIZE = 4 * BYTES_PER_MEASUREMENT * SEQUENCE_LEN_MAX

    def __init__(self) -> None:
        self.serial = self._open_serial()
        self.success: bool = False
        self.pcb_status = BcbStatus()
        self.decoder = ad_low_noise_float_2023_decoder.Decoder()

    def _open_serial(self) -> serial.Serial:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == self.VID:
                if port.pid == self.PID:
                    return serial.Serial(port=port.device, timeout=1.0)

        raise ValueError(
            f"No board with VID=0x{self.VID:02X} and PID=0x{self.PID:02X} found!"
        )

    def close(self) -> None:
        self.serial.close()

    def drain(self) -> None:
        while True:
            line = self.serial.read()
            if len(line) == 0:
                return

    def read_status(self) -> bool:
        self.success, self.pcb_status = self._read_status_inner()
        self.pcb_status.validate()
        return self.success

    def _read_status_inner(self) -> tuple[bool, BcbStatus]:
        """
        return True on success
        """
        status = BcbStatus()
        while True:
            line_bytes = self.serial.readline()
            if len(line_bytes) == 0:
                return False, status
            line = line_bytes.decode("ascii").strip()
            status.add(line)
            logger.info(f"  status: {line}")
            if line == "END=1":
                return True, status

    def test_usb_speed(self) -> None:
        begin_ns = time.monotonic_ns()
        counter = 0
        while True:
            measurements = self.serial.read(size=1_000_000)
            # print(f"len={len(measurements)/3}")
            self.decoder.push_bytes(measurements)

            while True:
                numpy_array = self.decoder.get_numpy_array()
                if numpy_array is None:
                    print(".", end="")
                    break
                if self.decoder.get_crc() != 0:
                    logger.error(f"ERROR crc={self.decoder.get_crc()}")
                if self.decoder.get_errors() not in (0, 8, 72):
                    logger.error(f"ERROR errors={self.decoder.get_errors()}")

                counter += len(numpy_array)
                duration_ns = time.monotonic_ns() - begin_ns
                logger.info(f"{1e9 * counter / duration_ns:0.1f} SPS")

                # counter += len(measurements) // 3
                # duration_ns = time.monotonic_ns() - begin_ns
                # print(f"{1e9*counter/duration_ns:0.1f} SPS")

        # Pico:197k  PC Peter 96k (0.1% CPU auslasung)

    def iter_measurements(self) -> typing.Iterable[np.ndarray]:
        while True:
            measurements = self.serial.read(size=1_000_000)
            # print(f"len={len(measurements)/3}")
            self.decoder.push_bytes(measurements)

            while True:
                adc_value_ain_signed32 = self.decoder.get_numpy_array()
                if adc_value_ain_signed32 is None:
                    # print(".", end="")
                    if self.decoder.size() > self.DECODER_OVERFLOW_SIZE:
                        msg = "f'Segment overflow! decoder.size {self.decoder.size()} > DECODER_OVERFLOW_SIZE {self.DECODER_OVERFLOW_SIZE}'"
                        # print(msg)
                        raise OutOfSyncException(msg)
                    break
                # counter += len(adc_value_ain_signed32)
                if self.decoder.get_crc() != 0:
                    msg = f"ERROR crc={self.decoder.get_crc()}"
                    # print(msg)
                    raise OutOfSyncException(msg)

                errors = self.decoder.get_errors()
                error_strings = self.pcb_status.list_errors(
                    errors,
                    inclusive_status=False,
                )
                if len(error_strings) > 0:
                    msg = f"ERROR: {errors}: {' '.join(error_strings)}"
                    logger.error(msg)

                # duration_s = time.monotonic() - begin_s
                # if duration_s > self.PRINTF_INTERVAL_S:
                #     print(
                #         f"{adc_value_ain_signed32[0]=:2.6f}  {counter/duration_s:0.1f} SPS"
                #     )
                #     begin_s = time.monotonic()
                #     counter = 0

                yield adc_value_ain_signed32


def main_standalone():
    def _send_command_reset():
        msg = f"send command reset: {RegisterFilter1.SPS_97656!r} {RegisterMux.NORMAL_INPUT_POLARITY!r}"
        logger.info(msg)
        additional_SPI_reads = 0
        command_reset = f"r-{RegisterFilter1.SPS_97656:02X}-{RegisterMux.NORMAL_INPUT_POLARITY:02X}-{additional_SPI_reads:d}"
        _send_command(command_reset)

    def _send_command(command: str) -> None:
        logger.info(f"send command: {command}")
        command_bytes = f"\n{command}\n".encode("ascii")
        adc.serial.write(command_bytes)

    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    adc = Adc()

    _send_command(Adc.COMMAND_STOP)
    adc.drain()
    _send_command_reset()
    adc.read_status()
    _send_command(Adc.COMMAND_START)
    while True:
            try:
                for adc_value_ain_signed32 in adc.iter_measurements():
                    print(len(adc_value_ain_signed32))
            except OutOfSyncException as e:
                logger.error(f"OutOfSyncException: {e}")
                bytes_purged = adc.decoder.purge_until_and_with_separator()
                logger.info(f"Purged {bytes_purged} bytes!")

                # self.connect()

if __name__ == "__main__":
    main_standalone()
