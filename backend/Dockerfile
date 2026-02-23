FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["bash", "-lc", "python -m scripts.wait_for_db && alembic upgrade head && python -m scripts.seed_data && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
