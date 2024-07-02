import requests
import psycopg2
import time
import random
import json
from flask import Flask, render_template

access_token = 'USERSVJ0RLO8S59VV02DNJ4BHAR2SH5GIIL07LQ077ITDOHROFDL0JILTG1M12VI'

DB_HOST = 'localhost'
DB_NAME = 'vacancies'
DB_USER = 'postgres'
DB_PASSWORD = 'ahb837js'

keywords = 'python разработчик'

headers = {
    'Authorization': f'Bearer {access_token}',
}

# Пример запроса к API для получения информации о вакансиях
base_url = 'https://api.hh.ru/vacancies'
params = {
    'text': keywords,
    'per_page': 100,
}

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

def get_regions():
    regions_url = 'https://api.hh.ru/areas'
    try:
        response = requests.get(regions_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Ищем регион с именем 'Россия' и возвращаем его id
            for area in data:
                if area['name'] == 'Россия':
                    return [area['id']]
            print("Регион 'Россия' не найден в API HH.ru")
            return []
        else:
            print(f"Ошибка при получении списка регионов: {response.status_code}")
            return []
    except Exception as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

def parse_and_save_vacancies():
    conn = connect_to_db()
    if conn:
        cursor = conn.cursor()

        # Создание таблицы для хранения вакансий 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                company VARCHAR(255) NOT NULL,
                salary TEXT,
                url TEXT,
                region_id INTEGER
            );
        """)
        regions = get_regions()

        for region_id in regions:
            params = {'area': region_id, 'page': 0}
            while True:
                try:
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
                                if salary:
                                    salary_text = f"{salary['from']} - {salary['to']} {salary['currency']}"
                                else:
                                    salary_text = None

                                cursor.execute(
                                    """
                                    INSERT INTO vacancies (name, company, salary, url, region_id) 
                                    VALUES (%s, %s, %s, %s, %s);
                                    """,
                                    (name, company, salary_text, url, region_id)
                                )
                            conn.commit()


                        # Проверка на наличие следующей страницы
                            if params['page'] < data['pages'] - 1:
                                params['page'] += 1
                            else:
                                break  # Выход из цикла, если страница последняя
                        else:
                            print("В ответе API нет данных о вакансиях")
                            break
                    elif response.status_code == 429:  # Обработка ошибки "слишком много запросов"
                        print(f"Ошибка при запросе к API: {response.status_code}, слишком много запросов. Ожидание 10 секунд...")
                        time.sleep(10)
                    else:
                        print(f"Ошибка при запросе к API: {response.status_code}")
                        break
                except Exception as e:
                    print(f"Ошибка при запросе к API: {e}")
                    break
                time.sleep(random.uniform(1,3))  # Пауза между запросами в пределах 1-3 секунд

            # Сохранение изменений в базе данных
            conn.commit()

        # Закрытие курсора и соединения
        cursor.close()
        conn.close()
def delete_table():
    """Удаляет таблицу vacancies из базы данных."""
    conn = connect_to_db()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DROP TABLE IF EXISTS vacancies")
            conn.commit()
            print("Таблица vacancies удалена")
        except Exception as e:
            print(f"Ошибка при удалении таблицы: {e}")
        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    try:
        parse_and_save_vacancies()
    except Exception as e:
        print(f"Ошибка во время парсинга: {e}")
        delete_table() # Удаляем таблицу в случае ошибки




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

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
