FROM alpine:3.12
LABEL Maintainer="Michael Stella <michael@jwplayer.com>"

ARG PIP_EXTRA_INDEX_URL
ENV PYTHON_EGG_CACHE=/tmp \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=0 \
    PIP_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_URL

ENTRYPOINT ["tini", "--", "rssalertbot"]

RUN addgroup bot \
    && adduser -D -G bot bot \
    && mkdir /home/bot/.aws \
    && chown -R bot:bot /home/bot

RUN apk add --no-cache \
        ca-certificates \
        libssl1.1 \
        python3 \
        py3-pip \
        tini \
        yaml \
    && rm -rf /var/cache/apk/*  \
    && ln -s /usr/bin/python3 /usr/bin/python

# install the application
COPY rssalertbot /app/rssalertbot
COPY CHANGELOG.rst MANIFEST.in setup.py /app/
WORKDIR /app
RUN pip install -e '.[dynamo,slack]'

# don't run as root
USER bot
CMD ["-c", "config.yaml"]
