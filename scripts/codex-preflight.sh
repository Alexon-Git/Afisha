#!/usr/bin/env bash
# Read-only diagnostic. Safe with spaces and Cyrillic in workspace path.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
cd "$ROOT" || exit 1

printf '\nAfisha / Codex — проверка среды\n'
printf 'Рабочая папка: %s\n' "$ROOT"
if [ ! -d .git ]; then
  printf '[ERROR] Это не Git checkout. Сначала клонируй Afisha в эту папку.\n'
  exit 1
fi

origin=$(git remote get-url origin 2>/dev/null || true)
case "$origin" in
  *github.com/Alexon-Git/Afisha* ) printf '[OK] Git origin — Afisha\n' ;;
  * ) printf '[WARN] Git origin не совпадает с ожидаемым репозиторием. Проверь вручную.\n' ;;
esac
printf '[INFO] Текущая ветка: %s\n' "$(git branch --show-current 2>/dev/null)"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  printf '[WARN] Есть незакоммиченные изменения (содержимое не выводится).\n'
else
  printf '[OK] Рабочая копия без локальных изменений.\n'
fi

for item in git python3 node npm codex bun docker; do
  if command -v "$item" >/dev/null 2>&1; then
    printf '[OK] %s доступен\n' "$item"
  else
    printf '[INFO] %s не найден в PATH\n' "$item"
  fi
done

if [ -x backend/.venv/bin/python ]; then
  printf '[OK] Python venv создан\n'
else
  printf '[INFO] Python venv ещё не создан (backend/.venv)\n'
fi
if [ -d frontend/node_modules ]; then
  printf '[OK] npm dependencies установлены\n'
else
  printf '[INFO] npm dependencies ещё не установлены\n'
fi
if [ -f backend/.env ]; then
  printf '[OK] backend/.env существует (значения не проверяются и не печатаются)\n'
else
  printf '[INFO] backend/.env отсутствует. Создай из backend/env.example и замени заглушки.\n'
fi

CODEX_PATH=$(printenv CODEX_HOME 2>/dev/null || true)
if [ -z "$CODEX_PATH" ]; then CODEX_PATH="$HOME/.codex"; fi
if [ -d "$CODEX_PATH/skills/gstack" ]; then
  printf '[OK] Найден runtime gstack в Codex skills\n'
else
  printf '[INFO] gstack не обнаружен в %s/skills/gstack\n' "$CODEX_PATH"
fi
if [ -f .agents/skills/afisha-onboard/SKILL.md ]; then
  printf '[OK] Локальный скилл afisha-onboard готов\n'
fi
if [ -f .agents/skills/afisha-p0-review/SKILL.md ]; then
  printf '[OK] Локальный скилл afisha-p0-review готов\n'
fi
printf '\nПроверка завершена. Код и настройки не изменялись.\n'
