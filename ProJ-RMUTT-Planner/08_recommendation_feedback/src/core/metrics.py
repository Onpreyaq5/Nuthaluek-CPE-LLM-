from prometheus_client import Counter, Histogram

EVENTS_ACCEPTED = Counter(
    "rmutt_feedback_events_accepted_total", "Events accepted by module 08", ["service", "action", "status"]
)
EVENTS_DUPLICATE = Counter("rmutt_feedback_events_duplicate_total", "Duplicate events ignored")
FEEDBACK_ACCEPTED = Counter(
    "rmutt_feedback_submissions_total", "Feedback submissions", ["target_type", "rating"]
)
ALERTS_CREATED = Counter("rmutt_feedback_alerts_created_total", "Alerts created", ["code", "channel"])
INGEST_LATENCY = Histogram("rmutt_feedback_ingest_seconds", "Event ingestion latency")
