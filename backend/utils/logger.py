"""
Logging utility for the agent.
"""

import logging
import sys
from typing import Optional
from pathlib import Path


class Logger:
    """Centralized logging configuration."""
    
    _instance: Optional[logging.Logger] = None
    
    @staticmethod
    def get_logger(name: str = "agent") -> logging.Logger:
        """
        Get or create a logger instance.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        if Logger._instance is not None:
            return logging.getLogger(name)
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(log_dir / "agent.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        Logger._instance = logger
        return logger


def get_logger(name: str = "agent") -> logging.Logger:
    """Convenience function to get a logger."""
    return Logger.get_logger(name)
