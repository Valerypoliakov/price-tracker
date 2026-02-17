import requests
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv

load_dotenv()

SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY')

def get_page(url):
    api_url = "http://api.scraperapi.com"
    params = {
        'api_key': SCRAPER_API_KEY,
        'url': url,
        'render': 'true',
        'country_code': 'ru'
    }
    try:
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка получения страницы: {e}")
        return None

def clean_price(price_str):
    if not price_str:
        return None
    cleaned = re.sub(r'[^\d]', '', price_str.replace('\xa0', '').replace(' ', ''))
    try:
        return float(cleaned)
    except:
        return None

def parse_biggeek(html):
    soup = BeautifulSoup(html, 'html.parser')
    el = soup.find(class_='total-prod-price')
    if el:
        price = clean_price(el.get_text())
        if price:
            return price
    return None

def detect_store(url):
    if 'biggeek.ru' in url:
        return 'biggeek'
    elif 'ozon.ru' in url:
        return 'ozon'
    elif 'wildberries.ru' in url or 'wb.ru' in url:
        return 'wildberries'
    elif 'market.yandex.ru' in url:
        return 'yandex_market'
    elif 'megamarket.ru' in url:
        return 'megamarket'
    return None

def get_price(url):
    store = detect_store(url)
    if not store:
        return None, None

    html = get_page(url)
    if not html:
        return store, None

    parsers = {
        'biggeek': parse_biggeek,
        'ozon': lambda html: None,
        'wildberries': lambda html: None,
        'yandex_market': lambda html: None,
        'megamarket': lambda html: None,
    }

    price = parsers[store](html)
    return store, price