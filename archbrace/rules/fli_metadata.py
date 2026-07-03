"""
Purpose:
    Serialize AR073 findings into diagnostic metadata.

Why is this in this project:
    Keeps the rule module small while exposing rich JSON metadata.

Inputs:
    ``FlowLocalityFinding`` values and diagnostic limits.

Outputs:
    Metadata dictionaries for diagnostics.

Side effects:
    None.

Failure behavior:
    Never raises for well-formed findings.
"""

from __future__ import annotations

from ..analysis.fli_models import FlowLocalityFinding


def finding_metadata(name: str, finding: FlowLocalityFinding, limit: int) -> dict[str, object]:
    return {
        "actual": finding.fli,
        "limit": limit,
        "symbol": name,
        "entry": finding.entry,
        "scores": _scores_metadata(finding),
        "dominant": _dominant_metadata(finding),
        "measurements": _measurements_metadata(finding),
        "reach": _reach_metadata(finding),
        "wrapper_path": _wrapper_path_metadata(finding),
        "entry_point": _entry_point_metadata(finding),
        "suggestions": _suggestions_metadata(finding),
        "caveats": list(finding.caveats),
        "path": list(finding.path),
        "reasons": list(finding.reasons),
        "unresolved_edges": finding.unresolved_edges,
    }


def _scores_metadata(finding: FlowLocalityFinding) -> dict[str, int]:
    return {
        "module_span": finding.scores.module_span,
        "layer_crossing": finding.scores.layer_crossing,
        "wrapper_chain": finding.scores.wrapper_chain,
        "remote_domain": finding.scores.remote_domain,
        "unresolved_edge": finding.scores.unresolved_edge,
    }


def _dominant_metadata(finding: FlowLocalityFinding) -> dict[str, object]:
    return {
        "component": finding.dominant.component,
        "score": finding.dominant.score,
        "ties": list(finding.dominant.ties),
    }


def _measurements_metadata(finding: FlowLocalityFinding) -> dict[str, int]:
    measurements = finding.measurements
    return {
        "module_count": measurements.module_count,
        "wrapper_depth": measurements.wrapper_depth,
        "generic_layer_count": measurements.generic_layer_count,
        "remote_domain_count": measurements.remote_domain_count,
        "foreign_module_count": measurements.foreign_module_count,
        "unresolved_call_count": measurements.unresolved_call_count,
        "traversal_depth_limit": measurements.traversal_depth_limit,
    }


def _reach_metadata(finding: FlowLocalityFinding) -> dict[str, object]:
    reach = finding.reach
    return {
        "modules": list(reach.modules),
        "generic_layers": list(reach.generic_layers),
        "remote_domains": list(reach.remote_domains),
        "visited_shared_utils": reach.visited_shared_utils,
        "truncated": reach.truncated,
    }


def _wrapper_path_metadata(finding: FlowLocalityFinding) -> dict[str, object]:
    wrapper_path = finding.wrapper_path
    return {
        "labels": list(wrapper_path.labels),
        "qualified_names": list(wrapper_path.qualified_names),
        "depth": wrapper_path.depth,
    }


def _entry_point_metadata(finding: FlowLocalityFinding) -> dict[str, object]:
    entry_point = finding.entry_point
    return {
        "signals": list(entry_point.signals),
        "decorators": list(entry_point.decorators),
        "is_public": entry_point.is_public,
        "parent_class": entry_point.parent_class,
    }


def _suggestions_metadata(finding: FlowLocalityFinding) -> list[dict[str, object]]:
    return [
        {
            "component": suggestion.component,
            "priority": suggestion.priority,
            "text": suggestion.text,
        }
        for suggestion in finding.suggestions
    ]
