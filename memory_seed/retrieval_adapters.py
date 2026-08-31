"""Thin input adapters for Retrieval Specification preview and resolution.

The resolver deliberately accepts only inline specifications. These adapters
add exact local-profile input without duplicating the canonical resolver.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .retrieval import preview_retrieval_spec, resolve_retrieval_spec
from .retrieval_profiles import load_retrieval_profile


class RetrievalInputValidationError(ValueError):
    """A precise error at the inline-spec/profile adapter boundary."""


def _input_error(message: str) -> None:
    raise RetrievalInputValidationError(f"retrieval input: {message}")


def resolve_retrieval_input(
    *,
    spec: Mapping[str, Any] | None = None,
    profile: str | None = None,
    profile_version: int | None = None,
    overrides: Mapping[str, Any] | None = None,
    cwd: str | Path = ".",
) -> dict[str, Any]:
    """Return the inline spec selected by exactly one supported input mode."""
    has_spec = spec is not None
    has_profile_fields = (
        profile is not None or profile_version is not None or overrides is not None
    )
    if has_spec and has_profile_fields:
        _input_error("provide exactly one mode: inline spec or profile/profile_version with overrides")
    if not has_spec and profile is None and profile_version is None and overrides is None:
        _input_error("provide exactly one mode: inline spec or profile/profile_version with overrides")
    if has_spec:
        if not isinstance(spec, Mapping):
            _input_error("spec must be an inline JSON object")
        return dict(spec)

    if not isinstance(profile, str) or not profile.strip():
        _input_error("profile mode requires a non-empty profile")
    if type(profile_version) is not int or profile_version < 1:
        _input_error("profile mode requires a positive integer profile_version")
    if overrides is not None and not isinstance(overrides, Mapping):
        _input_error("overrides must be a JSON object")
    return load_retrieval_profile(profile, profile_version, cwd, overrides=overrides)


def preview_retrieval_input(**kwargs: Any) -> dict[str, Any]:
    """Preview one inline or profile-derived Retrieval Specification."""
    cwd = kwargs.pop("cwd", ".")
    return preview_retrieval_spec(resolve_retrieval_input(cwd=cwd, **kwargs), cwd)


def resolve_retrieval_input_pack(**kwargs: Any) -> dict[str, Any]:
    """Resolve one inline or profile-derived Retrieval Specification."""
    cwd = kwargs.pop("cwd", ".")
    return resolve_retrieval_spec(resolve_retrieval_input(cwd=cwd, **kwargs), cwd)
