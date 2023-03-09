FROM python:3.10-alpine3.17
WORKDIR /bot
COPY . /bot
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "./bot.py"]