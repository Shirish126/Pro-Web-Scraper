import requests
import json
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

# Database setup
conn = sqlite3.connect('recon_data.db')
c = conn.cursor()

# Create tables if they do not exist
c.execute('''
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY,
        url TEXT,
        status_code INTEGER
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS headers (
        id INTEGER PRIMARY KEY,
        url TEXT,
        headers TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS forms (
        id INTEGER PRIMARY KEY,
        form_action TEXT,
        form_method TEXT,
        form_fields TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS scripts (
        id INTEGER PRIMARY KEY,
        script_src TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS cookies (
        id INTEGER PRIMARY KEY,
        url TEXT,
        cookies TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY,
        url TEXT,
        link TEXT,
        type TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS subdomains (
        id INTEGER PRIMARY KEY,
        subdomain TEXT
    )
''')
conn.commit()


# Function to store data
def store_data(table, data):
    if table == 'urls':
        c.execute('INSERT INTO urls (url, status_code) VALUES (?, ?)', data)
    elif table == 'headers':
        c.execute('INSERT INTO headers (url, headers) VALUES (?, ?)', data)
    elif table == 'forms':
        c.execute('INSERT INTO forms (form_action, form_method, form_fields) VALUES (?, ?, ?)', data)
    elif table == 'scripts':
        c.execute('INSERT INTO scripts (script_src) VALUES (?)', data)
    elif table == 'cookies':
        c.execute('INSERT INTO cookies (url, cookies) VALUES (?, ?)', data)
    elif table == 'links':
        c.execute('INSERT INTO links (url, link, type) VALUES (?, ?, ?)', data)
    elif table == 'subdomains':
        c.execute('INSERT INTO subdomains (subdomain) VALUES (?)', data)
    conn.commit()


# Web Scraping Function
def scrape_website(url):
    try:
        response = requests.get(url)
        print(f"Scraping {url}... Status Code: {response.status_code}")
        store_data('urls', (url, response.status_code))

        headers = json.dumps(dict(response.headers))
        store_data('headers', (url, headers))

        cookies = json.dumps(requests.utils.dict_from_cookiejar(response.cookies))
        store_data('cookies', (url, cookies))

        soup = BeautifulSoup(response.text, 'html.parser')

        forms = soup.find_all('form')
        for form in forms:
            form_action = form.get('action')
            form_method = form.get('method')
            form_fields = json.dumps({field.get('name'): field.get('type') for field in form.find_all('input')})
            store_data('forms', (form_action, form_method, form_fields))
            print(f"Found form: Action={form_action}, Method={form_method}, Fields={form_fields}")

        scripts = soup.find_all('script')
        for script in scripts:
            script_src = script.get('src')
            if script_src:
                store_data('scripts', (script_src,))
                print(f"Found script: Source={script_src}")

        links = soup.find_all('a', href=True)
        for link in links:
            link_url = urljoin(url, link['href'])
            if urlparse(link_url).netloc == urlparse(url).netloc:
                link_type = 'internal'
            else:
                link_type = 'external'
            store_data('links', (url, link_url, link_type))
            print(f"Found link: URL={link_url}, Type={link_type}")

        pagination_links = soup.find_all('a', href=True, string=re.compile(r'Next|More|Older|Newer', re.IGNORECASE))
        for pagination_link in pagination_links:
            next_page_url = urljoin(url, pagination_link['href'])
            scrape_website(next_page_url)

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")


# Main execution
if __name__ == "__main__":
    url = input("Enter URL: ")
    scrape_website(url)
    print("Scraping completed.")
