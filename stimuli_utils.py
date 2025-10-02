import sys
import time
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

MICROYPTHON_EXEC_TIMEOUT_S = 65


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

REQUIRED_MPFSHELL_VERSION = "100.9.24"
if mp.version.FULL < REQUIRED_MPFSHELL_VERSION:
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
        logger.info(f"micropython execfile: {filename.name}")
        rc = self.fe.execfile(filename)
        logger.info(f"micropython execfile: {filename.name} returned {rc}")

    def _exec_raw(self, command: str) -> None:
        logger.info(f"micropython _exec_raw('{command}')")
        data, data_err = self.fe.exec_raw(command, timeout=MICROYPTHON_EXEC_TIMEOUT_S)
        msg = f"micropython _exec_raw('{command}') returned: data={data}, data_err={data_err}"
        logger.info(msg)
        if len(data_err) > 0:
            raise ValueError(msg)

    def _exec_raw_with_exception_handler(self, command: str) -> None:
        try:
            self._exec_raw(command)
        except BaseException as e:
            msg = f"micropython exec failed: {command}"
            logger.error(msg)
            logger.exception(e)
            raise

    def _find_scenario(self, scenario: int) -> pathlib.Path:
        pattern = f"scenario_{scenario:02d}*.py"
        for _filename in DIRECTORY_MICROPYTHON.glob(pattern=pattern):
            return _filename

        msg = f"Scenario does not exist: {pattern}"
        logger.error(msg)
        return None

    def _wait_for_second_core(self) -> None:
        begin_s = time.monotonic()
        while True:
            ret = self.fe.eval("second_core_is_ready()")
            duration_s = time.monotonic() - begin_s
            if duration_s > 10.0:
                logger.info(f"_wait_for_second_core() returned after {duration_s:0.1f}s")
            if ret == b"True":
                return
            if duration_s > 65.0:
                msg = f"Second core not ready after {duration_s:0.1f}s. Powercycle the stimuli-pico!"
                logger.error(msg=msg)
                raise ValueError(msg)
            time.sleep(10)

    def run_scenario(
        self,
        scenario: int,
        run_synchron: bool,
        do_validate: bool,
    ) -> None:

        filename = self._find_scenario(scenario=scenario)
        if filename is None:
            msg = f"Scenario does not exist: {filename}"
            logger.error(msg)
            # return
            raise ValueError(msg)

        logger.info(
            f"run_scenario(scenario={scenario}, run_synchron={run_synchron}, do_validate={do_validate}): {filename.name}"
        )

        try:
            self._execfile(filename)
        except BaseException as e:
            msg = f"micropython execfile() failed: {filename.name}"
            logger.error(msg)
            logger.exception(e)
            raise

        self._wait_for_second_core()

        self._exec_raw_with_exception_handler(
            "run_scenario(run_synchron=True, do_validate=True)"
        )

        self._exec_raw_with_exception_handler(
            f"run_scenario(run_synchron={run_synchron}, do_validate={do_validate})"
        )

    def close(self):
        self.board.close()
