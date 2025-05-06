# Как внести вклад

Спасибо, что хотите помочь развитию Target Assistant Bot!

## Требования к окружению
- Python 3.10–3.12
- Poetry **или** `pip + venv`
- Установлены [pre-commit](https://pre-commit.com/) хуки: `pre-commit install`

## Процесс
1. Форкайте репозиторий и создавайте ветку от `main`: `git checkout -b feat/my-feature`.
2. Вносите изменения.
3. Запустите `pre-commit run -a` и убедитесь, что все хукы пройдены.
4. Запустите тесты: `pytest`.
5. Коммиты формируйте по [Conventional Commits](https://www.conventionalcommits.org/ru/v1.0.0/).
6. Откройте Pull Request и заполните шаблон.

## Проверка
CI запустит Ruff, MyPy, pytest с покрытием и проверку плейсхолдеров. PR должен быть «зелёным».

## Кодекс поведения
Мы придерживаемся [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Будьте вежливы и уважайте других. 