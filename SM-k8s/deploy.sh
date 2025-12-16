#!/bin/bash

set -e  # Exit on error

if [ "$1" == "clean" ]; then
  kubectl delete -k ./k8s/overlays/dev
  exit 0
fi

if [ "$1" == "create" ]; then
  # if minikube is not running, start it
  if minikube status &> /dev/null; then
    echo "Minikube is already running"
  else
    minikube start --network-plugin=cni --container-runtime=cri-o --vm-driver kvm2 --bootstrapper=kubeadm --nodes=1 --cpus=12 --memory=12g
  fi

  # addons for minikube
  minikube addons enable metrics-server

  mkdir -p k8s/networking/base/certs
  # if k8s/networking/base/certs/* does not exist, create it
  if [ ! -f k8s/networking/base/certs/tls.crt ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout k8s/networking/base/certs/tls.key -out k8s/networking/base/certs/tls.crt -subj "/CN=ca"
    # trust the self-signed certificate for dev browser
    sudo cp k8s/networking/base/certs/tls.crt /usr/local/share/ca-certificates/
  fi
  
  docker build -t frontend-test:latest -f ./Dockerfile.frontend . 
  minikube image load frontend-test:latest
  docker build -t controller:latest ./controller
  minikube image load controller:latest

  exit 0
fi

if [ "$1" == "delete" ]; then
  minikube delete
  exit 0
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
  echo "Error: Cannot connect to Kubernetes cluster"
  exit 1
fi

# Install Kata Containers
echo "Installing Kata Containers..."
kataVer=$(curl -sSL https://api.github.com/repos/kata-containers/kata-containers/releases/latest | jq .tag_name | tr -d '"')
kataChart="oci://ghcr.io/kata-containers/kata-deploy-charts/kata-deploy"

helm upgrade -i kata-deploy "${kataChart}" --version "${kataVer}" --wait=false --timeout=3m 2>/dev/null || echo "Kata deployment initiated"

# Wait a bit for cluster to stabilize
sleep 10

# Install NGINX Gateway Fabric
echo "Installing NGINX Gateway Fabric CRDs..."
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.2.2" | kubectl apply -f -

echo "Installing NGINX Gateway Fabric..."
helm upgrade -i ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace \
  -n nginx-gateway \
  --set nginx.service.type=NodePort \
  --wait=false \
  --timeout=3m \
  2>/dev/null || echo "NGINX Gateway deployment initiated"

# Install local-path-provisioner for dev
echo "Installing local-path-provisioner..."
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml

# Wait for critical components
echo "Waiting for NGINX Gateway Fabric to be ready..."
kubectl wait --timeout=3m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available || echo "Warning: NGINX Gateway may not be fully ready"

# install SM-k8s resources
echo "Deploying SM-k8s resources..."
kubectl apply -k ./k8s/overlays/dev

echo "Deployment complete!"