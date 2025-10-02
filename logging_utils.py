import logging
import enum
from ad_low_noise_float_2023.ad import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class EnumMixin:
    def eq(self, other):
        assert isinstance(other, type(self))
        return self == other

    @classmethod
    def all_text(cls):
        return ", ".join(sorted([f'"{d.name}"' for d in cls]))

    @classmethod
    def get_exception(cls, value: str):
        assert isinstance(value, str)
        err = f'Unkown "{value}". Expect one of {cls.all_text()}!'
        try:
            return cls[value]
        except KeyError as e:
            raise Exception(err) from e

class EnumLogging(EnumMixin, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"

    def getLoggingLevel(self):
        return {
            EnumLogging.DEBUG: logging.DEBUG,
            EnumLogging.INFO: logging.INFO,
            EnumLogging.WARNING: logging.WARNING,
        }[self]

def performSetValue(quant, value):
    """
    Returns the new value.
    Returns None if quant.name does not match.
    """
    logging.debug(f"value={repr(value)}")
    if quant.name == "Logging Driver":
        # logging_text = quant.getValueString()
        logger_labber = logging.getLogger("LabberDriver")
        logging_level = EnumLogging.get_exception(value)
        logger_labber.setLevel(logging_level.getLoggingLevel())
        return value

    if quant.name == "Logging AD":
        # logging_text = quant.getValueString()
        logging_level = EnumLogging.get_exception(value)
        logger.setLevel(logging_level.getLoggingLevel())
        return value

    return None
