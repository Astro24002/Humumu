"""JournalOut accepts v1 fields with defaults for backward compatibility."""

from datetime import datetime, timezone

from app.schemas.journal import JournalOut


def test_journal_out_accepts_v1_fields():
    j = JournalOut.model_validate(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Nature",
            "slug": "nature",
            "source_type": "rss",
            "source_url": "https://example.com/n.rss",
            "description": "",
            "fetch_interval": 1800,
            "is_active": True,
            "created_by": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "content_type": "journal",
            "directory_status": "public",
            "homepage_url": "https://nature.com",
            "consecutive_failures": 0,
        }
    )
    assert j.content_type == "journal"
    assert j.directory_status == "public"
    assert j.homepage_url == "https://nature.com"


def test_journal_out_defaults_when_fields_omitted():
    j = JournalOut.model_validate(
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Nature",
            "slug": "nature",
            "source_type": "rss",
            "source_url": "https://example.com/n.rss",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )
    assert j.content_type == "journal"
    assert j.directory_status == "public"
    assert j.homepage_url == ""
    assert j.consecutive_failures == 0
