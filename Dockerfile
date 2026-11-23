FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY landing_reports ./landing_reports
RUN pip install --no-cache-dir . && \
    useradd --system --uid 10001 app && mkdir -p /data && chown app:app /data
USER 10001:10001
ENTRYPOINT ["python", "-m", "landing_reports", "--config", "/app/config.json"]
