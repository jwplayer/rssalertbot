FROM alpine:3.6
MAINTAINER Michael Stella <michael@jwplayer.com>

ARG PIP_EXTRA_INDEX_URL
ENV PYTHON_EGG_CACHE=/tmp \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=0 \
    PIP_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_URL

ENTRYPOINT ["tini", "--"]

RUN addgroup bot && adduser -D -G bot bot && mkdir /home/bot/.aws

RUN apk add --no-cache \
        ca-certificates \
        libssl1.0 \
        python3 \
        tini \
        yaml \
    && rm -rf /var/cache/apk/*  \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && pip3 install -U pip setuptools

# install the application
COPY rssalertbot /app/rssalertbot
COPY CHANGELOG.rst MANIFEST.in setup.py /app/
WORKDIR /app
RUN pip3 install '.[dynamo,slack]'

# don't run as root
USER bot
CMD ["rssalertbot", "-c", "config.yaml"]
