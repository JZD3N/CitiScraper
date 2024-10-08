from flask import Flask, render_template, request, redirect, url_for, send_file
import requests
from bs4 import BeautifulSoup
import csv
import os
import concurrent.futures

app = Flask(__name__)

# Home page with form
@app.route('/')
def index():
    return render_template('index.html')

# Scraping route
@app.route('/scrape', methods=['POST'])
def scrape():
    query = request.form['query']
    limit = request.form['limit']

    try:
        limit_value = int(limit)
        if limit_value < 0:
            return "Invalid limit. Enter a value greater than or equal to 0."
    except ValueError:
        return "Invalid limit. Please enter a valid number."

    # Scrape the articles
    file_path = scrape_citi(query, limit_value if limit_value > 0 else None)
    
    if file_path:
        return redirect(url_for('download_file', filename=file_path))
    else:
        return "Scraping failed."

# Scrape function
def scrape_citi(query, limit=None):
    base_url = "https://citinewsroom.com/"
    category_urls = []
    page = 1
    while True:
        category_url = f"/?s={query}&page={page}"
        response = requests.get(base_url + category_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        if not soup.find('article', {'class': 'jeg_post jeg_pl_md_2 format-standard'}):
            break
        category_urls.append(category_url)
        if limit is not None and len(category_urls) >= limit:
            break
        page += 1

    headers = ["Title", "Link", "Date", "Excerpt"]
    data = []

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(scrape_page, base_url + category_url) for category_url in category_urls]
            for future in concurrent.futures.as_completed(futures):
                data.extend(future.result())

        file_path = os.path.join(os.getcwd(), f"citi_news_{query}.csv")
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(data)
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while scraping: {e}")
        return None

# Scrape page function
def scrape_page(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    article_list = soup.find_all('article', {'class': 'jeg_post jeg_pl_md_2 format-standard'})
    data = []

    for article in article_list:
        article_link = article.find('a').get('href')
        article_title = article.find('h3').text.strip()
        article_date = article.find('div', {'class': 'jeg_meta_date'}).text.strip()
        article_excerpt = article.find('div', {'class': 'jeg_post_excerpt'}).text.strip()
        data.append([article_title, article_link, article_date, article_excerpt])

    return data

# Download route
@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
