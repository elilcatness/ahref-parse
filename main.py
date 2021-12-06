import os
import time
from datetime import datetime as dt
from random import randint

from dotenv import load_dotenv
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
from selenium.webdriver import Chrome  # for annotation
from selenium.webdriver.common.by import By

from constants import *
from exceptions import *
from utils import get_driver, get_data, write_data


def auth(driver: Chrome, login: str, password: str):
    login_url = os.getenv('login_url')
    if not login_url:
        raise MissingDotenvData('В переменных среды отсутствует login_url')
    driver.get(login_url)
    for input_name, verbose_name, value in [('email', 'логина', login), ('password', 'пароля', password)]:
        try:
            field = driver.find_element(By.XPATH, f'//input[@name="{input_name}"]')
        except NoSuchElementException:
            raise AuthorizationFailedException(f'Не удалось найти поле для ввода {verbose_name}')
        for s in value:
            field.send_keys(s)
            time.sleep(float(f'0.1{randint(0, 9)}'))
    try:
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
    except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException) as e:
        raise AuthorizationFailedException(f'Не удалось нажать на кнопку авторизации [{e.__class__.__name__}]')


def ask_mode(modes: list):
    try:
        mode_idx = int(input('Укажите цифру для какого типа соответствия собираем данные:\n' +
                             '\n'.join([f'{i} - {modes[i - 1]}' for i in range(1, len(modes) + 1)]) + '\n')) - 1
    except ValueError:
        return print('Неверный формат')
    if mode_idx >= len(modes):
        return print(f'Число должно быть от 1 до {len(modes)}')
    return modes[mode_idx]


def main():
    modes = os.getenv('modes').split(';')
    if not modes:
        return print('Список типов соответствия пуст в .env')
    mode = ask_mode(modes)
    if not mode:
        exit(-1)
    with open(os.getenv('domains_filename'), encoding='utf-8') as f:
        domains = [x.strip() for x in f.readlines()]
        if not domains:
            raise FileIsEmptyException(f'Файл {os.getenv("domains_filename")} пуст')
        domains_count = len(domains)
    third_party_source = False
    driver = get_driver()
    with open(os.getenv('credentials_filename'), encoding='utf-8') as f:
        lines = [x.strip() for x in f.readlines()]
        if len(lines) > 1:
            third_party_source = True
            login_url = lines[0]
            base_url = os.getenv('keywords_fmt') % (lines[1].rstrip('/'), mode)
        else:
            base_url = os.getenv('keywords_fmt') % (os.getenv('base_url').rstrip('/'), mode)
        try:
            login, password = lines[0].split(':')
        except ValueError:
            raise InvalidFileData(f'Неверный формат данных в {os.getenv("credentials_filename")}')
    if not third_party_source:
        auth(driver, login, password)
        time.sleep(AUTH_TIMEOUT)
        if driver.current_url == os.getenv('login_url'):
            auth(driver, login, password)
    else:
        driver.get(login_url)
        print('Ожидание авторизации пользователем...')
        while driver.current_url == login_url:
            pass
    print('Авторизация прошла успешно...')
    output_filename = os.getenv('output_filename')
    for i, domain in enumerate(domains):
        callback, data = get_data(driver, base_url, domain)
        if callback == 'limit-reached':
            return print('Лимит превышен, завершение работы')
        if not data:
            print(f'[{dt.now().strftime("%H:%M:%S")}] {domain} пуст')
        else:
            write_data(data, output_filename, 'a')
            print(f'[{dt.now().strftime("%H:%M:%S")}] {i + 1}/{domains_count} записано [{domain}]')


if __name__ == '__main__':
    load_dotenv()
    main()
