"""
Centralized logging with structured output.
All services log through here for unified incident correlation.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    timestamp: str
    service: str
    level: str
    message: str
    trace_id: Optional[str] = None
    error_code: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# In-memory log store for the simulation
_log_store: List[LogEntry] = []


def log(
    service: str,
    level: LogLevel,
    message: str,
    trace_id: Optional[str] = None,
    error_code: Optional[str] = None,
    **extra
) -> LogEntry:
    """Log a message and store it for later retrieval."""
    entry = LogEntry(
        timestamp=datetime.now().isoformat(),
        service=service,
        level=level.value,
        message=message,
        trace_id=trace_id,
        error_code=error_code,
        extra=extra
    )
    _log_store.append(entry)
    return entry


def get_logs(
    service: Optional[str] = None,
    level: Optional[LogLevel] = None,
    trace_id: Optional[str] = None,
    limit: int = 100
) -> List[LogEntry]:
    """Retrieve logs with optional filtering."""
    result = _log_store.copy()
    if service:
        result = [e for e in result if e.service == service]
    if level:
        result = [e for e in result if e.level == level.value]
    if trace_id:
        result = [e for e in result if e.trace_id == trace_id]
    return result[-limit:]


def get_error_logs(limit: int = 50) -> List[LogEntry]:
    """Get only ERROR and CRITICAL logs."""
    return [e for e in _log_store if e.level in ("ERROR", "CRITICAL")][-limit:]


def format_logs_for_display(logs: List[LogEntry]) -> str:
    """Format logs for human-readable display."""
    lines = []
    for entry in logs:
        prefix = "🔴" if entry.level == "ERROR" else "🟡" if entry.level == "WARN" else "⚪"
        line = f"{entry.timestamp} {prefix} [{entry.service}] {entry.message}"
        if entry.error_code:
            line += f" (code={entry.error_code})"
        if entry.trace_id:
            line += f" trace={entry.trace_id}"
        lines.append(line)
    return "\n".join(lines)


def clear_logs():
    """Clear all stored logs."""
    global _log_store
    _log_store = []


def export_logs_json() -> str:
    """Export all logs as JSON."""
    return json.dumps([asdict(e) for e in _log_store], indent=2)
