import logging
import sys
from logging.handlers import RotatingFileHandler


_log_format = (
    "%(asctime)s- [%(levelname)s] - [%(funcName)s:%(lineno)d] - %(message)s"
)

LOGGING_LEVEL = logging.DEBUG


# ANSI escape-последовательности для цветов
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
BOLD_RED = "\033[1;31m"

# Создаем пользовательский форматер


class CustomFormatter(logging.Formatter):
    """Определяем цвета для разных уровней логирования"""
    COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED
    }

    def format(self, record):
        # Получаем цвет по уровню лога
        log_color = self.COLORS.get(record.levelno, RESET)
        # Форматируем сообщение с цветом
        message = super().format(record)
        return f"{log_color}{message}{RESET}"


formatter = CustomFormatter(_log_format)


def get_file_handler():
    """Обработчик для управления ротацией логов """
    file_handler = RotatingFileHandler(
        'bot.log',
        maxBytes=50000000,
        backupCount=5
    )
    file_handler.setLevel(LOGGING_LEVEL)
    file_handler.setFormatter(formatter)
    return file_handler


def get_stream_handler():
    """Обработчик отправки записей в стандартный поток"""
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(LOGGING_LEVEL)
    stream_handler.setFormatter(formatter)
    return stream_handler


def get_logger(name):
    """Создание логгера"""
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_stream_handler())
    return logger
