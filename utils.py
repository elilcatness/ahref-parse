import csv
from datetime import date, timedelta
import requests
from selenium.common.exceptions import TimeoutException
from seleniumwire.webdriver import Chrome, ChromeOptions

from constants import COOKIES_TIMEOUT
from exceptions import CookiesTimeoutException, ApiException


def get_driver(path='binary/chromedriver.exe'):
    options = ChromeOptions()
    # options.add_argument('--headless')
    return Chrome(executable_path=path, options=options)


def parse_cookies(cookies: str):
    try:
        return {c.split('=')[0]: c.split('=')[1] for c in cookies.split('; ')}
    except IndexError:
        return dict()


def get_cookies(driver: Chrome, base_url: str, domain: str, request_url: str):
    driver.get(base_url + domain)
    try:
        r = driver.wait_for_request(request_url, timeout=COOKIES_TIMEOUT)
    except TimeoutException:
        raise CookiesTimeoutException(f'Не удалось получить cookies с {base_url + domain}')
    return parse_cookies(r.headers.get('cookie', ''))


def _get_dates_for_api():
    actual_date = date.today()
    compared_with_date = actual_date - timedelta(days=30)
    return actual_date.isoformat(), compared_with_date.isoformat()


def get_data(api_url: str, domain: str, headers: dict, cookies: dict):
    actual, compared_with = _get_dates_for_api()
    response = requests.post(api_url, json={'args': {
        'mode': 'subdomains', 'protocol': 'both', 'reportMode':
            ['Compared', {'actual': actual, 'comparedWith': compared_with}],
        'url': domain}}, headers=headers, cookies=cookies)
    if response.status_code != 200:
        raise ApiException(f'Был получен код {response.status_code} от API.'
                           f'\nОтвет: {response.text}')
    return {'Domains': domain, **{list(d.values())[0]: list(d.values())[1] for d in response.json()[-1]}}


def write_data(data: dict, filename: str, mode: str, delimiter=';'):
    if mode == 'w':
        with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(data.keys()), delimiter=delimiter)
            writer.writeheader()
            writer.writerow(data)
    elif mode == 'a':
        prev_data = []
        rewrite = True
        with open(filename, newline='', encoding='utf-8') as csv_file:
            prev_keys = csv_file.readline().strip().split(delimiter)
            new_keys = [key for key in list(data.keys()) if key not in prev_keys]
            if not new_keys:
                rewrite = False
        if not rewrite:
            with open(filename, 'a', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=prev_keys, delimiter=delimiter)
                writer.writerow(data)
        else:
            with open(filename, 'r', newline='', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file, fieldnames=prev_keys,
                                        delimiter=delimiter)
                for row in list(reader)[1:]:
                    for key in new_keys:
                        row[key] = 0
                    prev_data.append(row)
            with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=list(prev_data[0].keys()), delimiter=delimiter)
                writer.writeheader()
                writer.writerows(prev_data)
                for key in prev_data[0].keys():
                    if key not in data.keys():
                        data[key] = 0
                writer.writerow(data)