FROM --platform=linux/amd64 python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=True
ENV PRODUCTION=1

COPY pyproject.toml .
ADD src/pprl src/pprl
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir .

COPY .env .
COPY scripts/server.py .

CMD [ "python", "server.py" ]
