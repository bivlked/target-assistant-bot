#!/usr/bin/env python3
"""
Скрипт для проверки статуса GitHub Pages и помощи в восстановлении.
"""

import json
import sys
import webbrowser
from datetime import datetime


def check_pages_status():
    """Проверить статус GitHub Pages и предложить решения."""

    print("=== Проверка статуса GitHub Pages ===\n")

    # Информация о проблеме
    print("🔴 Обнаружена проблема: GitHub Pages deployment failed")
    print("📋 Ошибка: HttpError 504 (Gateway Timeout)")
    print("💡 Причина: Временная проблема на стороне GitHub\n")

    # Решения
    print("=== Рекомендуемые действия ===\n")

    print("1. БЫСТРОЕ РЕШЕНИЕ (Перезапуск через веб-интерфейс):")
    print("   - Откройте: https://github.com/bivlked/target-assistant-bot/actions")
    print(
        "   - Найдите последний failed workflow 'Deploy Sphinx Documentation to GitHub Pages'"
    )
    print("   - Нажмите на него, затем кнопку 'Re-run all jobs'")
    print("   - Или используйте прямую ссылку для запуска manual workflow:")
    print(
        "     https://github.com/bivlked/target-assistant-bot/actions/workflows/docs-deploy-manual.yml\n"
    )

    print("2. АВТОМАТИЧЕСКОЕ РЕШЕНИЕ (уже применено):")
    print("   - Обновлен workflow docs-deploy.yml с автоматическими повторами")
    print("   - Добавлен manual workflow docs-deploy-manual.yml")
    print("   - При следующем push в main, деплой будет автоматически повторяться\n")

    print("3. ПРОВЕРКА СТАТУСА GitHub:")
    print("   - GitHub Status: https://www.githubstatus.com/")
    print("   - GitHub Actions Status: https://www.githubstatus.com/history\n")

    print("4. АЛЬТЕРНАТИВНЫЙ ДЕПЛОЙ (если проблема сохраняется):")
    print("   - Можно временно использовать GitHub Pages из ветки gh-pages")
    print("   - Для этого нужно будет изменить настройки в Settings -> Pages\n")

    # Предложить открыть ссылки
    response = input("Открыть страницу Actions в браузере? (y/n): ")
    if response.lower() == "y":
        webbrowser.open("https://github.com/bivlked/target-assistant-bot/actions")

    response = input("Открыть GitHub Status для проверки? (y/n): ")
    if response.lower() == "y":
        webbrowser.open("https://www.githubstatus.com/")


def create_status_report():
    """Создать отчет о текущем статусе."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = {
        "timestamp": timestamp,
        "issue": "GitHub Pages deployment failed",
        "error": "HttpError 504 Gateway Timeout",
        "cause": "Temporary GitHub server issue",
        "solutions_applied": [
            "Added retry logic to docs-deploy.yml workflow",
            "Created manual deployment workflow",
            "Created retry script for automated recovery",
        ],
        "recommended_action": "Re-run the failed workflow through GitHub UI",
    }

    with open(".local/pages_status_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n✅ Отчет сохранен в .local/pages_status_report.json")


if __name__ == "__main__":
    check_pages_status()
    create_status_report()

    print("\n=== Дополнительная информация ===")
    print("📝 Изменения уже внесены в репозиторий:")
    print("   - .github/workflows/docs-deploy.yml (добавлены повторы)")
    print("   - .github/workflows/docs-deploy-manual.yml (ручной запуск)")
    print("   - scripts/retry_pages_deploy.py (автоматизация)")
    print("   - scripts/check_pages_status.py (этот скрипт)")
    print("\n🚀 Коммитните изменения и запушьте в GitHub для применения!")
