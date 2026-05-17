FROM python:3.12-slim

WORKDIR /app

COPY app.pyz /tmp/app.pyz
RUN python -m zipfile -e /tmp/app.pyz /app \
    && rm /tmp/app.pyz

COPY overrides/ /app/

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade --target /app/site-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

RUN mkdir -p /app/levels /app/levels_cache /app/playlists

EXPOSE 3939

CMD ["python", "main.py"]
