import types

from utils import period_parser


def test_llm_days_handles_empty_choices(monkeypatch):
    """_llm_days() must return None (not raise) when response.choices is empty."""

    # Stub for OpenAI chat completion response with empty choices
    dummy_response = types.SimpleNamespace(choices=[])

    def fake_create(*args, **kwargs):  # noqa: D401 – simple stub
        return dummy_response

    dummy_client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=fake_create)
        )
    )

    # Patch internal client factory to return our stub
    monkeypatch.setattr(
        period_parser, "_get_client", lambda: dummy_client, raising=True
    )

    assert period_parser._llm_days("непонятный срок") is None
