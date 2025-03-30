FROM python:3.11

WORKDIR /app

RUN pip install Flask

RUN pip install flasgger

RUN pip install pillow

COPY . .

EXPOSE 5000

CMD [ "python", "main.py" ]