import os
import time

import logging
import requests
import telebot
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from telebot import TeleBot

from exceptions import (
    RequestStatusCodeError,
    EnvError,
    WrongStatusHomeWork
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

TIMESTAMP_PERIOD = 24 * 3600 * 30

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


bot = None


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s- [%(levelname)s] - %(message)s')
file_handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
console_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    env = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    undefined_envs = [k for k, v in env.items() if v is None]
    if undefined_envs:
        msg = (f'Отсутствуют обязательные переменные '
               f'окружения:{", ".join(undefined_envs)} \n'
               f'Программа принудительно остановлена.')
        logger.critical(msg)
        raise EnvError(msg)


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
    )
    logger.debug('Удачная отправка')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        payload = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if not response.status_code == requests.codes.OK:
            msg = f'Ошибка обращения к API. Код ответа {response.status_code}'
            logger.error(msg)
            raise RequestStatusCodeError(msg)
    except requests.RequestException as error:
        msg = f'Ошибка при запросе к основному API: {error}'
        logger.error(msg)
    return response.json()


def check_response(response: dict) -> list[dict[str, str]]:
    """Проверяет, что ответ API соответствует ожиданиям."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем.')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError(
            'Отсутствуют ключи "homeworks"'
            'или "current_date" в ответе API.'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError('Значение по ключу "homeworks" должно быть списком.')
    return response['homeworks']


def parse_status(homework: list[dict[str, str]]) -> str:
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError(
            'Отсутствуют ключи "homework_name"'
            'или "status" в ответе API.'
        )
    homework_name = homework['homework_name']
    status = homework['status']
    if not HOMEWORK_VERDICTS.get(status):
        msg = (f'Неожиданный статус домашней работы,'
               f'обнаруженный в ответе API. {status}')
        logger.error(msg)
        raise WrongStatusHomeWork(msg)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time()) - TIMESTAMP_PERIOD
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logger.debug('Отсутствие в ответе новых статусов')
            timestamp = response.get('current_date', timestamp)
        except telebot.apihelper.ApiException as error:
            msg = f'Ошибка при отправки сообщения в Телеграмм: {error}'
            logger.error(msg, exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
