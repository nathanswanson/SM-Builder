# server-manager — builder

server-manager is a web-based control plane for provisioning, configuring, and monitoring services and hosts. It combines a backend API, a single-page frontend, and supporting infrastructure (database, reverse proxy, and realtime channels).

Project highlights
- Purpose: manage server lifecycle, deployments, configuration, and health metrics from a unified UI and API.
- Architecture: backend FastAPI (REST/WebSocket), frontend react/vite/typescript, PostgreSQL for persistence, Caddy for TLS/reverse proxy, containerized for reproducible environments.
- Key features: environment-aware builds (DEV/PROD), websocket-backed realtime updates, dockerized services for simple local development.

How this repository (builder) fits
- This subproject builds the container images, assembly manifests, and local Docker Compose topology used to run the full system.
- Use the builder to produce consistent images and compose setups for development, testing, or edge deployments without manually wiring services.

Repository layout (high level)
- frontend/ - vite/react/chakra/hey-api frontend
- backend/ - fastapi/socket.io server

Getting started
- Create a .env (see Usage below) to configure secrets, hosts, and DB connection.
- Use docker compose build && docker compose up to build and run all components locally.


Where to go next
- Read the Usage and Installation sections below for step‑by‑step local development.
- Open issues or PRs for bugs, feature requests, or documentation improvements.

## Table of contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Requirements
- Linux, Windows(WSL)
- Docker

## Installation
Clone the repo and install dependencies:
```bash
git clone https://github.com/<org>/server-manager.git
cd server-manager/builder

```

## Usage
Make an .env file:

``` env
SECRET_KEY=
CADDY_FILE=CaddyFile
SQL_SERVER_PATH=postgresql://postgres:example@db:5432/postgres
TAG=amd64
CADDY_HOST=localhost
VITE_BACKEND_WEBSOCKET=wss://localhost:8000
VITE_BACKEND_HOST=https://localhost:8000
SM_ENV=DEV

```
run docker compose:
```bash
docker compose build
docker compose up
```

## License
MIT

## Authors / Maintainers
- Nathan Swanson <nathanswanson370@gmail.com>
