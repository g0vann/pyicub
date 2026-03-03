#!/bin/bash

docker volume prune -f
docker compose build --no-cache
