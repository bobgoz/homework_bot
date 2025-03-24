import os
import sys
import time
import logging

from dotenv import load_dotenv
import requests
from telebot import TeleBot
from http import HTTPStatus

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
    has_errors = False
    for key, value in tokens_dict.items():
        if not value:
            logging.critical(f'Токен {key} отсутствует или некорректен.')
            has_errors = True
    return not has_errors


def send_message(bot, message):
    """Отправка сообщения в Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение {message} отправлено')
    except UnsuccessfulSendMessage as error:
        logging.debug(f'Сообщение {message} не отправлено. Ошибка {error}')


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
        raise error(f'Эндпоинт {ENDPOINT} недоступен с'
                    f'параметрами {params}. Ошибка {error}.')

    if response.status_code != HTTPStatus.OK:
        raise requests.RequestException('Получен неожиданный статус-код: '
                                        f'{response.status_code}. Ожидаемый '
                                        f'статус-код: {HTTPStatus.OK}.')
    return response.json()


def check_response(response):
    """Проверка запроса на соответствие критериям."""
    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError('Полученный тип данных не соответствует типу. '
                            'Ожидаемый тип: list, '
                            f'Получен тип: {type(homeworks)}')
        return homeworks
    except KeyError as error:
        raise KeyError(f'Ключа {error} нет в коллекции '
                       f'{type(response)}, response. '
                       f'Доступные ключи в запросе: {response.keys()}.')


def parse_status(homework):
    """Получение соответствующего вердикта."""
    try:
        status = homework['status']
    except KeyError as error:
        raise KeyError(f'Ключа {error} нет в коллекции '
                       f'{type(homework)}, homework. Доступные ключи '
                       f'в словаре: {homework.keys()}')

    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        raise KeyError(f'Вердикта {error} нет в коллекции '
                       f'{type(verdict)}, verdict. Доступные ключи '
                       f'в словаре: {verdict.keys()}')

    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        raise KeyError(f'Требуемого ключа {error} нет в коллекции '
                       f'{type(homework)}, homework. Доступные ключи '
                       f'в словаре: {homework.keys()}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Проверка токенов.

    if not check_tokens():
        raise UnavailableTokens('Ошибка при проверке токенов')

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - ONE_MONTH_IN_SECONDS
    current_status = None
    last_error_message = None

    while True:
        try:
            homeworks = check_response(get_api_answer(timestamp))
            if not homeworks:
                message = 'Домашней работы нет.'
                logging.debug(message)
                send_message(bot, message)
                continue

            new_status = parse_status(homeworks[0])
            if current_status != new_status:
                current_status = new_status
                send_message(bot, new_status)

        except Exception as error:
            logging.error(
                f'Ошибка при обращении к API сервису. Ошибка {error}',
                exc_info=True)
            message = f'Сбой в работе программы: {error}'
            # Отправка сообщения при новой ошибке.
            if message != last_error_message:
                send_message(bot, message)
                last_error_message = message
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
