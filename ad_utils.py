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


CHANNELS = [
    Channel("IN_t"),
    Channel("IN_disable"),
    Channel("IN_P"),
    Channel("IN_N"),
]
