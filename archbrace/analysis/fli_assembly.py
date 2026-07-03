"""
Purpose:
    Assemble rich FLI findings from traversal and scoring results.

Why is this in this project:
    Keeps ``analyze_entry_point`` small while wiring metadata builders.

Inputs:
    Entry functions, indexes, and configuration.

Outputs:
    Populated ``FlowLocalityFinding`` objects.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed indexes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import ArchbraceConfig
from ..models import FunctionInfo, ModuleInfo
from .call_index import CallableIndex
from .fli_entry import classify_entry_point
from .fli_metadata import (
    build_caveats,
    build_reach_summary,
    build_suggestions,
    build_wrapper_path,
    compute_measurements,
    select_dominant,
)
from .fli_models import (
    DominantComponent,
    EntryPointInfo,
    FliMeasurements,
    FliScores,
    FliSuggestion,
    FlowLocalityFinding,
    ReachSummary,
    WrapperPath,
)
from .fli_scoring import compute_scores, format_reasons, longest_wrapper_chain_depth


@dataclass(frozen=True)
class _FindingParts:
    scores: FliScores
    wrapper_path: WrapperPath
    measurements: FliMeasurements
    dominant: DominantComponent
    entry_point: EntryPointInfo
    reach: ReachSummary
    suggestions: tuple[FliSuggestion, ...]
    caveats: tuple[str, ...]


def build_flow_locality_finding(
    function: FunctionInfo,
    module: ModuleInfo,
    reached: set[str],
    unresolved: int,
    depth_limited: bool,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> FlowLocalityFinding:
    parts = _finding_parts(function, module, reached, unresolved, depth_limited, index, config)
    return FlowLocalityFinding(
        entry=function.qualified_name,
        fli=parts.scores.total,
        scores=parts.scores,
        path=parts.wrapper_path.labels,
        unresolved_edges=unresolved,
        reasons=format_reasons(parts.scores, unresolved),
        reached_modules=tuple(sorted(reached)),
        measurements=parts.measurements,
        dominant=parts.dominant,
        entry_point=parts.entry_point,
        suggestions=parts.suggestions,
        caveats=parts.caveats,
        wrapper_path=parts.wrapper_path,
        reach=parts.reach,
        depth_limited=depth_limited,
    )


def _finding_parts(
    function: FunctionInfo,
    module: ModuleInfo,
    reached: set[str],
    unresolved: int,
    depth_limited: bool,
    index: CallableIndex,
    config: ArchbraceConfig,
) -> _FindingParts:
    scores = compute_scores(function, module, reached, unresolved, index, config)
    wrapper_path = build_wrapper_path(function, module, index, config)
    wrapper_depth = longest_wrapper_chain_depth(function, index, config)
    measurements = compute_measurements(
        module, reached, wrapper_depth, unresolved, config
    )
    reach = build_reach_summary(module, reached)
    return _FindingParts(
        scores=scores,
        wrapper_path=wrapper_path,
        measurements=measurements,
        dominant=select_dominant(scores),
        entry_point=classify_entry_point(function, module, config),
        reach=reach,
        suggestions=build_suggestions(scores, measurements, reach, wrapper_path),
        caveats=build_caveats(
            measurements,
            unresolved,
            config,
            reach,
            wrapper_path,
            depth_limited=depth_limited,
        ),
    )
