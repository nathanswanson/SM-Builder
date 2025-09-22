################################## BACKEND ##################################
FROM python:3.9.23-trixie AS backend-builder
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
ARG VITE_BACKEND_WEBSOCKET
ARG VITE_BACKEND_HOST
RUN echo ${VITE_BACKEND_HOST}
WORKDIR /app
ADD git@github.com:nathanswanson/frontend.git /app/
# install dependencies
RUN apt-get update -y
RUN apt-get upgrade -y



RUN npm install
RUN VITE_BACKEND_WEBSOCKET=${VITE_BACKEND_WEBSOCKET} VITE_BACKEND_HOST=${VITE_BACKEND_HOST} npm run build

################################## BASE ##################################
FROM ubuntu:25.04

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