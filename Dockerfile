FROM ubuntu:25.04

WORKDIR /app
COPY server-manager-frontend.zip server-manager-backend.zip /tmp/
RUN ls /tmp

RUN apt-get update && \
    apt-get install -y unzip pipx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN unzip /tmp/server-manager-backend.zip
RUN pipx install server_manager*.whl

# frontend
RUN unzip /tmp/server-manager-frontend.zip -d /data/static

EXPOSE 8000

VOLUME [ "/data"]
ENTRYPOINT [ "/root/.local/bin/server_manager" ]
