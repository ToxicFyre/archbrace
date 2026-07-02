"""
Purpose:
    The ``archbrace`` command-line interface: the ``check`` command and the
    ``--version`` option, wired to configuration, analysis, rules, and reporting
    (spec Section 4).

Why is this in this project:
    The user-facing entry point that composes configuration, analysis, rules,
    and reporting into a single command developers and CI actually run.

Inputs:
    Command-line arguments and repository configuration.

Outputs:
    Text or JSON diagnostics on stdout, error messages on stderr, and the
    documented process exit code.

Side effects:
    Reads source and configuration files; writes to stdout/stderr; exits the
    process.

Failure behavior:
    Configuration, parsing, and rule-execution failures are reported on stderr
    and produce exit code 2 (spec Sections 4.5, 9.4).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import cast

import click

from . import __version__
from .config import ArchbraceConfig, load_config
from .errors import ArchbraceError
from .models import Diagnostic, Severity
from .project import build_project_index
from .reporting.json import render_json
from .reporting.text import render_text
from .rules import get_all_rules, run_rules

_EXIT_OK = 0
_EXIT_DIAGNOSTICS = 1
_EXIT_ERROR = 2


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    version=__version__,
    prog_name="archbrace",
    message="%(prog)s %(version)s",
)
def cli() -> None:
    """Archbrace - a deterministic architectural linter for Python."""


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path())
@click.option(
    "--config",
    "config_path",
    type=click.Path(),
    default=None,
    help="Configuration file; defaults to the nearest pyproject.toml.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default=None,
    help="Output format; defaults to the configured format (text).",
)
@click.option("--select", default=None, help="Run only selected rule codes or prefixes.")
@click.option("--ignore", default=None, help="Suppress selected rule codes or prefixes.")
@click.option(
    "--fail-on",
    "fail_on",
    type=click.Choice(["error", "warning"]),
    default=None,
    help="Minimum severity that produces exit code 1.",
)
@click.option("--show-source", is_flag=True, default=False, help="Show the source line.")
@click.option("--no-color", is_flag=True, default=False, help="Disable colored output.")
def check(
    paths: tuple[str, ...],
    config_path: str | None,
    output_format: str | None,
    select: str | None,
    ignore: str | None,
    fail_on: str | None,
    show_source: bool,
    no_color: bool,
) -> None:
    """Scan one or more PATHS for architectural violations."""
    target_paths = [Path(item) for item in paths] or [Path(".")]
    try:
        config = _resolve_config(config_path, select, ignore, output_format, fail_on)
        project = build_project_index(target_paths, config)
        diagnostics = run_rules(get_all_rules(), project, config)
    except ArchbraceError as exc:
        click.echo(f"archbrace: error: {exc}", err=True)
        sys.exit(_EXIT_ERROR)

    base = Path.cwd()
    if config.format == "json":
        output = render_json(
            diagnostics, base=base, files_scanned=len(project.modules)
        )
    else:
        use_color = (not no_color) and sys.stdout.isatty()
        output = render_text(
            diagnostics, base=base, show_source=show_source, color=use_color
        )

    click.echo(output.rstrip("\n"))
    sys.exit(
        _EXIT_DIAGNOSTICS if _should_fail(diagnostics, config.fail_on) else _EXIT_OK
    )


def _resolve_config(
    config_path: str | None,
    select: str | None,
    ignore: str | None,
    output_format: str | None,
    fail_on: str | None,
) -> ArchbraceConfig:
    config = load_config(
        Path(config_path) if config_path else None,
        start=Path.cwd(),
    )
    config = config.merge_cli(select=_split(select), ignore=_split(ignore))
    if output_format is not None:
        config = replace(config, format=output_format)
    if fail_on is not None:
        config = replace(config, fail_on=cast(Severity, fail_on))
    return config


def _split(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _should_fail(diagnostics: list[Diagnostic], fail_on: Severity) -> bool:
    if fail_on == "warning":
        return any(d.severity in ("error", "warning") for d in diagnostics)
    return any(d.severity == "error" for d in diagnostics)


def main() -> None:
    """Console-script entry point for the ``archbrace`` command."""
    cli()


if __name__ == "__main__":
    main()
