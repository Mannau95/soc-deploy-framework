"""
Système de journalisation
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


class LoggerManager:
    """Gestionnaire de logs centralisé"""

    def __init__(self, log_dir: Path, log_level: str = "INFO"):
        self.log_dir = log_dir
        self.log_level = log_level
        self.loggers = {}

    def get_logger(self, name: str) -> logging.Logger:
        """Récupère ou crée un logger"""
        if name not in self.loggers:
            self.loggers[name] = self._create_logger(name)
        return self.loggers[name]

    def _create_logger(self, name: str) -> logging.Logger:
        """Crée un logger avec handlers fichier et console"""
        logger = logging.getLogger(f"soc_deploy.{name}")
        logger.setLevel(self.log_level)

        # Éviter les doublons
        if logger.handlers:
            return logger

        # Format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Handler fichier
        self.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            self.log_dir / f"{name}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Handler console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger
