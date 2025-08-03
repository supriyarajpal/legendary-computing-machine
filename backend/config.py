import os
from dotenv import dotenv_values, find_dotenv, load_dotenv
from commons.logger.log_helper import CustomLogger 


dotenv_path = find_dotenv()
env_dict = dotenv_values(dotenv_path)
env = env_dict.get("ENVIRONMENT")
if env in ("PROD", "DEV"):
    load_dotenv(dotenv_path, override=True)


class Config_Reader:
    def __init__(self, logger: CustomLogger):
        self.logger = logger

    def set_logger(self, logger: CustomLogger):
        self.logger = logger

    def read_config_value(self, key_name:str):
        return self._get_config_value(key_name)

    def _get_config_value(self, key_name:str)-> str:
        value = os.getenv(key_name, None)
        if value is None:
            if self.logger:
                self.logger.error(f"Necessary value {value} couldn't be found in environment")
            raise Exception(f"Necessary value {value} couldn't be found in environment")
        return value


class DefaultConfig:
    _initialised = False

    @classmethod
    def initialise(cls):
        if not cls._initialised:
            config_reader = Config_Reader(None)

            cls.logger = CustomLogger()
            config_reader.set_logger(cls.logger)

            try:
                cls.ENV = config_reader.read_config_value("ENVIRONMENT")
                cls.logger.info("Config values loaded successfully")
                cls.logger.info(f"Connected to {cls.ENV}")
                cls._initialised = True
            except Exception as e:
                cls.logger.error(f"Error loading config values: {e}")
                raise e

DefaultConfig.initialise()









