"""Tests for the optional real-LLM (Emergent universal key) wiring.

These do NOT call any external API. They only verify the config/mode logic:
- Default stays MOCK_LLM (deterministic, no key needed).
- Enabling EMERGENT_LLM_KEY with MOCK_LLM=false activates the real-LLM path.
- On any failure, the wrapper falls back to the deterministic mock engine.
"""
import importlib
import pytest

import backend.config as config_mod
import backend.agent.llm as llm_mod


def _reload(monkeypatch, mock_llm: str, emergent_key: str, gemini_key: str = ""):
    monkeypatch.setenv("MOCK_LLM", mock_llm)
    monkeypatch.setenv("EMERGENT_LLM_KEY", emergent_key)
    monkeypatch.setenv("GEMINI_API_KEY", gemini_key)
    importlib.reload(config_mod)
    importlib.reload(llm_mod)
    return llm_mod


def test_default_is_mock_mode(monkeypatch):
    mod = _reload(monkeypatch, mock_llm="true", emergent_key="")
    assert mod.llm_wrapper.mock_mode is True


def test_emergent_key_activates_real_mode(monkeypatch):
    mod = _reload(monkeypatch, mock_llm="false", emergent_key="sk-emergent-test")
    assert mod.llm_wrapper.mock_mode is False
    assert mod.llm_wrapper.emergent_key == "sk-emergent-test"


def test_real_mode_falls_back_to_mock_on_error(monkeypatch):
    mod = _reload(monkeypatch, mock_llm="false", emergent_key="sk-emergent-test")

    async def _boom(*args, **kwargs):
        raise RuntimeError("forced failure")

    mod.llm_wrapper._call_emergent_understand = _boom

    import asyncio
    proposal = asyncio.run(mod.llm_wrapper.analyze_complaint(
        "₹2,000 debited for my Zomato order TXN-1001, but the app says payment failed.",
        "CUST-4921",
    ))
    assert proposal.intent == "PAYMENT_COMPLAINT"
    assert proposal.extracted_txn_id == "TXN-1001"


def teardown_module():
    importlib.reload(config_mod)
    importlib.reload(llm_mod)
