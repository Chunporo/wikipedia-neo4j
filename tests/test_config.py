from __future__ import annotations

from pathlib import Path

import pytest

import src.config as config


def test_validate_runtime_settings_ok(tmp_path: Path, monkeypatch) -> None:
    key_file = tmp_path / "gemini.txt"
    key_file.write_text("key-1\n", encoding="utf-8")

    monkeypatch.setattr(config.settings, "neo4j_uri", "bolt://localhost:7687")
    monkeypatch.setattr(config.settings, "neo4j_username", "neo4j")
    monkeypatch.setattr(config.settings, "neo4j_password", "pw")
    monkeypatch.setattr(config.settings, "require_gemini_key_on_startup", True)
    monkeypatch.setattr(config.settings, "gemini_key_file", str(key_file))

    config.validate_runtime_settings()


def test_validate_runtime_settings_missing_gemini_file(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "require_gemini_key_on_startup", True)
    monkeypatch.setattr(config.settings, "gemini_key_file", "/tmp/not-exists-key-file")

    with pytest.raises(RuntimeError, match="Gemini key file not found"):
        config.validate_runtime_settings()


def test_load_gemini_api_keys_parses_file(tmp_path: Path, monkeypatch) -> None:
    key_file = tmp_path / "gemini.txt"
    key_file.write_text("#comment\n\nkey-1\nkey-2\n", encoding="utf-8")
    monkeypatch.setattr(config.settings, "gemini_key_file", str(key_file))

    assert config.load_gemini_api_keys() == ["key-1", "key-2"]


def test_load_gemini_api_keys_empty_file(tmp_path: Path, monkeypatch) -> None:
    key_file = tmp_path / "gemini.txt"
    key_file.write_text("\n#only-comment\n", encoding="utf-8")
    monkeypatch.setattr(config.settings, "gemini_key_file", str(key_file))

    with pytest.raises(RuntimeError, match="empty"):
        config.load_gemini_api_keys()


def test_resolve_orchestrator_model_prefers_new_field(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "orchestrator_model", "model-new")
    monkeypatch.setattr(config.settings, "gemini_model_text", "model-legacy")
    assert config.resolve_orchestrator_model() == "model-new"


def test_resolve_cypher_model_prefers_new_field(monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "cypher_model", "model-cypher")
    monkeypatch.setattr(config.settings, "gemini_model_text", "model-legacy")
    assert config.resolve_cypher_model() == "model-cypher"
