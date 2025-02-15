# chat_server/logger.py
"""
Logger Module
============

This module implements the logging configuration for the chat server application.

Key Features:
- Hierarchical logging system with multiple severity levels
- Daily rotating log files with timestamps
- Console and file output handlers
- Customizable log formatting
- Automatic log directory creation
- Thread-safe logging operations

Functions:
    setup_logging(): Configures and returns the logger instance

Usage:
    logger = setup_logging()
    logger.info("Server started")
    logger.error("Connection failed")

Author: Chayan Kumawat
Date: January 2025
Version: 1.0
"""
import logging
import os
from datetime import datetime
import socket

def setup_logging():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger('ChatServer')
    logger.setLevel(logging.DEBUG)

    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    log_file = os.path.join(log_dir, f'chat_server_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger