"""
This is a driver for
<this_repo>/testsetup_labber
"""

import sys
import logging

import InstrumentDriver

from ad_low_noise_float_2023.ad import LOGGER_NAME

import stimuli_utils
import logging_utils

logger = logging.getLogger(LOGGER_NAME)

logging.basicConfig()
logger.setLevel(logging.DEBUG)

print(sys.version_info)
stimuli_utils.assert_correct_python_version()

TODO_REMOVE = False


class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements a simple signal generator driver"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pico: stimuli_utils.PicoStimuli | None = None
        self.run_synchron: bool = False
        self.do_validate: bool = False

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        if self.pico is None:
            self.pico = stimuli_utils.PicoStimuli()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        if self.pico is not None:
            self.pico.close()
            self.pico = None

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # just return the value

        logger.info(f"performSetValue('{quant.name}', {value})")

        successfully_set = logging_utils.performSetValue(quant, value)
        if successfully_set:
            return value

        if quant.name == "Synchron":
            if value == "ASYNCHRON":
                if TODO_REMOVE:
                    logger.info("TODO REMOVE ASYNCHRON")
                self.run_synchron = False
                self.do_validate = False
            elif value == "SYNCHRON_DEBUG":
                if TODO_REMOVE:
                    logger.info("TODO REMOVE SYNCHRON_DEBUG")
                self.run_synchron = True
                self.do_validate = False
            elif value == "VALIDATE_DEBUG":
                self.run_synchron = True
                self.do_validate = True
            else:
                assert False, value
            return value

        if quant.name == "Scenario":
            if TODO_REMOVE:
                logger.info(f"TODO REMOVE self.run_synchron={self.run_synchron}")
            self.pico.run_scenario(
                scenario=round(value),
                run_synchron=self.run_synchron,
                do_validate=self.do_validate,
            )
            return value

        if quant.name == "Logging":
            logger.info("Logging severity not implemented yet")
            return value

        raise ValueError(f"Unknown quant.name '{quant.name}'!")

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        # if quant.name == 'Signal':
        #     # if asking for signal, start with getting values of other controls
        #     amp = self.getValue('Amplitude')
        #     freq = self.getValue('Frequency')
        #     phase = self.getValue('Phase')
        #     add_noise = self.getValue('Add noise')
        #     # calculate time vector from 0 to 1 with 1000 elements
        #     time = np.linspace(0,1,1000)
        #     signal = amp * np.sin(freq*time*2*np.pi + phase*np.pi/180.0)
        #     # add noise
        #     if add_noise:
        #         noise_amp = self.getValue('Noise amplitude')
        #         signal += noise_amp * np.random.randn(len(signal))
        #     # create trace object that contains timing info
        #     trace = quant.getTraceDict(signal, t0=0.0, dt=time[1]-time[0])
        #     # finally, return the trace object
        #     return trace
        # else:
        #     # for other quantities, just return current value of control
        #     return quant.getValue()

        # just return the quantity value
        return quant.getValue()
