#!/bin/bash

# kata



if [ "$1" == "clean" ]; then
  kubectl delete -k ./k8s/overlays/dev

  exit 0
fi
if [ "$1" == "create" ]; then
  minikube start --network-plugin=cni --enable-default-cni --container-runtime=cri-o --vm-driver kvm2 --bootstrapper=kubeadm    --nodes=1

  # addons for minikube
  minikube addons enable metrics-server


  kubectl label nodes minikube role=core
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


# Install NGINX Gateway Fabric
kubectl apply --server-side -f  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
kubectl kustomize "https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.2.1" | kubectl apply -f -
kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.2.1/deploy/crds.yaml
kubectl apply -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.2.1/deploy/default/deploy.yaml


# Install NFS CSI Driver
curl -skSL https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/v4.12.1/deploy/install-driver.sh | bash -s v4.12.1 --


# install SM-k8s resources
kubectl apply -k ./k8s/overlays/dev
# kubectl wait --for=condition=available --timeout=120s -n www statefulset.apps/postgresql
kubectl wait --for=condition=available --timeout=120s -n www deployment/frontend-deployment