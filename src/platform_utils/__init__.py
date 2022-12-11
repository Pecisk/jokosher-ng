import platform
from .windows import PlatformUtilsWindows
from .unix import PlatformUtilsUnix

system = platform.system()

class PlatformUtils(PlatformUtilsWindows if system == "windows" else PlatformUtilsUnix):
    pass
