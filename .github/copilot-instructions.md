## Overview

This project is a web-based server manager with a FastAPI backend and a React frontend. The entire stack is containerized and managed with Docker Compose.

-   **`SM-Backend/`**: A Python FastAPI application serving a REST and WebSocket API.
-   **`SM-Frontend/`**: A React/TypeScript single-page application built with Vite.
-   **`builder/`**: Contains the Docker Compose configuration to build and run the entire application stack. This is the main entry point for development.
-   **`conf/`**: Holds the Caddy server configuration for reverse proxying.

## Key Architectural Concepts

-   **Service Orchestration**: The `builder/compose.yml` and `builder/compose.override.yml` files define the services. The application is intended to be run via Docker Compose.
-   **Backend API**: The FastAPI backend in `SM-Backend/src/server_manager` provides the core business logic. Key files include `webservice.py` (the main FastAPI app) and the various API routers in `api/`.
-   **Frontend Application**: The frontend in `SM-Frontend/src` is a modern React application using Chakra UI for components and `hey-api` for type-safe API calls generated from the backend's OpenAPI schema.
-   **Real-time Updates**: The backend uses WebSockets for real-time communication with the frontend.

## Development Workflow

### Running the Application

The primary way to run the application for development is from the `builder/` directory.

1.  **Create a `.env` file** in the `builder/` directory. You can copy the example from the `builder/README.md`.
2.  **Build and run the services**:
    ```bash
    docker compose up --build
    ```

### Backend Development

-   The backend code is in `SM-Backend/src/server_manager`.
-   Dependencies are managed with `pyproject.toml`.
-   Tests are located in `SM-Backend/tests/` and can be run with `pytest`. For consistency, unify mock data and fixtures in `conftest.py` whenever possible.
-   Avoid using unittest-style mocks; prefer `pytest-mock` fixtures for better integration with pytest.
-   Run tests with command:
    ```bash
    hatch test
    ```
    inside SM-Backend directory.
### Frontend Development

-   The frontend code is in `SM-Frontend/src/`.
-   Dependencies are managed with `package.json`. Use `npm install` to install them.
-   The frontend dev server must be run inside the Docker container for proper API communication. Use `docker compose up` from the `builder/` directory to start both backend and frontend.
-   The API client is generated using `openapi-ts` based on the `openapi.json` from the backend. To update the client, first ensure the backend is running and then run `npm run openapi-ts` from the `SM-Frontend` directory.
-   Avoid using barrel imports (`import { ... } from './components'`) if a direct import (`import { MyComponent } from './components/MyComponent'`) is available. This improves tree-shaking and reduces bundle sizes.

## Project-Specific Conventions

-   **API Communication**: The frontend communicates with the backend via a generated OpenAPI client (`SM-Frontend/src/lib/hey-api`). When adding new backend endpoints, remember to regenerate the frontend client.
-   **Configuration**: Application configuration is managed through environment variables loaded from the `.env` file in the `builder` directory.
-   **Containerization**: All services are containerized. See the `Dockerfile` and `Dockerfile.dev` files in the respective `SM-Backend` and `SM-Frontend` directories. The `builder/compose.yml` file ties them all together.
-   **Reverse Proxy**: Caddy is used as a reverse proxy. The configuration is in `conf/CaddyFile.base` and `conf/CaddyFile.dev`.
