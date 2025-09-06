"""
Based on
C:\Program Files\Labber\Drivers\Examples\SimpleSignalGenerator
"""

import sys
import logging
import numpy as np

import InstrumentDriver

import stimuli_utils
import logging_utils

logger = logging.getLogger("LabberDriver")

logging.basicConfig()
logger.setLevel(logging.DEBUG)

print(sys.version_info)


class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements a simple signal generator driver"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pico: stimuli_utils.PicoStimuli | None = None
        self.is_asynchron: bool = True

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

        logger.info(f"performSetValue({quant}, {value})")

        logging_utils.performSetValue(quant)

        if quant.name == "Synchron":
            synchron_text = quant.getValueString()
            self.is_asynchron = synchron_text == "ASYNCHRON"

        if quant.name == "Scenario":
            self.pico.run_scenario(round(value), is_asynchron=self.is_asynchron)

        return value

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
        quant.getValue()
