#!/usr/bin/env bash
# Pull-деплой universal-bot: сервер сам забирает main, когда CI для коммита зелёный.
#
# Зачем: SSH-деплой из GitHub Actions зависел от секретов и доступности порта 22
# с раннеров GitHub. Здесь деплой идёт изнутри VPS, поэтому не зависит ни от
# секретов, ни от внешнего SSH. Запускается таймером universal-bot-deploy.timer.
#
# Поведение:
#   - нет новых коммитов   -> тихий выход 0;
#   - CI ещё идёт или упал -> выход 0, попробуем на следующем тике;
#   - CI зелёный           -> git merge --ff-only, pip install (если нужно),
#                             restart сервиса, проверка is-active;
#   - сервис не поднялся  -> откат на прежний коммит и выход 1.

set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/kvg/universal-bot}"
BRANCH="${BRANCH:-main}"
REPO="${REPO:-GorinKV/universal-bot}"
SERVICE="${SERVICE:-universal-bot}"
LOG="${LOG:-$HOME/deploy.log}"
STATE_FILE="${STATE_FILE:-$HOME/.cache/universal-bot-deploy.state}"

log() { echo "$(date -Is) $*"; }

cd "$REPO_DIR"

git rev-parse --git-dir >/dev/null 2>&1 || { log "не git-репозиторий: $REPO_DIR"; exit 1; }

git fetch --quiet --prune origin "$BRANCH"
local_sha="$(git rev-parse HEAD)"
remote_sha="$(git rev-parse "origin/$BRANCH")"

if [ "$local_sha" = "$remote_sha" ]; then
    exit 0
fi

# Статус CI именно для этого коммита (публичный API, без токена)
ci_status="$(
    curl -fsS --max-time 20 \
        "https://api.github.com/repos/$REPO/actions/runs?head_sha=$remote_sha&per_page=1" \
    | /usr/bin/python3 -c 'import json,sys
runs = ((json.load(sys.stdin) or {}).get("workflow_runs") or [])
if not runs:
    print("none none")
else:
    r = runs[0]
    print(str(r.get("status")) + " " + str(r.get("conclusion")))' \
    2>/dev/null || echo "api_error"
)"

if [ "$ci_status" != "completed success" ]; then
    # Не засоряем журнал: пишем только при смене состояния для этого коммита
    state="$remote_sha $ci_status"
    if [ "$(cat "$STATE_FILE" 2>/dev/null || true)" != "$state" ]; then
        log "ждём CI для ${remote_sha:0:7}: $ci_status"
        echo "$state" > "$STATE_FILE" 2>/dev/null || true
    fi
    exit 0
fi

log "деплой ${local_sha:0:7} -> ${remote_sha:0:7}"

git merge --ff-only "origin/$BRANCH" >/dev/null

# Зависимости переустанавливаем только если менялся pyproject.toml
if ! git diff --quiet "$local_sha" "$remote_sha" -- pyproject.toml; then
    log "обновляю зависимости"
    .venv/bin/pip install -q -e . 2>&1 | tail -3
fi

sudo -n /usr/bin/systemctl restart "$SERVICE"

# Ждём запуска до 20 секунд
for _ in $(seq 1 20); do
    systemctl is-active --quiet "$SERVICE" && break
    sleep 1
done

if systemctl is-active --quiet "$SERVICE"; then
    log "успех: $SERVICE активен на ${remote_sha:0:7}"
    echo "$remote_sha deployed" > "$STATE_FILE" 2>/dev/null || true
    exit 0
fi

log "ошибка: $SERVICE не поднялся, откат на ${local_sha:0:7}"
git reset --hard "$local_sha" >/dev/null
.venv/bin/pip install -q -e . 2>&1 | tail -3 || true
sudo -n /usr/bin/systemctl restart "$SERVICE" || true
exit 1
