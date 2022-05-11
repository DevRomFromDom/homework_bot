import os
import requests
import telegram
import time
import logging

from dotenv import load_dotenv
from http import HTTPStatus


load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
                    filename='logs.log')

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info("Сообщение успешно отправлено!")
    except telegram.TelegramError as error:
        logging.error(f"Отправка сообщения не удалась, {error}")


def get_api_answer(current_timestamp):
    """Запрос данный у API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
    except ConnectionError as error:
        logging.error(f"Ошибка при запросе к API {error}")
        raise ConnectionError(f"Ошибка при запросе к API {error}")
    if response.status_code == HTTPStatus.OK:
        try:
            data = response.json()
        except ValueError as error:
            logging.error(
                f"Исключение при переводе ответа api в Json, {error}")
            raise ValueError(
                f"Исключение при переводе ответа api в Json, {error}")
        return data
    else:
        logging.error(
            f"Не корректный статус ответа от сервера {response.status_code}")
        raise ConnectionError(
            f"Не корректный статус ответа от сервера {response.status_code}")


def check_response(response):
    """Проверка ответа от API."""
    if isinstance(response, dict):
        if 'homeworks' not in response.keys():
            logging.error("Ответ от сервера не содержит homeworks")
            raise KeyError("Ответ от сервера не содержит homeworks")
        homeworks = response.get('homeworks')
        if isinstance(homeworks, list):
            if homeworks == []:
                logging.debug('В ответе пусто!')
        else:
            logging.error(f"Не корректный тип homeworks {type(homeworks)}")
            raise TypeError(
                f"Не корректный тип homeworks {type(homeworks)}")
    else:
        logging.error("Не корректный тип данных полученый от Api!")
        raise TypeError("Не корректный тип данных полученый от Api!")
    return homeworks


def parse_status(homework):
    """Получение статуса о выполнении работы."""
    if isinstance(homework, dict):
        if 'homework_name' not in homework.keys():
            logging.error(
                'В обьекте выполненного задания нет ключа homework_name')
            raise KeyError(
                'В обьекте выполненного задания нет ключа homework_name')
        if 'status' not in homework.keys():
            logging.error('В обьекте выполненного задания нет ключа status')
            raise KeyError('В обьекте выполненного задания нет ключа status')
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES.keys():
            logging.error(
                f'Не корректный статус в ответе API {homework_status}')
            raise KeyError(
                f'Не корректный статус в ответе API {homework_status}')

        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logging.error("Тип работы полученной с сервера, не корректный!")
        raise TypeError("Тип работы полученной с сервера, не корректный!")


def check_tokens():
    """Проверка на наличие токенов."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }

    if not check_tokens():
        falsy_values = []
        for key, value in tokens.items():
            if not bool(value):
                falsy_values.append(key)

        logging.critical(f'Токен(ы) не переданы! Отсутствуют: {falsy_values}')
        raise RuntimeError(
            f'Токен(ы) не переданы! Отсутствуют: {falsy_values}')

    TEN_SEC = 10000
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - TEN_SEC)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks: list = check_response(response)
            for homework in homeworks:
                status: str = parse_status(homework)
                send_message(bot, status)

            current_timestamp = response.get(
                'current_date', current_timestamp)
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = None
            if not message:
                message = send_message(
                    bot, f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
