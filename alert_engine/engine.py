"""
Alert Engine
Detects anomalies and auto-creates incident tickets.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.logger import get_error_logs, LogEntry


@dataclass
class Alert:
    id: str
    severity: str  # SEV-1, SEV-2, SEV-3
    service: str
    title: str
    symptoms: List[str]
    triggered_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


@dataclass
class Ticket:
    id: str
    severity: str
    environment: str
    summary: str
    symptoms: List[str]
    first_detected: str
    status: str = "open"  # open, investigating, mitigating, resolved
    assigned_to: Optional[str] = None
    alerts: List[Alert] = field(default_factory=list)


class AlertEngine:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.tickets: List[Ticket] = []
        self.thresholds = {
            "error_count_sev2": 5,
            "error_count_sev1": 10,
            "lookback_seconds": 300
        }

    def check_for_alerts(self) -> List[Alert]:
        """Analyze recent logs and generate alerts if thresholds breached."""
        error_logs = get_error_logs(limit=100)
        new_alerts = []

        # Group errors by service
        by_service: Dict[str, List[LogEntry]] = {}
        for log in error_logs:
            if log.service not in by_service:
                by_service[log.service] = []
            by_service[log.service].append(log)

        for service, logs in by_service.items():
            count = len(logs)
            if count >= self.thresholds["error_count_sev1"]:
                severity = "SEV-1"
            elif count >= self.thresholds["error_count_sev2"]:
                severity = "SEV-2"
            else:
                continue

            # Extract symptoms from error messages
            symptoms = list(set(log.message for log in logs[:5]))

            alert = Alert(
                id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                severity=severity,
                service=service,
                title=f"High error rate in {service} service",
                symptoms=symptoms
            )
            new_alerts.append(alert)
            self.alerts.append(alert)

        return new_alerts

    def create_ticket_from_alerts(self, alerts: List[Alert]) -> Optional[Ticket]:
        """Auto-create an incident ticket from alerts."""
        if not alerts:
            return None

        # Determine overall severity (worst case)
        severity = "SEV-3"
        for alert in alerts:
            if alert.severity == "SEV-1":
                severity = "SEV-1"
                break
            elif alert.severity == "SEV-2":
                severity = "SEV-2"

        # Aggregate symptoms
        all_symptoms = []
        services = set()
        for alert in alerts:
            all_symptoms.extend(alert.symptoms)
            services.add(alert.service)

        ticket = Ticket(
            id=f"INC-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}",
            severity=severity,
            environment="production",
            summary=f"Checkout failures affecting {', '.join(services)}",
            symptoms=list(set(all_symptoms))[:5],
            first_detected=datetime.now().isoformat(),
            alerts=alerts
        )
        self.tickets.append(ticket)
        return ticket

    def trigger_demo_incident(self, failure_type: str = "billing_currency_missing") -> Ticket:
        """Trigger a demo incident for simulation purposes."""
        # Create a realistic alert based on failure type
        symptom_map = {
            "billing_currency_missing": [
                "POST /api/create-order 400 - validation failed",
                "Missing required field: currency",
                "Stripe: PaymentIntent requires currency"
            ],
            "ordering_inventory_lock": [
                "Failed to acquire inventory lock",
                "ORDER_423: Lock timeout",
                "High contention on SKU inventory"
            ],
            "frontend_stale_contract": [
                "Frontend API contract mismatch",
                "400 errors on checkout",
                "Schema validation failed"
            ]
        }

        symptoms = symptom_map.get(failure_type, ["Unknown error"])
        service = failure_type.split("_")[0]

        alert = Alert(
            id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
            severity="SEV-2",
            service=service,
            title=f"Production incident in {service}",
            symptoms=symptoms
        )
        self.alerts.append(alert)

        ticket = Ticket(
            id=f"INC-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}",
            severity="SEV-2",
            environment="production",
            summary="Users unable to complete checkout",
            symptoms=symptoms,
            first_detected=datetime.now().isoformat(),
            alerts=[alert]
        )
        self.tickets.append(ticket)
        return ticket


# Singleton
_alert_engine: Optional[AlertEngine] = None


def get_alert_engine() -> AlertEngine:
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = AlertEngine()
    return _alert_engine
