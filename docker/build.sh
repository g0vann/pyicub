#!/bin/bash

CACHE_BUST=$(date +%s)

LOCAL_USER_UID=$(id -u) \
LOCAL_USER_GID=$(id -g) \
CACHE_BUST=$CACHE_BUST \
# docker compose build
docker compose build