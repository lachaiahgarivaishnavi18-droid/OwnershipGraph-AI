FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY alembic.ini .
COPY backend/migrations/ /app/backend/migrations/
COPY models/ /models/
RUN useradd -m appuser && mkdir -p /app/instance && chown -R appuser /app
USER appuser
EXPOSE 5000
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","2","--timeout","120","run:app"]
