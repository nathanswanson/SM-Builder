################################## BACKEND ##################################
FROM python:3.9.23-trixie AS backend-builder
ARG WEBSERVER_PATH=backend
ADD git@github.com:nathanswanson/server_manager.git /app/
WORKDIR /app

# install dependencies
RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install pipx -y

# build backend
RUN pipx run hatch build -t wheel

################################## FRONTEND ##################################
FROM node:trixie-slim AS frontend-builder
ARG FRONTEND_PATH=frontend
ARG VITE_BACKEND_WEBSOCKET=wss://home.nathanswanson.online
ARG VITE_BACKEND_HOST=https://home.nathanswanson.online
WORKDIR /app
ADD git@github.com:nathanswanson/frontend.git /app/
# install dependencies
RUN apt-get update -y
RUN apt-get upgrade -y



RUN npm install
RUN npm run build

################################## BASE ##################################
FROM ubuntu:25.04
ARG DB_PATH=dev.db

# install dependencies
RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install pipx -y
RUN pipx ensurepath

WORKDIR /app

COPY --from=backend-builder /app/dist/ /app/dist/
RUN pipx install /app/dist/*.whl

COPY --from=frontend-builder /app/dist/ /data/static/

EXPOSE 8000

VOLUME [ "/data", "/config"]
ENTRYPOINT [ "/root/.local/bin/server_manager" ]