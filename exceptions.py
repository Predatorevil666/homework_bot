class RequestStatusCodeError(Exception):
    """Ошибка проверки статус кода."""

    pass


class EnvError(Exception):
    """Ошибка переменных окружения."""

    pass


class WrongStatusHomeWork(Exception):
    """Неожиданный статус домашней работы."""

    pass
