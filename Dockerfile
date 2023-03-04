FROM python:3.9-alpine as ffmpeg

#FROM jsavargas/zspotify as base

RUN apk --update add git ffmpeg

FROM ffmpeg as builder

WORKDIR /install

RUN apk add gcc libc-dev zlib zlib-dev jpeg-dev
COPY requirements.txt requirements.txt
RUN /usr/local/bin/python -m pip install --upgrade pip && \
    pip install --prefix="/install" -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

FROM python:3.9-alpine

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --from=ffmpeg /usr/ /usr/

COPY *.py /app/

VOLUME /download /config

ENTRYPOINT ["/usr/local/bin/python3", "main.py"]
