from pathlib import Path

import importlib

import pytest


def _fresh_google_cfg(monkeypatch):
    """Возвращает новый экземпляр GoogleConfig после очистки модуля config."""
    # Удаляем модуль из sys.modules, чтобы при повторном импорте исполнился код заново
    import sys

    sys.modules.pop("config", None)
    cfg = importlib.import_module("config")
    return cfg.GoogleConfig()


def test_credentials_path_uses_fallback(tmp_path, monkeypatch):
    """Если env-путь не существует, но есть fallback в BASE_DIR, используется он."""

    # Создаём временный каталог и "google_credentials.json" внутри
    base_dir = tmp_path / "proj"
    base_dir.mkdir()
    fallback_file = base_dir / "google_credentials.json"
    fallback_file.write_text("{}")

    # Переменные окружения
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(base_dir / "nonexistent.json"))

    # Переимпортируем config и берём новый экземпляр GoogleConfig
    google_cfg = _fresh_google_cfg(monkeypatch)
    import config as cfg_mod  # type: ignore

    # Подменяем BASE_DIR после импорта
    monkeypatch.setattr(cfg_mod, "BASE_DIR", base_dir, raising=True)

    # Проверяем
    path = Path(google_cfg.credentials_path)
    assert path == fallback_file


def test_credentials_path_raises_when_missing(tmp_path, monkeypatch):
    """Если ни env-путь, ни fallback не существуют, выбрасывается FileNotFoundError."""

    base_dir = tmp_path / "proj2"
    base_dir.mkdir()

    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(base_dir / "absent.json"))

    # Переимпортируем config и подменяем BASE_DIR
    google_cfg = _fresh_google_cfg(monkeypatch)
    import config as cfg_mod  # type: ignore

    monkeypatch.setattr(cfg_mod, "BASE_DIR", base_dir, raising=True)

    with pytest.raises(FileNotFoundError):
        _ = google_cfg.credentials_path
