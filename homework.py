import os
import sys
import time
import logging

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from expections import UnavailableTokens, UnsuccessfulSendMessage

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

LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'app.log')

ONE_MONTH_IN_SECONDS = 2600000


def check_tokens():
    """Проверка наличия токенов, перед запуском бота."""
    tokens_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    empty_variables_from_tokens = []
    for key, value in tokens_dict.items():
        if not value:
            logging.critical(f'Токен {key} пустой или некорректный.')
            empty_variables_from_tokens.append(key)
    if empty_variables_from_tokens:
        raise UnavailableTokens(
            f'Токены {empty_variables_from_tokens} недоступны.'
        )


def send_message(bot, message):
    """Отправка сообщения в Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение {message} отправлено')
    except UnsuccessfulSendMessage as error:
        logging.error(f'Ошибка {error}. Не удалось отправить сообщение.')


def get_api_answer(timestamp):
    """Получение ответа на запрос и обработка исключений."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except requests.RequestException as error:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен с'
                      f'параметрами {params}. Ошибка {error}.')
        raise error()

    if response.status_code != 200:
        logging.error(f'Неудачный статус-код от API: {response.status_code}')
        raise requests.RequestException
    return response.json()


def check_response(response):
    """Проверка запроса на соответствие критериям."""
    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            logging.error(
                f'Полученный тип данных не соответствует типу. '
                f'Ожидаемый тип: list, Получен тип: {type(homeworks)}')
            raise TypeError
        return homeworks
    except KeyError as error:
        logging.error(f'Ключа {error} нет в словаре. '
                      f'Доступные ключи в запросе: {response.keys()}.')
        raise KeyError


def parse_status(homework):
    """Получение соответствующего вердикта."""
    try:
        status = homework['status']
    except KeyError as error:
        logging.error(f'Ключа {error} нет в коллекции '
                      f'{type(homework)}, homework. Доступные ключи '
                      f'в словаре: {homework.keys()}')
        raise KeyError
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        logging.error(f'Вердикта {error} нет в коллекции '
                      f'{type(verdict)}, verdict. Доступные ключи '
                      f'в словаре: {verdict.keys()}')
        raise KeyError

    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        logging.error(f'Требуемого ключа {error} нет в коллекции '
                      f'{type(homework)}, homework. Доступные ключи '
                      f'в словаре: {homework.keys()}')
        raise KeyError

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Проверка токенов.
    try:
        check_tokens()
    except UnavailableTokens as error:
        raise UnavailableTokens(f'Ошибка при проверке токенов: {error}')

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - ONE_MONTH_IN_SECONDS
    current_status = None

    while True:
        try:
            response = check_response(get_api_answer(timestamp))
            if response:
                new_status = parse_status(response[0])
                if current_status != new_status:
                    current_status = new_status
                    send_message(bot, new_status)
            else:
                logging.debug('Домашней работы нет.')
                message = 'Домашней работы нет.'
                send_message(bot, message)
                continue

        except Exception as error:
            logging.error(
                f'Ошибка при обращении к API сервису. Ошибка {error}',
                exc_info=True)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.debug(f'Сообщение {message} отправлено')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(LOG_FILE_PATH,
                                      encoding='utf-8')
                  ],
        format=(
            'Дата и время события: %(asctime)s, '
            'Уровень лога: %(levelname)s, '
            'Имя функции: %(funcName)s, '
            'Строка: %(lineno)d, '
            'Сообщение:  %(message)s '
        ),
        level=logging.DEBUG,
    )
    main()
