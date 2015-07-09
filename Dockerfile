FROM python:2.7
RUN mkdir -p /usr/src/votemachine
WORKDIR /usr/src/votemachine
COPY requirements.txt /usr/src/votemachine/
RUN pip install -r requirements.txt
