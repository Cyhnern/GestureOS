"""
Merkezi logging kurulumu.
Diğer modüller: `from utils.logger import get_logger` ile kullanır.
"""
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        # Zaten kurulmuşsa tekrar handler eklemeyelim (duplicate log önler)
        return logger

    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Konsola yaz
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Dosyaya yaz
    try:
        file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass  # Dosya yazılamıyorsa sessizce devam et (örn. yetki sorunu)

    return logger
