# server-manager — builder

Short, one-line description of what this component does (e.g., "Build helper for server-manager project — compiles assets, generates artifacts, and packages releases").

## Table of contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Features
- List of main capabilities (e.g., build, bundle, lint, versioning).
- Platform/OS notes if relevant.

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
make an .env file:
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
