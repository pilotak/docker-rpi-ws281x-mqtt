FROM python:3.8-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y git build-essential \
&& pip3 install --trusted-host pypi.python.org -r requirements.txt \
&& git clone --recurse-submodules https://github.com/rpi-ws281x/rpi-ws281x-python \
&& cd /app/rpi-ws281x-python/library \
&& python3 setup.py install

CMD ["python", "-u", "ws281x.py"]