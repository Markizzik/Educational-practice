import requests
import psycopg2
import time
import random
import json
from flask import Flask, render_template, request, redirect, url_for

access_token = 'USERSVJ0RLO8S59VV02DNJ4BHAR2SH5GIIL07LQ077ITDOHROFDL0JILTG1M12VI'

DB_HOST = 'localhost'
DB_NAME = 'vacancies'
DB_USER = 'postgres'
DB_PASSWORD = 'ahb837js'

headers = {
    'Authorization': f'Bearer {access_token}',
}

base_url = 'https://api.hh.ru/vacancies'

app = Flask(__name__)

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")
        return None

def create_vacancies_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                salary TEXT,
                url TEXT,
                area_id INTEGER,
                area_name VARCHAR(255),
                published_at TIMESTAMP WITHOUT TIME ZONE,
                created_at TIMESTAMP WITHOUT TIME ZONE,
                apply_alternate_url TEXT,
                alternate_url TEXT,
                schedule_name VARCHAR(255),
                employment_name VARCHAR(255)
            )
        """)
        conn.commit()
        print("Таблица vacancies создана успешно или уже существует.")
    except Exception as e:
        print(f"Ошибка при создании таблицы vacancies: {e}")

def parse_vacancies_by_keyword(keyword, conn):
    try:
        cursor = conn.cursor()
        # Очистка таблицы перед вставкой новых данных
        cursor.execute("TRUNCATE TABLE vacancies")
        conn.commit()

        parsed_vacancies = []  # Список для хранения распарсенных вакансий
        total_pages = 100  # Нам нужно 100 страниц
        vacancies_per_page = 20

        for page in range(total_pages):
            params = {'text': keyword, 'page': page, 'per_page': vacancies_per_page}
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    vacancies = data['items']
                    for vacancy in vacancies:
                        name = vacancy['name']
                        company = vacancy['employer']['name']
                        salary = vacancy.get('salary')
                        url = vacancy['alternate_url']
                        area = vacancy.get('area')
                        if area:
                            area_id = area.get('id')
                            area_name = area.get('name')
                        else:
                            area_id = None
                            area_name = None
                        if salary:
                            salary_text = f"{salary['from']} - {salary['to']} {salary['currency']}"
                        else:
                            salary_text = None

                        published_at = vacancy.get('published_at')
                        created_at = vacancy.get('created_at')
                        apply_alternate_url = vacancy.get('apply_alternate_url')
                        alternate_url = vacancy.get('alternate_url')
                        schedule = vacancy.get('schedule')
                        employment = vacancy.get('employment')
                        schedule_name = schedule.get('name') if schedule else None
                        employment_name = employment.get('name') if employment else None

                        cursor.execute(
                            """
                            INSERT INTO vacancies (
                                name, company, salary, url, area_id, area_name, 
                                published_at, created_at, apply_alternate_url, 
                                alternate_url, schedule_name, employment_name
                            ) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                name, company, salary_text, url, area_id, area_name, 
                                published_at, created_at, apply_alternate_url, 
                                alternate_url, schedule_name, employment_name
                            )
                        )
                        conn.commit()
                        parsed_vacancies.append({
                            "name": name,
                            "company": company,
                            "salary": salary_text,
                            "url": url,
                            "area_id": area_id,
                            "area_name": area_name,
                            "published_at": published_at,
                            "created_at": created_at,
                            "apply_alternate_url": apply_alternate_url,
                            "alternate_url": alternate_url,
                            "schedule_name": schedule_name,
                            "employment_name": employment_name
                        })
            else:
                print(f"Ошибка при запросе к API: {response.status_code} - {response.text}")
                break

        print(f"Вакансии '{keyword}' успешно сохранены в базу данных.")
        return parsed_vacancies
    except Exception as e:
        print(f"Ошибка при сохранении вакансии: {e}")
        return []


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results', methods=['POST'])
def results():
    conn = connect_to_db()
    if conn:
        create_vacancies_table(conn)
        keyword = request.form['keyword']
        parsed_vacancies = parse_vacancies_by_keyword(keyword, conn)
        if parsed_vacancies:
            return render_template('results.html', vacancies=parsed_vacancies, keyword=keyword)
        else:
            return render_template('results.html', keyword=keyword, error_message=f"Вакансии '{keyword}' не найдены.")
    else:
        return render_template('results.html', error_message="Ошибка подключения к базе данных.")

if __name__ == "__main__":
    app.run(debug=True)



# client_id = 'IFFP6QSBTAA1SS1HJ9UB8NAQUSNA8F9T883FSL28J1LFUGR760D66SKDI2DT9BNS'
# client_secret = 'SRSHU9Q0CR4MK8742KN8FO9TNR3AOJISSMTNRTVHP6HNOFPNUP9BPRV3UUOBB0UJ'
# authorization_code = 'P0JEE44SPVNGAUPTEKNBAMGNE1BT912HDRPRKJSNROFK9ROQG37V8TACRTB19IBV'
# redirect_uri = 'http://127.0.0.1:5000'

# token_url = 'https://hh.ru/oauth/token'
# data = {
#    'grant_type': 'authorization_code',
#    'client_id': client_id,
#    'client_secret': client_secret,
#    'code': authorization_code,
#    'redirect_uri': redirect_uri,
# }

# response = requests.post(token_url, data=data)
# token_info = response.json()
# print(token_info)