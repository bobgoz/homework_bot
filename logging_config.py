import logging.config
import logging.handlers
import os
import logging


def setup_logging():
    # logging.basicConfig(
    #         format='%(asctime)s %(levelname)s %(message)s',
    #         level=logging.DEBUG,
    #         encoding='utf-8',
    #     )
    current_path = os.path.dirname(__file__)
    log_file_path = os.path.join(current_path, 'app.log')
        
    LOGGING = {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '%(asctime)s %(levelname)s %(message)s',
                }
            },
            'handlers': {
                'stream_handler': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'default'
                },
                'file_handler': {
                    'class': 'logging.FileHandler',
                    'filename': log_file_path,
                    'level': 'DEBUG',
                    'formatter': 'default',
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['stream_handler', 'file_handler']
            }
        }
        
    logging.config.dictConfig(LOGGING)

    return logging.getLogger(__name__)


logger = setup_logging()

