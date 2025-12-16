"""
Tenant Controller - Polls PostgreSQL and reconciles Kubernetes resources.

Architecture:
  Server Manager (API) → PostgreSQL ← Tenant Controller → Kubernetes

The controller reads server/tenant configurations from the database
and ensures the corresponding K8s resources exist.
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass

import kubernetes
from kubernetes.client import ApiException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))  # seconds
DB_CONNECTION = os.getenv("SM_DB_CONNECTION", "")
USE_INCLUSTER = os.getenv("KUBERNETES_SERVICE_HOST") is not None


@dataclass
class ServerConfig:
    """Represents a server configuration from the database."""

    id: int
    name: str
    container_name: str
    template_image: str
    template_name: str
    node_name: str
    tenant_id: int
    template_volumes: list[str] | None
    template_ports: list[int] | None
    tenant_name: str
    env: dict
    cpu: int | None
    memory: int | None
    disk: int | None
    ports: list[int]


def get_db_session():
    """Create database session."""
    if not DB_CONNECTION:
        raise ValueError("SM_DB_CONNECTION environment variable is required")
    engine = create_engine(DB_CONNECTION)
    Session = sessionmaker(bind=engine)
    return Session()


def calculate_server_hash(server: ServerConfig) -> str:
    """Calculate a deterministic hash of the server configuration."""
    data = server.__dict__.copy()
    # Serialize to JSON with sorted keys to ensure consistency
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def fetch_template_by_id(session, template_id: int) -> dict | None:
    """Fetch template details by ID."""
    query = text("SELECT * FROM templates WHERE id = :template_id")
    result = session.execute(query, {"template_id": template_id}).fetchone()
    return dict(result) if result else None


def fetch_servers_from_db(session) -> list[ServerConfig]:
    """Fetch all server configurations from the database."""
    query = text("""
        SELECT DISTINCT ON (s.id)
            s.id,
            s.name,
            s.container_name,
            s.env,
            s.cpu,
            s.memory,
            s.disk,
            s.port,
            t.image as template_image,
            t.exposed_volumes as template_volumes,
            t.name as template_name,
            n.name as node_name,
            u.id as tenant_id,
            u.username as tenant_name
        FROM servers s
        JOIN templates t ON s.template_id = t.id
        JOIN nodes n ON s.node_id = n.id
        JOIN serveruserlink sul ON s.id = sul.server_id
        JOIN users u ON sul.user_id = u.id
        ORDER BY s.id, sul.server_id
    """)

    result = session.execute(query)
    servers = []
    for row in result:
        servers.append(
            ServerConfig(
                id=row.id,
                name=row.name,
                container_name=row.container_name or f"server-{row.id}",
                template_image=row.template_image,
                template_name=row.template_name,
                node_name=row.node_name,
                tenant_id=row.tenant_id,
                tenant_name=row.tenant_name,
                template_volumes=row.template_volumes,
                template_ports=row.template_ports,
                env=row.env or {},
                cpu=row.cpu,
                memory=row.memory,
                disk=row.disk,
                ports=row.port or [],
            )
        )
    return servers


def update_namespace(name: str, core_api: kubernetes.client.CoreV1Api) -> bool:
    """Ensure a namespace exists, create if not. Returns True if created."""
    try:
        core_api.read_namespace(name=name)
        return False
    except ApiException as e:
        if e.status == 404:
            core_api.create_namespace(body={"metadata": {"name": name}})
            logger.info(f"Created namespace: {name}")
            return True
        raise


def update_pvc(
    name: str,
    namespace: str,
    storage_size: str,
    storage_class: str,
    core_api: kubernetes.client.CoreV1Api,
) -> bool:
    """Ensure a PVC exists, create if not. Returns True if created."""
    try:
        core_api.read_namespaced_persistent_volume_claim(name=name, namespace=namespace)
        return False
    except ApiException as e:
        if e.status == 404:
            pvc_body = {
                "metadata": {"name": name},
                "spec": {
                    "accessModes": ["ReadWriteOnce"],
                    "storageClassName": storage_class,
                    "resources": {"requests": {"storage": storage_size}},
                },
            }
            core_api.create_namespaced_persistent_volume_claim(
                namespace=namespace, body=pvc_body
            )
            logger.info(f"Created PVC: {name} in namespace {namespace}")
            return True
        raise


def update_deployment(
    server: ServerConfig, namespace: str, apps_api: kubernetes.client.AppsV1Api
) -> bool:
    """Ensure a deployment exists for the server, create/update if needed."""
    deployment_name = f"server-{server.id}"
    config_hash = calculate_server_hash(server)

    # Build resource requirements
    resources = {"requests": {}, "limits": {}}
    if server.cpu:
        resources["requests"]["cpu"] = f"{server.cpu}m"
        resources["limits"]["cpu"] = f"{server.cpu}m"
    if server.memory:
        resources["requests"]["memory"] = f"{server.memory}Gi"
        resources["limits"]["memory"] = f"{server.memory}Gi"

    # Build environment variables
    env_vars = [{"name": k, "value": str(v)} for k, v in server.env.items()]

    # Build container ports
    container_ports = [{"containerPort": p} for p in server.ports]

    deployment_spec = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": deployment_name,
            "namespace": namespace,
            "labels": {
                "app": deployment_name,
                "server-manager.io/server-id": str(server.id),
                "server-manager.io/template": server.template_name,
            },
            "annotations": {"server-manager.io/config-hash": config_hash},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": deployment_name}},
            "template": {
                "metadata": {"labels": {"app": deployment_name}},
                "spec": {
                    "securityContext": {
                        "fsGroup": 1000,
                        "fsGroupChangePolicy": "OnRootMismatch",
                    },
                    "containers": [
                        {
                            "name": server.container_name,
                            "image": server.template_image,
                            "securityContext": {
                                "runAsUser": 1000,
                                "runAsGroup": 1000,
                                "runAsNonRoot": True,
                            },
                            "env": env_vars,
                            "ports": container_ports,
                            "resources": resources if resources["requests"] else {},
                            "volumeMounts": [
                                {
                                    "name": "server-data",
                                    "mountPath": "/data",
                                },
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "server-data",
                            "persistentVolumeClaim": {
                                "claimName": f"server-{server.id}-pvc",
                            },
                        },
                    ],
                },
            },
        },
    }

    try:
        existing = apps_api.read_namespaced_deployment(
            name=deployment_name, namespace=namespace
        )
        existing_hash = existing.metadata.annotations.get(  # type: ignore
            "server-manager.io/config-hash", ""
        )

        if existing_hash != config_hash:
            logger.info(
                f"Updating deployment {deployment_name} in namespace {namespace}"
            )
            apps_api.patch_namespaced_deployment(
                name=deployment_name, namespace=namespace, body=deployment_spec
            )
            return True
        else:
            logger.debug(
                f"Deployment {deployment_name} in namespace {namespace} is up to date"
            )
            return False

    except ApiException as e:
        if e.status == 404:
            logger.info(
                f"Creating deployment {deployment_name} in namespace {namespace}"
            )
            apps_api.create_namespaced_deployment(
                namespace=namespace, body=deployment_spec
            )
            return True
        else:
            logger.error(f"Error reconciling deployment {deployment_name}: {e}")
            raise


def update_service(
    server: ServerConfig, namespace: str, core_api: kubernetes.client.CoreV1Api
) -> bool:
    """Ensure a service exists for the server."""
    service_name = f"server-{server.id}-svc"
    deployment_name = f"server-{server.id}"

    if not server.ports:
        return False

    service_ports = [
        {"port": p, "targetPort": p, "name": f"port-{p}"} for p in server.ports
    ]

    service_spec = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": service_name,
            "namespace": namespace,
        },
        "spec": {
            "type": "NodePort",
            "selector": {"app": deployment_name},
            "ports": service_ports,
        },
    }

    try:
        core_api.read_namespaced_service(name=service_name, namespace=namespace)
        return False
    except ApiException as e:
        if e.status == 404:
            core_api.create_namespaced_service(namespace=namespace, body=service_spec)
            logger.info(f"Created service: {service_name} in namespace {namespace}")
            return True
        raise


def reconcile_server(
    server: ServerConfig,
    core_api: kubernetes.client.CoreV1Api,
    apps_api: kubernetes.client.AppsV1Api,
    storage_class: str = "tenant-storage-class",
):
    """Reconcile K8s resources for a single server."""
    # missing data must fail fast
    assert server.template_image, "Template image is required"
    assert server.template_name, "Template name is required"
    assert server.node_name, "Node name is required"

    # Each tenant (user) gets their own namespace
    namespace = f"tenant-{server.tenant_id}"
    logger.debug(
        f"Reconciling server: {server.name} (id={server.id}) in namespace {namespace}"
    )

    # Ensure namespace exists
    update_namespace(namespace, core_api)

    # Ensure PVC exists
    storage_size = f"{server.disk}Gi"
    update_pvc(
        name=f"server-{server.id}-pvc",
        namespace=namespace,
        storage_size=storage_size,
        storage_class=storage_class,
        core_api=core_api,
    )

    # Ensure deployment exists
    update_deployment(server, namespace, apps_api)

    # Ensure service exists
    update_service(server, namespace, core_api)


def cleanup_orphaned_resources(
    servers: list[ServerConfig],
    core_api: kubernetes.client.CoreV1Api,
    apps_api: kubernetes.client.AppsV1Api,
):
    """Remove K8s resources for servers no longer in the database."""
    server_ids = {str(s.id) for s in servers}

    # Get all tenant namespaces
    tenant_namespaces = {f"tenant-{s.tenant_id}" for s in servers}

    for namespace in tenant_namespaces:
        try:
            deployments = apps_api.list_namespaced_deployment(
                namespace=namespace, label_selector="server-manager.io/server-id"
            )

            for deployment in deployments.items:
                labels = deployment.metadata.labels or {}
                server_id = labels.get("server-manager.io/server-id")

                if server_id and server_id not in server_ids:
                    logger.info(
                        f"Cleaning up orphaned deployment: {deployment.metadata.name}"
                    )
                    apps_api.delete_namespaced_deployment(
                        name=deployment.metadata.name, namespace=namespace
                    )

                    # Also clean up associated service
                    service_name = f"server-{server_id}-svc"
                    try:
                        core_api.delete_namespaced_service(
                            name=service_name, namespace=namespace
                        )
                        logger.info(f"Cleaned up orphaned service: {service_name}")
                    except ApiException as e:
                        if e.status != 404:
                            raise
        except ApiException as e:
            logger.warning(f"Error during cleanup in namespace {namespace}: {e}")


def main():
    """Main controller loop."""
    logger.info("Starting Tenant Controller")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info(
        f"Database: {DB_CONNECTION[:30]}..." if DB_CONNECTION else "Database: NOT SET"
    )

    # Initialize Kubernetes client
    if USE_INCLUSTER:
        kubernetes.config.load_incluster_config()
        logger.info("Using in-cluster Kubernetes config")
    else:
        kubernetes.config.load_kube_config()
        logger.info("Using local kubeconfig")

    core_api = kubernetes.client.CoreV1Api()
    apps_api = kubernetes.client.AppsV1Api()

    # Verify K8s connection
    version_api = kubernetes.client.VersionApi()
    version_info = version_api.get_code()
    logger.info(f"Connected to Kubernetes: {version_info.git_version}")  # type: ignore

    # Main reconciliation loop
    while True:
        try:
            session = get_db_session()
            servers = fetch_servers_from_db(session)
            logger.info(f"Found {len(servers)} server in database")

            for server in servers:
                try:
                    reconcile_server(server, core_api, apps_api)
                except Exception as e:
                    logger.error(f"Error reconciling server {server.name}: {e}")

            # Cleanup orphaned resources
            cleanup_orphaned_resources(servers, core_api, apps_api)

            session.close()

        except Exception as e:
            logger.error(f"Error in reconciliation loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
