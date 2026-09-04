# ECI Framework — multi-stage CPU image (edge/server/air-gapped via ECI_PROFILE).
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY protocol0 ./protocol0
RUN pip install --upgrade pip && pip install -e .[dev] && python -c "import eci; print(eci.__version__)"
ENV ECI_PROFILE=server ECI_PORT=8777
EXPOSE 8777
VOLUME ["/data"]
HEALTHCHECK --interval=60s --timeout=5s --retries=3 CMD python -m eci health --once || exit 1
ENTRYPOINT ["python", "-m", "eci"]
CMD ["health", "--serve", "--port", "8777"]
