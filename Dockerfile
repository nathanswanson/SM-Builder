FROM ubuntu:25.04

WORKDIR /app

# backend
COPY server_manager*.whl /app/
# frontend
COPY frontend/ /srv/

RUN apt-get update && \
    apt-get install -y unzip pipx docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pipx install server_manager*.whl && rm server_manager*.whl

EXPOSE 8000

VOLUME [ "/data"]
ENTRYPOINT [ "/root/.local/bin/server_manager" ]
