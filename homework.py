import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Updater

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

updater = Updater(token=TELEGRAM_TOKEN)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено!')
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения. {error}')
        message = 'Ошибка отправки сообщения!'
        raise (message)


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise exceptions.ServerGet(error)
    if response.status_code != HTTPStatus.OK:
        message = 'Ошибка при получении ответа с сервера'
        raise exceptions.get_api_200(message)
    logger.info('Запрос успешен')
    return response.json()


def check_response(response):
    """Проверка запроса."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error('Отсутствует ключ у homeworks')
        raise KeyError('Отсутствует ключ у homeworks')
    try:
        homework = homeworks[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Статус проверки."""
    if 'homework_name' in homework:
        homework_name = homework.get('homework_name')
    else:
        raise KeyError(
            'API вернул домашнее задание без ключа "homework_name" key'
        )
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError(f'Ошибка статуса homework : {verdict}')
    logging.info(f'Новый статус {verdict}')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Проверяет наличие токенов."""
    if PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID:
        return True
    elif PRACTICUM_TOKEN is None:
        logger.info('Ошибка PRACTICUM_TOKEN')
        return False
    elif TELEGRAM_TOKEN is None:
        logger.info('Ошибка TELEGRAM_TOKEN')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logger.info('Ошибка TELEGRAM_CHAT_ID')
        return False


def main():
    """Основная функция."""
    if not check_tokens():
        message = 'Отсутствуют токены'
        logger.critical(message)
        raise (message)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(error)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
