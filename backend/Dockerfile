FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install flask flask-jwt-extended flask-cors psycopg2-binary redis

EXPOSE 5000

CMD ["python", "lib.py"]
