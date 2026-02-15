import importlib
import pkgutil
from typing import Any


def collect_command_meta(package: str) -> list[dict[str, Any]]:
    metas: list[dict[str, Any]] = []
    try:
        pkg = importlib.import_module(package)
        for m in pkgutil.iter_modules(pkg.__path__, package + "."):
            mod = importlib.import_module(m.name)
            meta = getattr(mod, "COMMAND_META", None)
            if isinstance(meta, dict):
                metas.append(meta)
    except Exception:
        pass
    return metas


def collect_command_names(package: str) -> list[str]:
    metas = collect_command_meta(package)
    names: list[str] = []
    for meta in metas:
        name = meta.get("name")
        if not name:
            continue
        names.append(str(name))
    names.sort()
    return names

