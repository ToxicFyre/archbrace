"""
Purpose:
    Shared FLI models and constants for AR073.

Why is this in this project:
    AR073 scoring and traversal share typed findings and layer constants.

Inputs:
    None at import time.

Outputs:
    FLI dataclasses and shared constant sets.

Side effects:
    None.

Failure behavior:
    Pure data definitions; construction raises ``TypeError`` only on misuse.
"""

from __future__ import annotations

from dataclasses import dataclass

GENERIC_LAYERS = frozenset(
    {
        "handlers",
        "services",
        "managers",
        "processors",
        "repositories",
        "adapters",
        "interfaces",
        "factories",
        "strategies",
        "utils",
        "helpers",
        "common",
    }
)
SHARED_DOMAIN_TOKENS = frozenset({"shared", "common", "utils"})
ENTRY_POINT_NAMES = frozenset(
    {
        "main",
        "run",
        "execute",
        "create",
        "update",
        "delete",
        "import",
        "export",
    }
)
ROUTE_DECORATORS = (
    "click.command",
    "typer.command",
    "app.route",
    "router.get",
    "router.post",
    "router.put",
    "router.delete",
    "router.patch",
    "celery.task",
)


def module_domain(module_name: str) -> str:
    for token in module_name.split("."):
        if token not in GENERIC_LAYERS:
            return token
    return module_name.split(".")[0]


@dataclass(frozen=True)
class CallEdge:
    """A conservative call-graph edge collected during FLI traversal."""

    caller: str
    callee: str
    confidence: str
    same_file: bool
    same_package: bool
    call_kind: str


@dataclass(frozen=True)
class FliScores:
    """Component scores that sum to the Flow Locality Index."""

    module_span: int
    layer_crossing: int
    wrapper_chain: int
    remote_domain: int
    unresolved_edge: int

    @property
    def total(self) -> int:
        return (
            self.module_span
            + self.layer_crossing
            + self.wrapper_chain
            + self.remote_domain
            + self.unresolved_edge
        )


@dataclass(frozen=True)
class FlowLocalityFinding:
    """An entry point whose FLI exceeds the configured limit."""

    entry: str
    fli: int
    scores: FliScores
    path: tuple[str, ...]
    unresolved_edges: int
    reasons: tuple[str, ...]
