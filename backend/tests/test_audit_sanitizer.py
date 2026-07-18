from backend.services.audit import REDACTED, sanitize_metadata


def test_audit_sanitizer_redacts_sensitive_nested_metadata() -> None:
    sanitized = sanitize_metadata(
        {
            "candidate_id": 4,
            "authorization": "Bearer should-not-appear",
            "nested": {
                "database_url": "postgresql://not-safe-to-store",
                "safe": ["value", {"api_key": "not-safe"}],
            },
        }
    )

    assert sanitized == {
        "candidate_id": 4,
        "authorization": REDACTED,
        "nested": {
            "database_url": REDACTED,
            "safe": ["value", {"api_key": REDACTED}],
        },
    }
