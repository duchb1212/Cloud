from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    allowed_origins: tuple[str, ...]
    contracts_dir: Path
    max_body_bytes: int
    log_level: str
    data_mode: str = "real"
    persistence_enabled: bool = False
    local_auth_enabled: bool = False
    ocr_enabled: bool = False
    ocr_service_url: str = "http://127.0.0.1:8080"
    ocr_chinese_service_url: str | None = None

    @classmethod
    def from_environment(cls, environment=None):
        values = os.environ if environment is None else environment

        def integer(name, default, minimum, maximum):
            try:
                result = int(values.get(name, str(default)))
            except (TypeError, ValueError):
                raise ConfigurationError(f"{name} must be an integer") from None
            if not minimum <= result <= maximum:
                raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
            return result

        stage = values.get("APP_ENV", "local")
        if stage not in {"local", "test", "production"}:
            raise ConfigurationError("APP_ENV must be one of: local, test, production")
        host = values.get("APP_HOST", "127.0.0.1")
        if stage == "production":
            if host not in {"0.0.0.0", "127.0.0.1", "localhost", "::1"}:
                raise ConfigurationError("APP_HOST must be 0.0.0.0 or a loopback address")
        elif host not in {"127.0.0.1", "localhost", "::1"}:
            raise ConfigurationError("Local foundation must bind to a loopback host")
        if values.get("DATA_MODE", "real") != "real":
            raise ConfigurationError("DATA_MODE must be real; use the separate CT-04 server for mock mode")
        origins = tuple(filter(None, (item.strip() for item in values.get(
            "ALLOWED_ORIGINS", "http://localhost:8443,http://127.0.0.1:8443",
        ).split(","))))
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or "*" in origin:
                raise ConfigurationError("ALLOWED_ORIGINS must contain exact HTTP(S) origins without paths or credentials")
            try:
                parsed.port
            except ValueError:
                raise ConfigurationError("ALLOWED_ORIGINS contains an invalid port") from None
        contracts = Path(values.get("CONTRACTS_DIR", Path(__file__).resolve().parents[3] / "contracts")).expanduser().resolve()
        if not (contracts / "contract-version.json").is_file():
            raise ConfigurationError("CONTRACTS_DIR must reference a complete contract checkout")
        level = values.get("LOG_LEVEL", "INFO").upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("LOG_LEVEL is invalid")
        enabled = values.get("PERSISTENCE_ENABLED", "0")
        if enabled not in {"0", "1"}:
            raise ConfigurationError("PERSISTENCE_ENABLED must be 0 or 1")
        local_auth = values.get("LOCAL_AUTH_ENABLED", "0")
        if local_auth not in {"0", "1"}:
            raise ConfigurationError("LOCAL_AUTH_ENABLED must be 0 or 1")
        if local_auth == "1" and enabled != "1":
            raise ConfigurationError("Local authentication requires persistence")
        ocr_enabled = values.get("OCR_ENABLED", "0")
        if ocr_enabled not in {"0", "1"} or (ocr_enabled == "1" and local_auth != "1"):
            raise ConfigurationError("OCR_ENABLED must be 0/1 and requires local integration")
        def provider_url(name, default):
            value = values.get(name, default)
            if not value:
                return None
            parsed = urlsplit(value)
            try:
                if stage == "production":
                    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                        raise ValueError()
                else:
                    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                        raise ValueError()
            except ValueError:
                raise ConfigurationError(name + " must be a valid HTTP(S) origin without credentials") from None
            return value
        ocr_url = provider_url("OCR_SERVICE_URL", "http://127.0.0.1:8080")
        if not ocr_url:
            raise ConfigurationError("OCR_SERVICE_URL must not be empty")
        chinese_url = provider_url("OCR_CHINESE_SERVICE_URL", None)
        return cls(stage, host, integer("APP_PORT", 8081, 1, 65535), origins, contracts,
                   integer("APP_MAX_BODY_BYTES", 1048576, 1, 1048576), level, persistence_enabled=enabled == "1", local_auth_enabled=local_auth == "1",
                   ocr_enabled=ocr_enabled == "1", ocr_service_url=ocr_url, ocr_chinese_service_url=chinese_url)
