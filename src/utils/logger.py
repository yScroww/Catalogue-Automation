import logging
import os
from typing import Optional
from datetime import datetime

def get_logger(name: str = "catalog_builder", log_level: Optional[int] = None) -> logging.Logger:
    """Configura e retorna um logger com handlers para console e arquivo."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    # Nível padrão
    logger.setLevel(logging.DEBUG)
    
    # Formatação
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler para console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO if log_level is None else log_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    
    # Handler para arquivo (com data no nome)
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    
    logger.info(f"Logger configurado. Arquivo de log: {log_file}")
    return logger