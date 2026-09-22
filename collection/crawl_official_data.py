import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def get_link(url):
    links = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Không lấy được link từ {url}: status_code={response.status_code}")
            return []

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        div_wrappers = soup.find_all('div', class_=['text-weather-location fix-weather-location', 'uk-width-expand'])
        for div in div_wrappers:
            a_tag = div.find('a')
            if not a_tag:
                continue
            main_title = a_tag.get_text(strip=True)
            link = a_tag.get('href')
            if not link:
                continue
            full_link = urljoin(url, link)
            links.append({
                'main_title': main_title,
                'link': full_link,
            })

        return links
    except Exception as e:
        print(f"Lỗi get_link({url}): {e}")
        return []


def crawl_article_content(url, main_title):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Không lấy được nội dung từ {url}: status_code={response.status_code}")
            return None

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        content_area = soup.find('div', class_='content-news')
        title_tag = content_area.find('h2', class_='tt-content-news') if content_area else None
        title = title_tag.get_text(strip=True) if title_tag else ''
        p_tags = content_area.find_all('p') if content_area else soup.find_all('p')

        if not p_tags:
            print(f"Không tìm thấy nội dung bài viết trên {url}")
            return None

        content = ' '.join(' '.join(p.stripped_strings) for p in p_tags)
        return {
            'main_title': main_title,
            'link': url,
            'title': title,
            'content': content,
        }
    except Exception as e:
        print(f"Lỗi crawl_artical_content({url}): {e}")
        return None

