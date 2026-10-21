#!/bin/sh
# Start exited containers in this Compose project.
#
# restart=always brings a container back after a crash, and again when dockerd
# itself restarts. It does not start a container Docker stopped on purpose.
# The nginx image uses SIGQUIT for that stop (the "signal 3 (SIGQUIT) received,
# shutting down" lines). This loop starts those containers.
#
# A container must stay exited for several passes so `compose down` can remove
# it first. ./deploy.sh --down also stops this service before the others.

PASSES_BEFORE_START=4
INTERVAL_SECONDS=10
STAMP_DIR=/tmp/ensure-running-stamps

trap 'exit 0' TERM INT

sleep_interruptible() {
  # Foreground sleep. Backgrounding sleep and waiting on it returns immediately
  # when this shell is PID 1, which skips the grace period and can start
  # containers while `compose down` is removing them.
  sleep "$1" || true
}

mkdir -p "$STAMP_DIR"

echo "ensure-running: waiting for the Docker socket..."
while [ ! -S /var/run/docker.sock ]; do
  sleep_interruptible 2
done

project=""
while [ -z "$project" ]; do
  self_id="$(cat /etc/hostname)"
  project="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$self_id" 2>/dev/null || true)"
  if [ -z "$project" ]; then
    echo "ensure-running: compose project label not available yet"
    sleep_interruptible 2
  fi
done

echo "ensure-running: watching project ${project}"

while true; do
  if ! ids="$(docker ps -aq --filter "label=com.docker.compose.project=${project}" --filter "status=exited" 2>/tmp/ensure-running-ps.err)"; then
    echo "ensure-running: docker ps failed: $(cat /tmp/ensure-running-ps.err 2>/dev/null)"
    sleep_interruptible "$INTERVAL_SECONDS"
    continue
  fi

  seen_ids=""
  for id in $ids; do
    [ -n "$id" ] || continue
    service="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.service"}}' "$id" 2>/dev/null || true)"
    if [ -z "$service" ] || [ "$service" = "ensure-running" ]; then
      continue
    fi
    seen_ids="${seen_ids} ${id}"
    stamp="${STAMP_DIR}/${id}"
    count=0
    if [ -f "$stamp" ]; then
      read -r count < "$stamp" || count=0
    fi
    case "$count" in
      ''|*[!0-9]*) count=0 ;;
    esac
    count=$((count + 1))
    echo "$count" > "$stamp"
    if [ "$count" -eq 1 ]; then
      echo "ensure-running: ${service} is exited; will start it if it stays down"
    fi
    if [ "$count" -ge "$PASSES_BEFORE_START" ]; then
      echo "ensure-running: starting ${service} (${id})"
      if docker start "$id"; then
        rm -f "$stamp"
      fi
    fi
  done

  for stamp in "$STAMP_DIR"/*; do
    [ -f "$stamp" ] || continue
    id="$(basename "$stamp")"
    case " ${seen_ids} " in
      *" ${id} "*) ;;
      *) rm -f "$stamp" ;;
    esac
  done

  sleep_interruptible "$INTERVAL_SECONDS"
done
