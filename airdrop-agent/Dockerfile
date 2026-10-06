FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:99

# virtual screen + VNC (so you can watch the agent and log in yourself)
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb x11vnc novnc websockify fluxbox \
        fonts-noto-color-emoji fonts-noto-cjk ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && chmod -R a+rx /ms-playwright

RUN useradd -m -u 1000 agent && mkdir -p /data && chown agent:agent /data

COPY agent ./agent
COPY examples ./examples
COPY start.sh .
COPY tests ./tests

USER agent
CMD ["bash", "start.sh"]
