class RequestStatusCodeError(Exception):
    """Ошибка проверки статус кода."""


class EnvError(Exception):
    """Ошибка переменных окружения."""


class BotConnectionError(Exception):
    """Нет подключения к интернету"""
