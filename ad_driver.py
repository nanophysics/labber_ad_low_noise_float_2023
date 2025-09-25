# pylint: disable=dangerous-default-value
import sys
import time
import logging
import typing

import InstrumentDriver  # pylint: disable=import-error
import numpy as np

from ad_low_noise_float_2023.ad import LOGGER_NAME
from ad_low_noise_float_2023.constants import PcbParams, RegisterFilter1

import ad_utils
import ad_thread
import logging_utils

logger = logging.getLogger("LabberDriver")
logger_ad = logging.getLogger(LOGGER_NAME)

logging.basicConfig()
logger.setLevel(logging.DEBUG)
logger_ad.setLevel(logging.DEBUG)

print(sys.version_info)

assert sys.version_info.major == 3, sys.version_info
assert sys.version_info.minor == 7, sys.version_info
assert sys.version_info.micro == 9, sys.version_info


class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements the AMI430 driver"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread: typing.Optional[ad_thread.AdThread] = None
        # self._thread: AMI430_thread.VisaThread = None
        # self._ramping_required = True
        self.dict_channels = {ch.label: ch for ch in ad_utils.CHANNELS}


    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        # Reset the usb connection (it must not change the applied voltages)
        self.log("labber_ad_low_noise_float_2023 Driver")
        # station = AMI430_driver_config.get_station()
        assert self._thread is None
        self._thread = ad_thread.AdThread()
        self._thread.start()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        assert self._thread is not None

        self._thread.stop()
        self._thread = None

    # def performSetValue(self, quant, value, sweepRate=0.0, options={}):
    #     begin_s = time.monotonic()
    #     rc = self._performSetValue(quant=quant, value=value, sweepRate=sweepRate, options=options)
    #     logger.info(f"performSetValue('{quant.name}') returned. {time.monotonic()-begin_s:0.2f}s")
    #     return rc

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        begin_s = time.monotonic()

        value_before = self.getValue(quant.name)

        new_value = logging_utils.performSetValue(quant, value)
        if new_value is None:
            new_value = self._thread.set_quantity_sync(quant_name=quant.name, value=value)
            if new_value is None:
                logger.warning(f"Nobody was setting '{quant.name}'...")

        first_call = "FIRST" if self.isFirstCall(options) else ""
        logger.info(f"performSetValue('{quant.name}', {value_before} -> {new_value}) {first_call} {time.monotonic()-begin_s:0.2f}s")

        return new_value


    def checkIfSweeping(self, quant):
        """Always return false, sweeping is done in loop"""
        return False

    def performGetValue(self, quant, options={}):
        begin_s = time.monotonic()
        rc = self._performGetValue(quant=quant, options=options)
        logger.info(f"performGetValue('{quant.name}') returned {time.monotonic()-begin_s:0.2f}s")
        return rc
    
    def _performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # only implmeneted for geophone voltage
        isFirstCall = self.isFirstCall(options)
        first_call = "FIRST" if isFirstCall else ""
        logger.info(f"performGetValue('{quant.name}') {first_call}")

        value = self._thread.get_quantity_sync(quant)
        if value is not None:
            return value
        
        channel = self.dict_channels.get(quant.name, None)
        if channel is not None:
            # check if first call, if so get new traces
            if isFirstCall:
                self.wait_trigger()

            # return correct data
            return quant.getTraceDict(channel.data, dt=1.0/self._thread._aquisition._sps)

        # just return the quantity value
        return quant.getValue()

    def wait_trigger(self):
        """Resample the data"""

        logger.info("TODO REMOVE wait_measurements() ENTERING")
        self._thread.wait_measurements()
        logger.info("TODO REMOVE wait_measurements() LEAVING")
        return

        # logger.info("Sleep 7s")
        # time.sleep(7)
        
        # duration_max_s = float(self.getValue("duration_max_s"))
        # sample_rate_sps_text = self.getValue("sample_rate_SPS")
        sample_rate_sps = 97656  # TODO
        # sample_count = int(duration_max_s * sample_rate_sps)

        for idx, channel in enumerate(self.dict_channels.values()):
            channel.data = np.array(
                [1.0 * idx + i * 0.001 for i in range(sample_count)]
            )

        # self.dt = 1.0 / sample_rate_sps
