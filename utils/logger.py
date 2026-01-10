import logging
import json
import time
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Merge extra fields if provided
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Strict white-list for safety (never log content or embedding)
            safe_keys = {"user_id", "event", "duration_ms", "status", "model", "cache_hit", "top_k", "memories_count"}
            for k, v in record.extra_data.items():
                if k in safe_keys:
                    log_data[k] = v

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logger(name: str = "second_brain"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    # Prevent propagation to root logger to avoid double logging
    logger.propagate = False
    return logger

# Common logger instance
logger = setup_logger()

def log_event(level: int, event: str, message: str, **kwargs):
    """
    Helper to log structured events with extra data.
    """
    extra = {"extra_data": {"event": event, **kwargs}}
    logger.log(level, message, extra=extra)
