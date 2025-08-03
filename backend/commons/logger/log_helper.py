import datetime
import os
import sys

class CustomLogger: 
    def _log(self, level, message):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        filename = os.path.basename(sys._getframe(2).f_code.co_filename)
        print(f"[{timestamp}] [{level}] [{filename}] {message}")

    def info(self, message):
        self._log("INFO", message)

    def error(self, message):
        self._log("ERROR", message)

    def warning(self, message):
        self._log("WARNING", message)