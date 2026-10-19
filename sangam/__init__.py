
import sys as _sys

# Windows consoles default to a legacy code page; print cards and charts' labels as UTF-8.
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
