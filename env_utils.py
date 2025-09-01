#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # fallback if python-dotenv не установлен
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

def load_env() -> None:
    """
    Единая загрузка .env:
    1) Пытаемся вручную распарсить .env (поддержка простых многострочных значений через \n),
    2) Затем вызываем load_dotenv(override=True), чтобы не сломать совместимость.
    """
    for env_path in (Path(".env"), Path("../.env"), Path("../../.env")):
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                # не валимся на редких случаях форматирования
                pass
            break

    # Финальный проход (переменные из файла переопределяют окружение, если надо)
    try:
        load_dotenv(override=True)  # может быть no-op, если нет python-dotenv
    except Exception:
        pass
