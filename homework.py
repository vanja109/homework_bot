import logging
import os
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

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


logging.basicConfig(
    filemode='a',
    filename='logs.log',
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
        raise exceptions.FailMessage(f'Ошибка отправки сообщения {error}')


def get_api_answer(current_timestamp):
    """Получение ответа от API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise exceptions.ServerGet(error)
    if response.status_code != HTTPStatus.OK:
        raise exceptions.GetApi200('Ошибка при получении ответа с сервера')
    logger.info('Запрос успешен')
    return response.json()


def check_response(response):
    """Проверка запроса."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError('Отсутствует ключ у homeworks')
    if isinstance(homeworks, list):
        return homeworks
    else:
        raise exceptions.ListErr('homeworks не список')


def parse_status(homework):
    """Статус проверки."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError(
            'В homework нет ключа "homework_name" или "status"'
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        raise KeyError(f'Ошибка статуса homework : {verdict}')
    logger.info(f'Новый статус {verdict}')
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Проверяет наличие токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная функция."""
    if not check_tokens():
        message = 'Отсутствуют токены'
        logger.critical(message)
        raise exceptions.TokkenError(message)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.info("Статус домашней работы не обновился")
                time.sleep(RETRY_TIME)
            homework = homeworks[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
