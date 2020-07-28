# Builder
FROM python:3.8-slim as builder

COPY ./requirements.txt ./

RUN apt update \
    && apt install -y --no-install-recommends gcc make build-essential scons swig \
    && pip3 install --user -r requirements.txt

# Executor
FROM python:3.8-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY ./effects.py ./ws281x.py ./

CMD ["python", "-u", "./ws281x.py"]