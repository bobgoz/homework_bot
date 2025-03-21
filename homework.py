import os
import time
import logging
import logging.config

# from logging_config import setup_logging
from dotenv import load_dotenv
import requests
from telebot import TeleBot


load_dotenv()
# logging = setup_logging()

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




def check_tokens():
    """Проверка наличия токенов, перед запуском бота."""
    if (
        PRACTICUM_TOKEN is not None
        and TELEGRAM_TOKEN is not None
        and TELEGRAM_CHAT_ID is not None
    ):
        return True
    else:
        logging.critical('Переменные окружения отсутствуют.')


def send_message(bot, message):
    """Отправка сообщения в Телеграмм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Ошибка {error}. Не удалось отправить сообщение.')


def get_api_answer(timestamp):
    """Получение ответа на запрос и обработка исключений."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
        if response.status_code != 200:
            logging.error(f'Неудачный ответ от API: {response.status_code}')
            raise requests.RequestException(
                f'Неудачный ответ от API: {response.status_code}'
            )
        return response.json()
    except Exception as error:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен. Ошибка {error}')
        raise error(f'Эндпоинт {ENDPOINT} недоступен. Ошибка {error}')


def check_response(response):
    """Проверка запроса на соответствие критериям."""
    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            logging.error('Полученный тип данных не соответствует типу list')
            raise TypeError('Полученный тип данных не соответствует типу list')
        return homeworks[0]
    except KeyError:
        logging.error('Ключа "homeworks" нет в словаре.')
        raise KeyError('Ключа "homeworks" нет в словаре.')


def parse_status(homework):
    """Получение соответствующего вердикта."""
    try:
        status = homework['status']
        verdict = HOMEWORK_VERDICTS[status]
        if status is None:
            logging.error(
                'значение ключа "status" не содержит документации.'
            )
            raise ValueError(
                'значение ключа "status" не содержит документации.'
            )
    except Exception as error:
        logging.error(f'Ошибка {error}. Требуемого ключа нет в словаре.')
        raise error(f'Ошибка {error}. Требуемого ключа нет в словаре.')

    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('Ключ "homework_name" отсутствует в словаре.')
        raise KeyError('Ключ "homework_name" отсутствует в словаре.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def setup_logging():
    """Хранение настроек для логгера."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Форматирование
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    
    # Хандлер для консоли
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)

    # Файловый хандлер
    current_path = os.path.dirname(__file__)
    log_file_path = os.path.join(current_path, 'app.log')
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


def main():
    """Основная логика работы бота."""
    
    # current_path = os.path.dirname(__file__)
    # log_file_path = os.path.join(current_path, 'app.log')
        
    # LOGGING = {
    #         'version': 1,
    #         'formatters': {
    #             'default': {
    #                 'format': '%(asctime)s %(levelname)s %(message)s',
    #             }
    #         },
    #         'handlers': {
    #             'stream_handler': {
    #                 'class': 'logging.StreamHandler',
    #                 'level': 'DEBUG',
    #                 'formatter': 'default'
    #             },
    #             'file_handler': {
    #                 'class': 'logging.FileHandler',
    #                 'filename': log_file_path,
    #                 'level': 'DEBUG',
    #                 'formatter': 'default',
    #             }
    #         },
    #         'root': {
    #             'level': 'DEBUG',
    #             'handlers': ['stream_handler', 'file_handler']
    #         }
    #     }
        
    # logging.config.dictConfig(LOGGING)

    
    
    # logging.setLevel(logging.INFO)
    
    # stream_handler = logging.StreamHandler()
    # stream_handler.setLevel(logging.DEBUG)
    
    # file_handler = logging.StreamHandler()
    # file_handler.setLevel(logging.DEBUG)
    
    # logging.addHandler(stream_handler)
    # logging.addHandler(file_handler)


    if check_tokens():
        # Создаём объект логгера
        logging = setup_logging()
        
        # Создаем объект класса бота
        bot = TeleBot(token=TELEGRAM_TOKEN)
        one_month_in_seconds = 2600000
        timestamp = int(time.time()) - one_month_in_seconds
        current_status = None

        while True:
            try:
                new_status = parse_status(check_response(
                    get_api_answer(timestamp)))
                if current_status != new_status:
                    current_status = new_status
                    send_message(bot, new_status)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error('Ошибка при обращении к API сервису.',
                              exc_info=True)
                send_message(bot, message)
                logging.debug('Сообщение отправлено')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
