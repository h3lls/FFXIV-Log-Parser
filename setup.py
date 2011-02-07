import sys

from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
        name = "FFXIVLogParser",
        version = "2.1",
        description = "FFXIV Log Parser",
        executables = [Executable("logparse.py", base = base)])