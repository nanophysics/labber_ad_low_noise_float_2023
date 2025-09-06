import logging

logger = logging.getLogger("LabberDriver")


def performSetValue(quant):
    if quant.name == "Logging":
        logging_text = quant.getValueString()
        level = {
            "WARNING": logging.warning,
            "INFO": logging.INFO,
        }.get(logging_text, logging.DEBUG)
        logger.setLevel(level)
