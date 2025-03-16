from dotenv import load_dotenv
import os
import requests
from pprint import pprint
import time
from datetime import datetime, timedelta
from telebot import TeleBot
import logging

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.DEBUG,
    encoding='utf-8',
)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    if (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) is not None:
        return True


def send_message(bot, message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.error


def get_api_answer(timestamp):
    response = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    response = response.json()
    pprint(1)
    return response
    

def check_response(response):
    if 'homeworks' in response:
        homeworks = response.get('homeworks')[0]
        pprint(2)
        return homeworks
        
        
def parse_status(homework):
    status = homework['status']
    verdict = HOMEWORK_VERDICTS[status]
    homework_name = homework['homework_name']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


# get_api_answer(timestapm)
# check_response(get_api_answer(timestapm))

def main():
    """Основная логика работы бота."""

    if check_tokens():

        # Создаем объект класса бота
        bot = TeleBot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())

        # ...
        action = True
        while action:
            try:
                message = parse_status(check_response(
                    get_api_answer(timestamp)
                ))
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error
                action = False
        send_message(bot, message)
            


if __name__ == '__main__':
    main()
