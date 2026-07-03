"""
Purpose:
    Rich metadata builders for AR073 diagnostics.

Why is this in this project:
    AR073 exposes lean messages and structured JSON metadata for tools and users.

Inputs:
    FLI scores, traversal reach, wrapper paths, and entry-point classification.

Outputs:
    Measurements, dominant component, reach summary, suggestions, and caveats.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex, module_for_function
from .fli_models import (
    DominantComponent,
    FliMeasurements,
    FliScores,
    FliSuggestion,
    ReachSummary,
    WrapperPath,
    module_domain,
)
from .fli_scoring import (
    module_generic_layer,
    uses_shared_utils,
)

REACH_LIST_CAP = 20

COMPONENT_ORDER: tuple[str, ...] = (
    "wrapper_chain",
    "layer_crossing",
    "module_span",
    "remote_domain",
    "unresolved_edge",
)

COMPONENT_SHORT: dict[str, str] = {
    "wrapper_chain": "wrapper chain",
    "layer_crossing": "generic layers",
    "module_span": "modules",
    "remote_domain": "remote domains",
    "unresolved_edge": "unresolved calls",
}


def build_wrapper_path(
    entry: FunctionInfo,
    module: ModuleInfo,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> WrapperPath:
    from .fli_scoring import _next_wrapper, path_label

    labels: list[str] = [path_label(entry, module)]
    qualified: list[str] = [entry.qualified_name]
    current = entry
    visited = {entry.qualified_name}
    while len(labels) <= config.max_fli_depth:
        next_hop = _next_wrapper(current.qualified_name, visited, index)
        if next_hop is None:
            break
        next_function = index.callables_by_qualified_name.get(next_hop)
        next_module = module_for_function(next_function, index) if next_function else None
        if next_function is None or next_module is None:
            break
        labels.append(path_label(next_function, next_module))
        qualified.append(next_hop)
        visited.add(next_hop)
        current = next_function
    depth = max(len(labels) - 1, 0)
    return WrapperPath(labels=tuple(labels), qualified_names=tuple(qualified), depth=depth)


def _next_wrapper_qualified(
    name: str,
    visited: set[str],
    index: CallableIndex,
) -> str | None:
    from .fli_scoring import _next_wrapper

    return _next_wrapper(name, visited, index)


def compute_measurements(
    entry_module: ModuleInfo,
    reached_modules: set[str],
    wrapper_depth: int,
    unresolved: int,
    config: ArchbraceConfig,
) -> FliMeasurements:
    generic_layers = collect_generic_layers(reached_modules)
    remote_domains = collect_remote_domains(entry_module, reached_modules)
    foreign_modules = count_foreign_modules(entry_module, reached_modules)
    return FliMeasurements(
        module_count=len(reached_modules),
        wrapper_depth=wrapper_depth,
        generic_layer_count=len(generic_layers),
        remote_domain_count=len(remote_domains),
        foreign_module_count=foreign_modules,
        unresolved_call_count=unresolved,
        traversal_depth_limit=config.max_fli_depth,
    )


def collect_generic_layers(reached_modules: set[str]) -> tuple[str, ...]:
    layers = {
        layer
        for module in reached_modules
        if (layer := module_generic_layer(module)) is not None
    }
    return tuple(sorted(layers))


def collect_remote_domains(
    entry_module: ModuleInfo,
    reached_modules: set[str],
) -> tuple[str, ...]:
    entry_domain = module_domain(entry_module.module_name)
    domains = {
        module_domain(module_name)
        for module_name in reached_modules
        if module_name != entry_module.module_name
        and module_domain(module_name) != entry_domain
    }
    return tuple(sorted(domains))


def count_foreign_modules(entry_module: ModuleInfo, reached_modules: set[str]) -> int:
    entry_domain = module_domain(entry_module.module_name)
    return sum(
        1
        for module_name in reached_modules
        if module_name != entry_module.module_name
        and module_domain(module_name) != entry_domain
    )


def build_reach_summary(
    entry_module: ModuleInfo,
    reached_modules: set[str],
) -> ReachSummary:
    modules = sorted(reached_modules)
    remote_domains = collect_remote_domains(entry_module, reached_modules)
    truncated = len(modules) > REACH_LIST_CAP or len(remote_domains) > REACH_LIST_CAP
    return ReachSummary(
        modules=tuple(modules[:REACH_LIST_CAP]),
        generic_layers=collect_generic_layers(reached_modules),
        remote_domains=tuple(remote_domains[:REACH_LIST_CAP]),
        visited_shared_utils=any(
            uses_shared_utils(module_name) for module_name in reached_modules
        ),
        truncated=truncated,
    )


def select_dominant(scores: FliScores) -> DominantComponent:
    candidates = _score_candidates(scores)
    if not candidates:
        return DominantComponent(component="module_span", score=0, ties=())
    best_score = max(score for _, score in candidates)
    tied = [component for component, score in candidates if score == best_score]
    winner = min(tied, key=COMPONENT_ORDER.index)
    other_ties = tuple(sorted((c for c in tied if c != winner), key=COMPONENT_ORDER.index))
    return DominantComponent(component=winner, score=best_score, ties=other_ties)


def _score_candidates(scores: FliScores) -> list[tuple[str, int]]:
    return [
        (component, score)
        for component in COMPONENT_ORDER
        if (score := getattr(scores, component)) > 0
    ]


def build_suggestions(
    scores: FliScores,
    measurements: FliMeasurements,
    reach: ReachSummary,
    wrapper_path: WrapperPath,
) -> tuple[FliSuggestion, ...]:
    ranked = sorted(
        (
            (component, getattr(scores, component))
            for component in COMPONENT_ORDER
            if getattr(scores, component) > 0
        ),
        key=lambda item: (-item[1], COMPONENT_ORDER.index(item[0])),
    )
    suggestions: list[FliSuggestion] = []
    for priority, (component, _) in enumerate(ranked, start=1):
        text = _suggestion_text(component, measurements, reach, wrapper_path)
        if text:
            suggestions.append(FliSuggestion(component=component, priority=priority, text=text))
    if ranked:
        suggestions.append(
            FliSuggestion(
                component="general",
                priority=99,
                text=(
                    "This may be intentional if layers express real boundaries. "
                    "Consider raising max_fli only after reviewing reach."
                ),
            )
        )
    return tuple(suggestions)


def _suggestion_text(
    component: str,
    measurements: FliMeasurements,
    reach: ReachSummary,
    wrapper_path: WrapperPath,
) -> str:
    hop_label = "hop" if measurements.wrapper_depth == 1 else "hops"
    if component == "wrapper_chain":
        return (
            f"Collapse {measurements.wrapper_depth} pass-through {hop_label} in the "
            "wrapper path, or merge adjacent layers that do not express a real boundary."
        )
    if component == "layer_crossing":
        layers = ", ".join(reach.generic_layers)
        return f"Reduce hops through generic folders: {layers}."
    if component == "module_span":
        return (
            f"{measurements.module_count} modules are involved; consider a vertical "
            "slice in the same domain instead of horizontal layers."
        )
    if component == "remote_domain":
        domains = ", ".join(reach.remote_domains)
        return (
            f"Entry point reaches {measurements.remote_domain_count} other domain(s): "
            f"{domains}. Move shared logic closer or narrow entry scope."
        )
    if component == "unresolved_edge":
        call_label = "call" if measurements.unresolved_call_count == 1 else "calls"
        return (
            f"{measurements.unresolved_call_count} dynamic/unresolved {call_label} may "
            "hide additional reach; use explicit calls where possible."
        )
    return ""


def build_caveats(
    measurements: FliMeasurements,
    unresolved: int,
    config: ArchbraceConfig,
    reach: ReachSummary,
    wrapper_path: WrapperPath,
    *,
    depth_limited: bool,
) -> tuple[str, ...]:
    caveats: list[str] = []
    if unresolved > 0:
        call_label = "call" if unresolved == 1 else "calls"
        caveats.append(
            f"FLI may be underestimated due to {unresolved} unresolved local-looking "
            f"{call_label}."
        )
    if depth_limited:
        caveats.append(
            f"Traversal stopped at depth {config.max_fli_depth}; actual reach may be "
            "larger."
        )
    if measurements.module_count > wrapper_path.depth + 1:
        caveats.append(
            "Wrapper path shows pass-through hops only; see reach.modules for full spread."
        )
    if reach.truncated:
        caveats.append(
            f"Reach lists are capped at {REACH_LIST_CAP} entries; see truncated flag."
        )
    return tuple(caveats)


def format_lean_message(
    symbol: str,
    actual: int,
    limit: int,
    dominant: DominantComponent,
    measurements: FliMeasurements,
) -> str:
    summary = _dominant_summary(dominant, measurements)
    return f"{symbol}: flow locality {actual}/{limit} ({summary})"


def _dominant_summary(dominant: DominantComponent, measurements: FliMeasurements) -> str:
    parts = [_summary_fragment(dominant.component, measurements)]
    for tie in dominant.ties:
        parts.append(COMPONENT_SHORT[tie])
    if len(parts) > 1:
        return " + ".join(parts)
    return parts[0]


def _summary_fragment(component: str, measurements: FliMeasurements) -> str:
    if component == "wrapper_chain":
        return f"wrapper chain, depth {measurements.wrapper_depth}"
    if component == "layer_crossing":
        return f"{measurements.generic_layer_count} generic layers"
    if component == "module_span":
        return f"{measurements.module_count} modules"
    if component == "remote_domain":
        count = measurements.remote_domain_count
        label = "domain" if count == 1 else "domains"
        return f"{count} remote {label}"
    if component == "unresolved_edge":
        return "unresolved calls"
    return COMPONENT_SHORT.get(component, component)
