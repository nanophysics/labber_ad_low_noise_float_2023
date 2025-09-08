# pylint: disable=dangerous-default-value
import sys
import logging
import typing

import InstrumentDriver  # pylint: disable=import-error
import numpy as np

import ad_utils
import ad_thread
import logging_utils

logger = logging.getLogger("LabberDriver")

logging.basicConfig()
logger.setLevel(logging.DEBUG)

print(sys.version_info)

assert sys.version_info.major == 3, sys.version_info
assert sys.version_info.minor == 7, sys.version_info
assert sys.version_info.micro == 9, sys.version_info


class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements the AMI430 driver"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread: typing.Optional[ad_thread.AdThread] = None
        self.dt: float = 1.0
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

    # @property
    # def station(self) -> Station:
    #     return self._thread.station

    # @property
    # def visa_station(self) -> AMI430_visa.VisaStation:
    #     return self._thread.visa_station

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        assert self._thread is not None

        self._thread.stop()
        self._thread = None

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of multiple calls, to set multiple voltages efficiently

        logging_utils.performSetValue(quant)

        if self.isFirstCall(options):
            logger.info(f"********** FIRST CALL '{quant.name}' {value}: {options}")

        self._thread.set_quantity(quant_name=quant.name, value=value)

        return value

        # try:
        #     quantity = Quantity(quant.name)
        #     value_new = self._thread.set_quantity_sync(quantity=quantity, value=value)
        #     if quantity in (
        #         Quantity.ControlSetpointX,
        #         Quantity.ControlSetpointY,
        #         Quantity.ControlSetpointZ,
        #         Quantity.ControlHoldCurrent,
        #         Quantity.ControlHoldSwitchheaterOn,
        #     ):
        #         self._ramping_required = True

        #     if self.isFinalCall(options):
        #         if self.visa_station._mode is AMI430_visa.ControlMode.RAMPING_WAIT:
        #             if self._ramping_required:
        #                 self._ramping_required = False
        #                 logger.info(
        #                     f"********** FINAL CALL {quant.name} {value}: {options}"
        #                 )
        #                 self._thread.wait_till_ramped_sync()
        #                 logger.info(
        #                     f"********** FINAL CALL DONE {quant.name} {value}: {options}"
        #                 )

        #     return value_new
        # except:
        #     print(" ???", quant.name, value)
        #     pass

        # logger.error(f"performSetValue: Unknown quantity '{quant.name}' {value}")
        # # if quant.name == "Control / Field target":
        # #     raise

    def checkIfSweeping(self, quant):
        """Always return false, sweeping is done in loop"""
        return False

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # only implmeneted for geophone voltage
        logger.debug(f"performGetValue({quant.name})")

        channel = self.dict_channels.get(quant.name, None)
        if channel is not None:
            isFirstCall = self.isFirstCall(options)
            logger.debug(f"performGetValue({quant.name}): isFirstCall {isFirstCall}")

            # check if first call, if so get new traces
            if isFirstCall:
                self.getTraces()

            # return correct data
            return quant.getTraceDict(channel.data, dt=self.dt)

        # just return the quantity value
        return quant.getValue()

    def getTraces(self):
        """Resample the data"""

        duration_max_s = float(self.getValue("duration max s"))
        sample_rate_sps_text = self.getValue("Sample rate SPS")
        sample_rate_sps = 97656  # TODO
        sample_count = int(duration_max_s * sample_rate_sps)

        for idx, channel in enumerate(self.dict_channels.values()):
            channel.data = np.array(
                [1.0 * idx + i * 0.001 for i in range(sample_count)]
            )

        self.dt = 1.0 / sample_rate_sps

        # data = self.mAI.readAll()
        # # put data in list of channels
        # for key, data in data.items():
        #     indx = self.lChName.index(key)
        #     self.lTrace[indx] = data
        # self.dt = 1.0/self.getValue('Sample rate')

        # try:
        #     quantity = Quantity(quant.name)
        # except:
        #     raise Exception("performGetValue(): Unknown quant.name={quant.name} ")

        # try:
        #     value = self._thread.get_quantity_sync(quantity=quantity)
        #     return value
        # except:
        #     raise Exception(
        #         f"performGetValue(): Failed to get_quantity_sync(quantity={quantity}) "
        #     )
