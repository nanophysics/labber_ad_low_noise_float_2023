import sys
import pathlib
import logging

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent

REQUIRED_PYTHON_VERSION = (3, 7, 9)
PYTHON_VERSION = (
    sys.version_info.major,
    sys.version_info.minor,
    sys.version_info.micro,
)


def assert_correct_python_version():
    if PYTHON_VERSION != REQUIRED_PYTHON_VERSION:
        raise Exception(
            f"Python version {REQUIRED_PYTHON_VERSION} is required but found version {PYTHON_VERSION}"
        )


try:
    import mp
    import mp.version
    import mp.micropythonshell
    import mp.pyboard_query
except ModuleNotFoundError:
    raise Exception(
        'The module "mpfshell2" is missing. Did you call "pip -r requirements_stimuli.txt"?'
    )

REQUIRED_MPFSHELL_VERSION = "100.9.17"
if mp.version.FULL > REQUIRED_MPFSHELL_VERSION:
    raise Exception(
        f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!'
    )

DIRECTORY_MICROPYTHON = DIRECTORY_OF_THIS_FILE / "stimuli_src_micropython"
assert (
    DIRECTORY_MICROPYTHON.is_dir()
), f"Directory does not exist: {DIRECTORY_MICROPYTHON}"


class PicoStimuli:
    def __init__(self):
        logger.info("Connecting to pico...")
        self.board: mp.pyboard_query.Board = mp.pyboard_query.ConnectHwtypeSerial(
            product=mp.pyboard_query.Product.RaspberryPico
        )

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
        rc = self.fe.execfile(filename)
        logger.info(f"micropython returned: {rc}")

    def _exec_raw(self, command: str) -> None:
        logger.info(f"micropython _exec_raw('{command}')")
        data, data_err = self.fe.exec_raw(command)
        msg = f"micropython _exec_raw('{command}') returned: data={data}, data_err={data_err}"
        logger.info(msg)
        if len(data_err) >0:
            raise ValueError(msg)
        
    def _exec_raw_with_exception_handler(self, command: str) -> None:
        try:
            self._exec_raw(command)
        except BaseException as e:
            msg = f"micropython exec failed: {command}"
            logger.error(msg)
            logger.exception(e)
            raise


    def run_scenario(
        self,
        scenario: int,
        run_synchron: bool,
        do_validate: bool,
    ) -> None:
        filename = DIRECTORY_MICROPYTHON / f"scenario_{scenario:02d}.py"
        logger.info(
            f"run_scenario(scenario={scenario}, run_synchron={run_synchron}, do_validate={do_validate})"
        )

        if not filename.is_file():
            msg = f"Scenario does not exist: {filename}"
            logger.error(msg)
            return
            # raise ValueError(msg)

        try:
            self._execfile(filename)
        except BaseException as e:
            msg = f"micropython execfile() failed: {filename}"
            logger.error(msg)
            logger.exception(e)
            raise

        self._exec_raw_with_exception_handler( "run_scenario(run_synchron=True, do_validate=True)")

        self._exec_raw_with_exception_handler(f"run_scenario(run_synchron={run_synchron}, do_validate={do_validate})")

    def close(self):
        self.board.close()
