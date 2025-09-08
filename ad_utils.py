import dataclasses
import numpy as np


class DriverAbortException(Exception):
    pass


@dataclasses.dataclass()
class Channel:
    label: str
    data: np.array = dataclasses.field(default_factory=lambda: np.array([]))

    def reset(self) -> None:
        self.data.clear()


CHANNEL_T = Channel("IN_t")
CHANNEL_DISABLE = Channel("IN_disable")
CHANNEL_VOLTAGE = Channel("IN_voltage")
CHANNELS = [
    CHANNEL_T,
    CHANNEL_DISABLE,
    CHANNEL_VOLTAGE,
]
