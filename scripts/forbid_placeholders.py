import re
import sys
import subprocess
from pathlib import Path

# Список запрещённых плейсхолдеров / маркеров
# Расширяем по мере необходимости
PATTERNS = [
    r"<updated>",
    r"<full content[^>]*>",
    r"current full file[^\n]*",
]

regexes = [re.compile(p) for p in PATTERNS]

# Получаем файлы, добавленные в индекс
files = (
    subprocess.check_output(["git", "diff", "--cached", "--name-only"])
    .decode()
    .splitlines()
)

bad_files: list[str] = []
for file_path in files:
    path = Path(file_path)
    # Игнорируем бинарные и удалённые файлы
    if not path.is_file() or path.suffix == ".pyc":
        continue
    if path.name == "forbid_placeholders.py":
        # допускаем наличие шаблонов внутри самого проверяющего скрипта
        continue
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        # Если не удалось прочитать – пропускаем
        continue
    if any(r.search(text) for r in regexes):
        bad_files.append(file_path)

if bad_files:
    sys.stderr.write(
        "В файлах обнаружены временные плейсхолдеры: " + ", ".join(bad_files) + "\n"
    )
    sys.exit(1)
