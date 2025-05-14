# Как внести вклад

Спасибо, что хотите помочь развитию Target Assistant Bot! Мы ценим любой вклад, будь то исправление ошибок, предложение новых функций или улучшение документации.

## Начало работы

### Требования к окружению
- Python 3.10–3.12 (рекомендуется использовать `pyenv` для управления версиями Python)
- Poetry **или** `pip` с виртуальным окружением (`venv`):
  ```bash
  # Используя venv (пример)
  python3 -m venv .venv
  source .venv/bin/activate  # для Linux/macOS
  # .venv\Scripts\activate   # для Windows
  pip install -U pip
  pip install -r requirements.txt
  # pip install -r requirements-dev.txt # Раскомментируйте, если dev-зависимости вынесены
  ```
- Установлены [pre-commit](https://pre-commit.com/) хуки:
  ```bash
  pip install pre-commit
  pre-commit install
  ```
  Это поможет автоматически форматировать код и запускать линтеры перед каждым коммитом.

### Рабочий процесс (Feature Branches)
Мы используем Feature Branch Workflow. Пожалуйста, придерживайтесь его:

1.  **Форк и клонирование**:
    *   Форкните [основной репозиторий](https://github.com/bivlked/target-assistant-bot) на GitHub.
    *   Клонируйте ваш форк локально: `git clone https://github.com/YOUR_USERNAME/target-assistant-bot.git`
    *   Добавьте основной репозиторий как upstream: `git remote add upstream https://github.com/bivlked/target-assistant-bot.git`

2.  **Создание ветки**:
    *   Перед началом работы убедитесь, что ваша локальная ветка `main` синхронизирована с `upstream/main`:
        ```bash
        git checkout main
        git pull upstream main --rebase
        ```
    *   Создайте новую ветку от `main` для вашей задачи:
        *   Для новой фичи: `git checkout -b feat/краткое-описание-фичи` (например, `feat/telegram-reminders`)
        *   Для исправления бага: `git checkout -b fix/описание-бага` (например, `fix/cache-invalidation-issue`)
        *   Используйте префиксы `feat/`, `fix/`, `docs/`, `style/`, `refactor/`, `test/`, `chore/`.

3.  **Внесение изменений**:
    *   Пишите код, добавляйте тесты для новых функций или исправлений.
    *   Старайтесь делать атомарные коммиты.

4.  **Проверки перед коммитом и пушем**:
    *   Запустите `pre-commit run -a` (или он сработает автоматически при `git commit`). Убедитесь, что все хуки (Black, Ruff, MyPy) пройдены успешно.
    *   Запустите тесты: `pytest -q`. Все тесты должны проходить.
    *   Проверьте покрытие тестами: `pytest --cov=.` (должно быть не ниже 80%).

5.  **Формирование коммитов**:
    *   Сообщения коммитов должны соответствовать спецификации [Conventional Commits](https://www.conventionalcommits.org/ru/v1.0.0/). Это помогает нам автоматически генерировать CHANGELOG и понимать историю изменений.
    *   Пример: `feat: add user authentication via phone number` или `fix: correct typo in welcome message`.

6.  **Push и Pull Request**:
    *   Отправьте вашу ветку в ваш форк: `git push origin feat/ваша-фича`.
    *   Создайте Pull Request (PR) из вашей feature-ветки в ветку `main` основного репозитория.
    *   Заполните шаблон PR, предоставьте понятное описание изменений и ссылку на связанный Issue (если есть).

## Проверка PR
*   CI (GitHub Actions) автоматически запустит все проверки (линтеры, тесты на разных версиях Python, анализ покрытия). PR должен быть «зелёным» перед мерджем.
*   Ожидайте код-ревью. Будьте готовы ответить на вопросы и внести доработки по результатам ревью.

## Кодекс поведения
Мы придерживаемся [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Пожалуйста, будьте вежливы, конструктивны и уважайте других участников.

Если у вас есть вопросы, не стесняйтесь создавать Issue или обсуждать их. Спасибо за ваш вклад! 