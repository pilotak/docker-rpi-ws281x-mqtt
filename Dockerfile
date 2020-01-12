FROM python:3.8-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get -y --no-install-recommends install git build-essential \
&& pip3 install --trusted-host pypi.python.org -r requirements.txt \
&& git clone --recurse-submodules https://github.com/rpi-ws281x/rpi-ws281x-python \
&& cd /app/rpi-ws281x-python/library \
&& python3 setup.py install \
&& apt-get purge -y git ca-certificates build-essential \
&& apt-get autoremove -y \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

CMD ["python", "-u", "ws281x.py"]