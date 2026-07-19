FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml setup.py .
RUN pip install --no-cache-dir .

COPY harness/ harness/
COPY demos/ demos/

EXPOSE 8000

CMD ["uvicorn", "harness.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]