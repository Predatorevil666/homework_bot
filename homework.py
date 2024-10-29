import os
import time
from contextlib import suppress

import requests
import telebot
from dotenv import load_dotenv
from telebot import TeleBot

import app_loger
from exceptions import (
    RequestStatusCodeError,
    EnvError,
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = app_loger.get_logger(__name__)


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    undefined_tokens = [name for name, token in tokens.items() if not token]
    if undefined_tokens:
        msg = ('Отсутствуют обязательные переменные '
               f'окружения:{", ".join(undefined_tokens)} \n'
               'Программа принудительно остановлена.')
        logger.critical(msg)
        raise EnvError(msg)


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    logger.info('Начало отправки сообщения в Telegram')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
    )
    logger.debug('Удачная отправка сообщения в Telegram!')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        logger.info('Запрос к API оправляется')
        payload = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        logger.info('Получен корректный ответ от API!')
    except requests.RequestException as error:
        raise ConnectionError(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != requests.codes.OK:
        msg = f'Ошибка обращения к API. Код ответа {response.status_code}'
        raise RequestStatusCodeError(msg)
    return response.json()


def check_response(response: dict) -> None:
    """Проверяет, что ответ API соответствует ожиданиям."""
    logger.info('Начало проверки получения данных')
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API должен быть словарем.'
            f'Получен тип: {type(response).__name__}'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'Отсутствуют ключ "homeworks" в ответе API.'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            "Значение по ключу <homeworks> должно быть списком."
            f"Получен тип: {type(response['homeworks']).__name__}"
        )
    logger.info('Проверка данных прошла успешно!')


def parse_status(homework: list[dict[str, str]]) -> str:
    """Извлекает статус домашней работы."""
    logger.info('Начало проверки статуса домашней работы')
    required_keys = ['lesson_name', 'status']
    missing_keys = [key for key in required_keys if key not in homework]
    if missing_keys:
        raise KeyError(
            'Отсутствуют ключи в домашней работе:'
            f' {", ".join(missing_keys)}.'
            f' Ожидались ключи: {", ".join(required_keys)}.'

        )
    'Отсутствуют ключи в домашней работе: {}. Ожидались ключи: {}.'
    lesson_name = homework['lesson_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        msg = (f'Неожиданный статус домашней работы,'
               f'обнаруженный в ответе API. {status}')
        raise ValueError(msg)
    verdict = HOMEWORK_VERDICTS[status]
    logger.info('Проверка статуса домашней работы прошла успешно!')
    return f'Изменился статус проверки работы - "{lesson_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if len(homeworks) == 0:
                logger.debug('Получен пустой список домашних работ')
                continue
            status_homework = parse_status(homeworks[0])
            if last_message != status_homework:
                send_message(bot, status_homework)
                last_message = status_homework
            logger.debug('Отсутствие в ответе новых статусов')
            timestamp = response.get('current_date', timestamp)
        except (
            telebot.apihelper.ApiException,
            requests.RequestException
        ) as error:
            msg = f'Ошибка при отправки сообщения в Телеграмм: {error}'
            logger.exception(msg)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(error)
            if last_message != message:
                with suppress(
                        telebot.apihelper.ApiException,
                        requests.RequestException
                ):
                    send_message(bot, message)
                    last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
