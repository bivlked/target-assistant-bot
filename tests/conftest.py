import sys
from pathlib import Path

# Добавляем корень репозитория в sys.path, чтобы импорты 'utils', 'sheets' работали при запуске CI.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
