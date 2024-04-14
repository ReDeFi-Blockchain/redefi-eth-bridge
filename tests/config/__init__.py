try:
    from .local import Config
except ImportError:
    from .base import BaseConfig as Config
