"""The ingest address is a credential, so it has to behave like one."""

from __future__ import annotations

from app.api.v1.ingest import _org_for, ingest_token
from app.core.config import get_settings
from app.integrations.graph import PROVIDER_SCOPES, seal, unseal


def test_an_address_round_trips_to_its_own_workspace():
    token = ingest_token("org_abc123")
    assert _org_for(token) == "org_abc123"


def test_one_workspaces_address_never_opens_another():
    """The org id is in the URL, so tampering with it must not be enough."""
    token = ingest_token("org_abc123")
    forged = token.replace("org_abc123", "org_victim", 1)
    assert _org_for(forged) is None


def test_a_truncated_or_empty_address_is_refused():
    token = ingest_token("org_abc123")
    assert _org_for(token[:-1]) is None
    assert _org_for("") is None
    assert _org_for("org_abc123") is None


def test_rotating_the_app_secret_revokes_every_address():
    token = ingest_token("org_abc123")
    settings = get_settings()
    original = settings.SECRET_KEY
    try:
        settings.SECRET_KEY = "a-completely-different-secret"
        assert _org_for(token) is None
    finally:
        settings.SECRET_KEY = original
    assert _org_for(token) == "org_abc123"


def test_a_refresh_token_is_not_stored_in_the_clear():
    stored = seal("0.AXoA-refresh-token")
    assert "refresh-token" not in stored
    assert unseal(stored) == "0.AXoA-refresh-token"


def test_an_unreadable_token_asks_for_re_authorisation_rather_than_raising():
    assert unseal("not-a-fernet-token") is None
    assert unseal(None) is None


def test_no_connector_asks_for_write_access():
    """Margin reads solicitations. It has no business sending or deleting mail."""
    for provider, scopes in PROVIDER_SCOPES.items():
        assert "offline_access" in scopes, provider
        for scope in scopes:
            assert "Write" not in scope, f"{provider} asks for {scope}"
            assert "Send" not in scope, f"{provider} asks for {scope}"


def test_the_connector_card_advertises_the_scopes_consent_will_ask_for():
    """Two lists drift. The card reads from the connector itself."""
    from app.core.provisioning import default_scopes

    for provider, scopes in PROVIDER_SCOPES.items():
        assert default_scopes(provider) == [s for s in scopes if s != "offline_access"]
