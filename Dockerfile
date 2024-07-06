FROM python:3.9


WORKDIR /add

EXPOSE 8000

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt


COPY . .


CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]