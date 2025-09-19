#!/bin/bash

# Build the Docker image for the both platforms


docker buildx build --ssh default --platform linux/arm64 -t server-manager:arm64 --load .
# save the image to a tar file
docker save server-manager:arm64 -o server-manager-arm64.tar

# optional deploy to server
if [ "$1" == "deploy" ]; then
  scp server-manager-arm64.tar game-server@raspberrypi.home:/home/game-server/deploy/
  ssh game-server@raspberrypi.home "docker load -i /home/game-server/deploy/server-manager-arm64.tar"

  # also the Caddyfile, compose.yml
  # scp Caddyfile game-server@raspberrypi.home:/home/game-server/deploy/
  # scp compose.yml game-server@raspberrypi.home:/home/game-server/deploy/

  # restart server manager keeping other compose services up
  ssh game-server@raspberrypi.home "docker-compose -f /home/game-server/deploy/compose.yml up -d webserver"
fi
