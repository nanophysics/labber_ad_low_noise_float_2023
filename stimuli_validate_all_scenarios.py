from __future__ import annotations
import time
import enum
import logging
import threading
import dataclasses
import typing
import stimuli_utils

def main_standalone():
    """
    TODO: Could not make this running as mpfshell2 does not run anymore on python 3.15.

    A)
    $ uv pip install micropython-telnetlib           
        Using Python 3.13.5 environment at: C:\Projekte\ETH\ETH-labber_ad_low_noise_float_2023\gits\ad_low_noise_float_2023_git\.venv                                      
        × Failed to download and build `micropython-telnetlib==0.0.1`
        ╰─▶ C:\Users\maerki\AppData\Local\uv\cache\sdists-v9\pypi\micropython-telnetlib\0.0.1\mjCZfMMvjjKx-cuf12f42\src does not appear to be a Python project, as       
            neither `pyproject.toml` nor `setup.py` are present in the directory

    See: https://github.com/threat9/routersploit/issues/860

    B)
        File "c:\Users\maerki\.vscode\extensions\ms-python.debugpy-2025.10.0-win32-x64\bundled\libs\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_runpy.py", line 118, in _run_code
            exec(code, run_globals)
            ~~~~^^^^^^^^^^^^^^^^^^^
        File "stimuli_validate_all_scenarios.py", line 8, in <module>
            import stimuli_utils
        File "C:\Projekte\ETH\ETH-labber_ad_low_noise_float_2023\labber_ad_low_noise_float_2023\stimuli_utils.py", line 28, in <module>
            import mp.pyboard_query
        File "c:\Projekte\ETH\ETH-labber_ad_low_noise_float_2023\gits\ad_low_noise_float_2023_git\.venv\Lib\site-packages\mp\pyboard_query.py", line 10, in <module>     
            from mp.firmware.update import URL_README
        File "c:\Projekte\ETH\ETH-labber_ad_low_noise_float_2023\gits\ad_low_noise_float_2023_git\.venv\Lib\site-packages\mp\firmware\update.py", line 6, in <module>    
            from mp.firmware import pydfu
        File "c:\Projekte\ETH\ETH-labber_ad_low_noise_float_2023\gits\ad_low_noise_float_2023_git\.venv\Lib\site-packages\mp\firmware\pydfu.py", line 92, in <module>    
            getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)
                                                            ^^^^^^^^^^^^^^^^^^
        AttributeError: module 'inspect' has no attribute 'getargspec'. Did you mean: 'getargs'?
    """


if __name__ == "__main__":
    main_standalone()
