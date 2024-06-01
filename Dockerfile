FROM python:3.11-slim-bullseye

VOLUME [ "/app/media" ]

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash", "entrypoint.sh"]

EXPOSE 80