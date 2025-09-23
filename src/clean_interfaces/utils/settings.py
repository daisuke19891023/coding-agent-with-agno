"""Application settings management using Pydantic Settings.

This module provides centralized configuration management for the application,
with support for environment variables and validation.
"""

from enum import Enum
from typing import Any, ClassVar, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OTelExportMode(str, Enum):
    """OpenTelemetry log export modes."""

    FILE = "file"
    OTLP = "otlp"
    BOTH = "both"


class LoggingSettings(BaseSettings):
    """Logging configuration settings.

    All settings can be configured via environment variables.
    """

    instance: ClassVar[Any] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Basic logging settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    log_format: Literal["json", "console", "plain"] = Field(
        default="json",
        description="Log output format",
    )

    log_file_path: str | None = Field(
        default=None,
        description="Path to log file for local file logging",
    )

    # OpenTelemetry settings
    otel_logs_export_mode: OTelExportMode = Field(
        default=OTelExportMode.FILE,
        description="OpenTelemetry logs export mode: file, otlp, or both",
    )

    otel_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry collector endpoint",
    )

    otel_service_name: str = Field(
        default="python-app",
        description="Service name for OpenTelemetry",
    )

    otel_export_timeout: int = Field(
        default=30000,
        description="OpenTelemetry export timeout in milliseconds",
        ge=1,
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            msg = f"Invalid log level: {v}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format value."""
        valid_formats = {"json", "console", "plain"}
        if v.lower() not in valid_formats:
            msg = f"Invalid log format: {v}. Must be one of {valid_formats}"
            raise ValueError(msg)
        return v.lower()

    @field_validator("otel_export_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            msg = "Timeout must be a positive integer"
            raise ValueError(msg)
        return v

    @property
    def otel_export_enabled(self) -> bool:
        """Check if OpenTelemetry export is enabled."""
        return self.otel_logs_export_mode in (OTelExportMode.OTLP, OTelExportMode.BOTH)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump model including computed properties."""
        data = super().model_dump(**kwargs)
        data["otel_export_enabled"] = self.otel_export_enabled
        return data


class InterfaceSettings(BaseSettings):
    """Interface configuration settings."""

    instance: ClassVar[Any] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    interface_type: str = Field(
        default="cli",
        description="Type of interface to use (cli, restapi)",
    )

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, v: str) -> str:
        """Validate interface type value."""
        from clean_interfaces.types import InterfaceType

        try:
            # Validate that it's a valid interface type
            InterfaceType(v.lower())
            return v.lower()
        except ValueError:
            valid_types = [t.value for t in InterfaceType]
            msg = f"Invalid interface type: {v}. Must be one of {valid_types}"
            raise ValueError(msg) from None

    @property
    def interface_type_enum(self) -> Any:
        """Get interface type as enum."""
        from clean_interfaces.types import InterfaceType

        return InterfaceType(self.interface_type)


class AgentSettings(BaseSettings):
    """Configuration settings for agent integrations."""

    instance: ClassVar[Any] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="AGNO_",
    )

    # Provider selection
    provider: Literal["openai", "azure_openai", "anthropic", "gemini"] = Field(
        default="openai",
        description=(
            "LLM provider to use for agent models: openai, azure_openai, anthropic, gemini."
        ),
    )

    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        description="OpenAI API key used by agno agents.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model identifier for agno agents.",
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias="OPENAI_BASE_URL",
        description="Optional custom base URL for OpenAI-compatible endpoints.",
    )

    # Azure OpenAI
    azure_openai_api_key: str | None = Field(
        default=None,
        validation_alias="AZURE_OPENAI_API_KEY",
        description="Azure OpenAI API key (uses 'api-key' header).",
    )
    azure_openai_endpoint: str | None = Field(
        default=None,
        validation_alias="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint, e.g. https://<name>.openai.azure.com/",
    )
    azure_openai_api_version: str | None = Field(
        default=None,
        validation_alias="AZURE_OPENAI_API_VERSION",
        description="Azure OpenAI API version, e.g. 2024-05-01-preview.",
    )
    azure_openai_deployment: str | None = Field(
        default=None,
        validation_alias="AZURE_OPENAI_DEPLOYMENT",
        description="Azure OpenAI deployment name (used instead of model id).",
    )

    # Anthropic
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
        description="Anthropic API key.",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Default Anthropic model identifier.",
    )
    anthropic_base_url: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_BASE_URL",
        description="Optional Anthropic base URL.",
    )

    # Google Gemini
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
        description="Google Gemini API key.",
    )
    gemini_model: str = Field(
        default="gemini-1.5-pro",
        description="Default Google Gemini model identifier.",
    )
    gemini_base_url: str | None = Field(
        default=None,
        validation_alias="GEMINI_BASE_URL",
        description="Optional Gemini base URL.",
    )
    agent_name: str = Field(
        default="Clean Interfaces Agent",
        description="Display name assigned to agno agents.",
    )


class MCPSettings(BaseSettings):
    """Configuration for MCP integrations used by agents."""

    instance: ClassVar[Any] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="MCP_",
    )

    lsp_walker_provider: Literal["serena"] = Field(
        default="serena",
        description="Identifier for the LSP walker provider to use.",
    )
    lsp_walker_command: str = Field(
        default=(
            "uvx --from git+https://github.com/oraios/serena serena start-mcp-server"
        ),
        description="Command used to launch the default LSP walker MCP server.",
    )
    lsp_walker_context: str | None = Field(
        default="ide-assistant",
        description="Optional context passed to the MCP server.",
    )
    lsp_walker_transport: Literal["stdio", "sse", "streamable-http"] = Field(
        default="stdio",
        description="Transport protocol used to connect to the MCP server.",
    )
    lsp_walker_timeout_seconds: int = Field(
        default=60,
        description="Read timeout applied when communicating with the MCP server.",
        ge=1,
    )
    lsp_walker_url: str | None = Field(
        default=None,
        description="Optional URL for transports that require explicit endpoints.",
    )


def get_settings() -> LoggingSettings:
    """Get the global settings instance.

    Returns:
        LoggingSettings: The settings instance

    """
    if LoggingSettings.instance is None:
        LoggingSettings.instance = LoggingSettings()
    return LoggingSettings.instance


def reset_settings() -> None:
    """Reset the global settings instance.

    This is mainly useful for testing.
    """
    LoggingSettings.instance = None


def get_interface_settings() -> InterfaceSettings:
    """Get the global interface settings instance.

    Returns:
        InterfaceSettings: The interface settings instance

    """
    if InterfaceSettings.instance is None:
        InterfaceSettings.instance = InterfaceSettings()
    return InterfaceSettings.instance


def reset_interface_settings() -> None:
    """Reset the global interface settings instance.

    This is mainly useful for testing.
    """
    InterfaceSettings.instance = None


def get_agent_settings() -> AgentSettings:
    """Get the global agent settings instance."""
    if AgentSettings.instance is None:
        AgentSettings.instance = AgentSettings()
    return AgentSettings.instance


def reset_agent_settings() -> None:
    """Reset the global agent settings instance."""
    AgentSettings.instance = None


def get_mcp_settings() -> MCPSettings:
    """Get the global MCP settings instance."""
    if MCPSettings.instance is None:
        MCPSettings.instance = MCPSettings()
    return MCPSettings.instance


def reset_mcp_settings() -> None:
    """Reset the global MCP settings instance."""
    MCPSettings.instance = None
