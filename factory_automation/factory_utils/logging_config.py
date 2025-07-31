"""Structured logging configuration for Factory Automation System"""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs in JSON format"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "pathname", "process", "processName",
                          "relativeCreated", "stack_info", "thread", "threadName",
                          "exc_info", "exc_text"]:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = False,
    colored: bool = True
) -> None:
    """
    Configure logging for the application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        structured: Use structured JSON logging
        colored: Use colored output for console (ignored if structured=True)
    """
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        if colored and sys.stdout.isatty():
            format_str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
            console_handler.setFormatter(ColoredFormatter(format_str))
        else:
            format_str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
            console_handler.setFormatter(logging.Formatter(format_str))
    
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
                )
            )
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True  # Remove existing handlers
    )
    
    # Set specific loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "level": level,
            "structured": structured,
            "colored": colored,
            "log_file": str(log_file) if log_file else None
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Example usage patterns
def log_with_context(logger: logging.Logger, message: str, **context):
    """
    Log a message with additional context
    
    Example:
        log_with_context(logger, "Order processed", 
                        order_id="ORD-123", 
                        customer="ABC Corp",
                        items=5)
    """
    logger.info(message, extra=context)


def log_error_with_context(logger: logging.Logger, message: str, error: Exception, **context):
    """
    Log an error with exception and additional context
    
    Example:
        try:
            process_order()
        except Exception as e:
            log_error_with_context(logger, "Failed to process order", e,
                                 order_id="ORD-123",
                                 customer="ABC Corp")
    """
    context["error_type"] = type(error).__name__
    context["error_message"] = str(error)
    logger.error(message, exc_info=error, extra=context)