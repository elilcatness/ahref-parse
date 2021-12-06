import csv
from datetime import date

from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as exp_cond
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire.webdriver import Chrome, ChromeOptions

from constants import COOKIES_TIMEOUT, BUTTON_TIMEOUT, LOAD_TIMEOUT
from exceptions import CookiesTimeoutException


def get_driver(path='binary/chromedriver.exe'):
    options = ChromeOptions()
    options.add_argument('--log-level=3')
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
    compared_with_date = actual_date + relativedelta(months=-1)
    return actual_date.isoformat(), compared_with_date.isoformat()


def get_data(driver: Chrome, url: str, domain: str):
    driver.get(url + domain)
    if 'Sorry! your daily' in driver.page_source:
        return 'limit-reached', None
    header = WebDriverWait(driver, LOAD_TIMEOUT).until(exp_cond.presence_of_element_located((
        By.XPATH,
        '//h4[@class="css-a5m6co-text css-p8ym46-fontFamily css-11397xj-fontSize '
        'css-1wmho6b-fontWeight css-mun6jo-color css-15qzf5r-display"]'
    )))
    if header.text.strip().lower() == '0 ключевых слов' or header.text.strip().lower() == '0 keywords':
        return None, None
    try:
        btn = WebDriverWait(driver, BUTTON_TIMEOUT).until(exp_cond.presence_of_element_located((
            By.XPATH,
            '//div[@class="css-1m3jbw6-dropdown '
            'css-mkifqh-dropdownMenuWidth css-1sspey-dropdownWithControl"]/button')))
        WebDriverWait(driver, BUTTON_TIMEOUT).until(exp_cond.element_to_be_clickable(btn))
        btn.click()
    except TimeoutException:
        return None, None
    data = {}
    rows = WebDriverWait(driver, LOAD_TIMEOUT).until(exp_cond.presence_of_all_elements_located((
        By.XPATH,
        '//div[@class="css-131jr5s-row css-13wqkl7-row css-13n3pes-rowLayout css-87ebjr-rowAlign"]'
    )))
    for row in rows:
        country = row.find_element(
            By.XPATH,
            './/div[@class="css-a5m6co-text css-p8ym46-fontFamily css-11397xj-fontSize css-15qzf5r-display"]').text
        try:
            count_raw = row.find_element(
                By.XPATH,
                './/div[@class="css-1ckph53-badge css-z4csn1-ghost css-m40bx0-rounded '
                'css-1wh4hpic-padding css-xtgw0q-height-medium"]').text
        except NoSuchElementException:
            count_raw = row.find_element(
                By.XPATH,
                './/div[@class="css-a5m6co-text css-10st79w-fontFamily css-1s1cif8-fontSize '
                'css-15qzf5r-display"]').text
        if count_raw.endswith('B'):
            count = int(float(count_raw.replace('B', '')) * 10 ** 9)
        elif count_raw.endswith('M'):
            count = int(float(count_raw.replace('M', '')) * 10 ** 6)
        elif count_raw.endswith('K'):
            count = int(float(count_raw.replace('K', '')) * 10 ** 3)
        else:
            count = int(count_raw)
        data[country] = count
    return None, {'Domains': domain, **data}


def write_data(data: dict, filename: str, mode: str, delimiter=';'):
    if mode == 'w':
        with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(data.keys()), delimiter=delimiter)
            writer.writeheader()
            writer.writerow(data)
    elif mode == 'a':
        prev_data = []
        rewrite = True
        try:
            with open(filename, newline='', encoding='utf-8') as csv_file:
                prev_keys = csv_file.readline().strip().split(delimiter)
                new_keys = [key for key in list(data.keys()) if key not in prev_keys]
                if not new_keys:
                    rewrite = False
        except FileNotFoundError:
            return write_data(data, filename, 'w', delimiter)
        if not rewrite:
            with open(filename, 'a', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=prev_keys, delimiter=delimiter)
                for key in prev_keys:
                    if key not in data.keys():
                        data[key] = 0
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
                writer = csv.DictWriter(csv_file, fieldnames=list(prev_data[0].keys()) if prev_data
                                        else list(data.keys()), delimiter=delimiter)
                writer.writeheader()
                writer.writerows(prev_data)
                if prev_data:
                    for key in prev_data[0].keys():
                        if key not in data.keys():
                            data[key] = 0
                writer.writerow(data)
