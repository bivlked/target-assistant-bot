#!/usr/bin/env python3
"""
Скрипт для перезапуска GitHub Pages deployment в случае временных ошибок.
"""

import os
import sys
import time
import requests  # type: ignore[import-untyped]
from typing import Optional


def get_latest_workflow_run(
    owner: str, repo: str, workflow_name: str, token: str
) -> Optional[dict]:
    """Получить последний запуск workflow."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/runs"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        runs = response.json()["workflow_runs"]
        if runs:
            return runs[0]
    return None


def rerun_workflow(owner: str, repo: str, run_id: int, token: str) -> bool:
    """Перезапустить workflow."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
    response = requests.post(url, headers=headers)

    return response.status_code == 201


def trigger_workflow_dispatch(
    owner: str, repo: str, workflow_name: str, token: str, branch: str = "main"
) -> bool:
    """Запустить workflow вручную через workflow_dispatch."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"
    data = {"ref": branch}

    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 204


def main():
    # Параметры репозитория
    owner = "bivlked"
    repo = "target-assistant-bot"
    workflow_name = "docs-deploy.yml"

    # Получить токен из переменной окружения
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Ошибка: Не найден GITHUB_TOKEN в переменных окружения")
        print("Установите токен: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)

    print(f"Проверяю последний запуск workflow '{workflow_name}'...")

    # Получить последний запуск
    latest_run = get_latest_workflow_run(owner, repo, workflow_name, token)

    if latest_run:
        run_id = latest_run["id"]
        status = latest_run["status"]
        conclusion = latest_run["conclusion"]

        print(
            f"Последний запуск: ID={run_id}, Status={status}, Conclusion={conclusion}"
        )

        if status == "completed" and conclusion == "failure":
            # Проверить, была ли это ошибка 504
            print("Обнаружен неудачный запуск. Перезапускаю...")

            if rerun_workflow(owner, repo, run_id, token):
                print("✅ Workflow успешно перезапущен!")
                print(
                    f"Проверьте статус: https://github.com/{owner}/{repo}/actions/runs/{run_id}"
                )
            else:
                print("❌ Не удалось перезапустить workflow")
                print("Попробуйте перезапустить вручную через веб-интерфейс GitHub")
        else:
            print("Последний запуск не требует перезапуска")
    else:
        print("Не удалось получить информацию о последнем запуске")
        print("Попробуйте запустить workflow вручную через веб-интерфейс")


if __name__ == "__main__":
    main()
