import pytest
from llm.async_client import AsyncLLMClient


def test_async_extract_plan():
    json_text = 'Some intro [\n  {"day": "01.05.25", "task": "T"}\n] epilogue'
    assert AsyncLLMClient._extract_plan(json_text)[0]["task"] == "T"
