import logging
from logging.handlers import RotatingFileHandler
import sys
import os

LOG_FILE = "logs/qa_tool.log"

def setup_logging():
    """Configura el logger principal de la aplicación."""
    os.makedirs("logs", exist_ok=True)
    
    logger = logging.getLogger("QA_Tool")
    logger.setLevel(logging.DEBUG)

    # Evitar duplicación de handlers si se llama varias veces
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formateador
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s')

    # Handler para el archivo (rolling)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=2
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler para la consola (para debug)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Muestra solo INFO y superior en consola
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging configurado.")
    return logger