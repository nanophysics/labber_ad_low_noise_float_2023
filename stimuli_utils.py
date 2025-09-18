import sys
import enum
import pathlib
import logging

logger = logging.getLogger('LabberDriver')

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent

REQUIRED_PYTHON_VERSION=(3, 7, 9)
PYTHON_VERSION=(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
if PYTHON_VERSION != REQUIRED_PYTHON_VERSION:
    raise Exception(f'Python version {REQUIRED_PYTHON_VERSION} is required but found version {PYTHON_VERSION}')

try:
    import mp
    import mp.version
    import mp.micropythonshell
    import mp.pyboard_query
except ModuleNotFoundError:
    raise Exception('The module "mpfshell2" is missing. Did you call "pip -r requirements_stimuli.txt"?')

REQUIRED_MPFSHELL_VERSION='100.9.17'
if mp.version.FULL > REQUIRED_MPFSHELL_VERSION:
    raise Exception(f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!')

DIRECTORY_MICROPYTHON = DIRECTORY_OF_THIS_FILE / 'stimuli_src_micropython'
assert DIRECTORY_MICROPYTHON.is_dir(), f"Directory does not exist: {DIRECTORY_MICROPYTHON}"

class PicoStimuli:
    def __init__(self):
        logger.info("Connecting to pico...")
        self.board: mp.pyboard_query.Board = mp.pyboard_query.ConnectHwtypeSerial(product=mp.pyboard_query.Product.RaspberryPico)

        self.shell = self.board.mpfshell
        self.fe = self.shell.MpFileExplorer
        # Download the source code
        # self.shell.sync_folder(DIRECTORY_OF_THIS_FILE / 'stimuli_src_micropython', FILES_TO_SKIP=['config_identification.py'])
        # # Start the program
        # self.fe.exec_('import micropython_logic')
        self._execfile(DIRECTORY_MICROPYTHON / "init.py")

        logger.info("Connected to pico!")

    def _execfile(self, filename: pathlib.Path) -> None:
        logger.info(f"micropython execfile: {filename}")
        try:
            rc = self.fe.execfile(filename)
            logger.info(f"micropython returned: {rc}")
        except BaseException as e:
            logger.error(f"micropython execfile failed: {filename}")
            logger.exception(e)

    def _exec_raw(self, command: str) -> None:
        logger.info(f"micropython exec: {command}")
        try:
            rc = self.fe.exec_raw(command)
            logger.info(f"micropython returned: {rc}")
        except BaseException as e:
            logger.error(f"micropython exec failed: {command}")
            logger.exception(e)

    def run_scenario(self, scenario: int, is_asynchron: bool) -> None:
        filename = DIRECTORY_MICROPYTHON / f"scenario_{scenario:02d}.py"
        logger.info(f"run_scenario({scenario})")
        
        if not filename.is_file():
            msg = f"Scenario does not exist: {filename}"
            logger.error(msg)
            return
            # raise ValueError(msg)

        self._execfile(filename)

        if is_asynchron:
            self._exec_raw('run_scenario_on_second_thread()')
        else:
            self._exec_raw('run_scenario()')

    def close(self):
        self.board.close()
