FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src/ ./src/
COPY schema/ ./schema/
COPY ../contracts/ /app/contracts/
ENV APP_ENV=production APP_HOST=0.0.0.0 APP_PORT=8080
EXPOSE 8080
CMD ["python", "-m", "lingualive_api"]
