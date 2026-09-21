FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY app ./app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8004/health')"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]