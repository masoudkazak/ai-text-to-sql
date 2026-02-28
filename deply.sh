#!/usr/bin/env bash

set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $*"; }
fail() { echo -e "${RED}[deploy]${NC} $*"; exit 1; }

if [[ ! -f .env ]]; then
  fail ".env not found"
fi

log "Take latest version of repository"
git pull origin main

log "Build Images"
$COMPOSE build --no-cache

log "Running Containers"
$COMPOSE up -d

log "Waiting for project is ready..."
sleep 15

log "Get status..."
$COMPOSE ps

if curl -sf http://localhost/health > /dev/null 2>&1; then
  log "Project run successfully!"
else
  warn "Something is wrong!!!"
  $COMPOSE logs --tail=50 backend
fi