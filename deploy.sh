#!/bin/sh

IMAGE_NAME="whale-alert"
MY_USER="thanet31756"

echo "STOP CONTAINNER"
docker rm $(docker stop $(docker ps -a -q --filter="name=$IMAGE_NAME"))

echo "DELETE IMAGE"
docker rmi $(docker images --format '{{.Repository}}:{{.Tag}}' | grep "$IMAGE_NAME")

docker rm $(docker stop $(docker ps -a -q --filter ancestor=<image-name> --format="{{.ID}}"))


echo "START PULL NEW IMAGE"
docker login -u "$MY_USER" -p 'eba259b2-c52b-4ab8-9231-2d956e5516ee'

docker pull "$MY_USER/$IMAGE_NAME:latest"

docker run -d --restart=always --name="whale-alert" -v /volume1/docker/whale-alert-env.txt:/app/.env -v /volume1/docker/prices.txt:/app/prices.txt "$MY_USER/$IMAGE_NAME:latest"
