import requests
import psycopg2
import time
import random
import json
from flask import Flask, render_template, request, jsonify

access_token = 'USERSVJ0RLO8S59VV02DNJ4BHAR2SH5GIIL07LQ077ITDOHROFDL0JILTG1M12VI'

DB_HOST = 'db'
DB_NAME = 'vacancies'
DB_USER = 'postgres'
DB_PASSWORD = 'ahb837js'
DB_PORT = '5432'

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
            password=DB_PASSWORD,
            port =DB_PORT
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
        cursor.execute("TRUNCATE TABLE vacancies")
        conn.commit()

        parsed_vacancies = []  
        total_pages = 100  
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

@app.route('/filter_results', methods=['POST'])
def filter_results():
    conn = connect_to_db()
    if conn:
        create_vacancies_table(conn)
        keyword = request.form.get('keyword')
        city = request.form.get('city')
        schedule = request.form.get('schedule')
        employment = request.form.get('employment')
        salary_from = request.form.get('salary_from')
        salary_to = request.form.get('salary_to')

        cursor = conn.cursor()
        query = "SELECT * FROM vacancies WHERE name LIKE %s"
        params = [f"%{keyword}%"]

        if city:
            query += " AND area_name = %s"
            params.append(city)

        if schedule:
            query += " AND schedule_name = %s"
            params.append(schedule)

        if employment:
            query += " AND employment_name = %s"
            params.append(employment)

        if salary_from:
            query += " AND salary >= %s"
            params.append(salary_from)

        if salary_to:
            query += " AND salary <= %s"
            params.append(salary_to)

        cursor.execute(query, params)
        vacancies = cursor.fetchall()

        html = ''
        if vacancies:
            html = "<h2>Найденные вакансии:</h2><ul>"
            for vacancy in vacancies:
                html += f"""
                    <li>
                        <h3><a href="{vacancy[4]}">{vacancy[1]}</a></h3>
                        <p>Компания: {vacancy[2]}</p>
                        <p>Зарплата: {vacancy[3]}</p>
                        <p>Город: {vacancy[6]}</p>
                        <p>Опубликована: {vacancy[7]}</p>
                        <p>Создана: {vacancy[8]}</p>
                        <p>Ссылка на отклик: {vacancy[9]}</p>
                        <p>Ссылка на вакансию: {vacancy[10]}</p>
                        <p>График работы: {vacancy[11]}</p>
                        <p>Тип занятости: {vacancy[12]}</p>
                    </li>
                """
            html += "</ul>"
        else:
            html = "<p>Вакансии не найдены.</p>"

        return html
    else:
        return "Ошибка подключения к базе данных."

@app.route('/results', methods=['POST', 'GET'])
def results():
    conn = connect_to_db()
    if conn:
        create_vacancies_table(conn)
        keyword = request.form.get('keyword') or request.args.get('keyword')
        parsed_vacancies = parse_vacancies_by_keyword(keyword, conn)

        city = request.form.get('city')
        schedule = request.form.get('schedule')
        employment = request.form.get('employment')
        salary_from = request.form.get('salary_from')
        salary_to = request.form.get('salary_to')

        schedule_names = set(v['schedule_name'] for v in parsed_vacancies if v['schedule_name'] is not None)
        employment_names = set(v['employment_name'] for v in parsed_vacancies if v['employment_name'] is not None)

        if parsed_vacancies:
            filtered_vacancies = []
            for vacancy in parsed_vacancies:
                if (
                    (not city or vacancy['area_name'] == city) and
                    (not schedule or vacancy['schedule_name'] == schedule) and
                    (not employment or vacancy['employment_name'] == employment) and
                    (not salary_from or salary_from == '' or (vacancy['salary'] and int(vacancy['salary'].split(' ')[0]) >= int(salary_from))) and
                    (not salary_to or salary_to == '' or (vacancy['salary'] and int(vacancy['salary'].split(' ')[0]) <= int(salary_to)))
                ):
                    filtered_vacancies.append(vacancy)

            return render_template('results.html', vacancies=filtered_vacancies, keyword=keyword, city=city, schedule=schedule, employment=employment, salary_from=salary_from, salary_to=salary_to, schedule_names=schedule_names, employment_names=employment_names)
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