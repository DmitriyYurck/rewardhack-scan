"""Configuration: env vars + optional config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class JudgeConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    input_per_1m: float = 3.0
    output_per_1m: float = 15.0


class ReplayConfig(BaseModel):
    timeout_s: int = 300
    test_command: str = "pytest -q"
    hidden_tests_path: str = ""
    network: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RHSCAN_", env_file=".env", extra="ignore")

    judges: JudgeConfig = Field(default_factory=JudgeConfig)
    replay: ReplayConfig = Field(default_factory=ReplayConfig)
    rules_path: str = "rules.yaml"
    judge_cache_dir: str = ".rhscan/judge_cache"
    rules_version: str = "v1"
    judge_prompt_version: str = "v1"


def load_settings(config_path: str | None = None) -> Settings:
    settings = Settings()
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {config_path}")
        data = yaml.safe_load(path.read_text()) or {}
        if "judge" in data:
            settings.judges = JudgeConfig(**data["judge"])
        if "replay" in data:
            settings.replay = ReplayConfig(**data["replay"])
        for key in ("rules_path", "judge_cache_dir", "rules_version", "judge_prompt_version"):
            if key in data:
                setattr(settings, key, data[key])
    return settings


def load_rule_defs(path: str) -> list[dict[str, object]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"rules file not found: {path} (set RHSCAN_RULES_PATH or pass --rules)"
        )
    data = yaml.safe_load(p.read_text()) or {}
    rules = data.get("rules", data) if isinstance(data, dict) else data
    if not isinstance(rules, list):
        raise ValueError(f"rules.yaml must contain a 'rules' list: {path}")
    return rules
