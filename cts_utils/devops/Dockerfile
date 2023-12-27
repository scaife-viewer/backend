from python:3.12-bookworm
WORKDIR /opt/cts-utils/src/
COPY tests/requirements.txt tests/requirements.txt
RUN pip install --disable-pip-version-check --upgrade pip setuptools wheel virtualenv
ENV PATH="/opt/cts-utils/bin:${PATH}" VIRTUAL_ENV="/opt/scaife-stack"
RUN set -x \
    && virtualenv /opt/cts-utils \
    && pip install -r tests/requirements.txt
COPY . .
