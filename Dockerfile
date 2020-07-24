FROM python:3.8-slim as builder

COPY ./requirements.txt /opt/requirements.txt

RUN apt-get update 

RUN apt-get install -y gcc make build-essential git scons swig
RUN pip3 install --no-warn-script-location --user -r /opt/requirements.txt

FROM python:3.8-slim as executor

COPY --from=builder /root/.local /root/.local
COPY ./effects.py /app/effects.py
CMD ["python", "-u", "/app/ws281x.py"]
COPY ./ws281x.py /app/ws281x.py

