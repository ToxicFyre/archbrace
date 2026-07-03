"""Tests for AR073 Flow Locality Index."""

from __future__ import annotations

import json

from archbrace.reporting.json import render_json
from archbrace.rules.flow_locality import FlowLocalityIndexRule


def _bad_invoice_flow() -> dict[str, str]:
    return {
        "invoice/api.py": (
            "from invoice.handlers import CreateInvoiceHandler\n"
            "\n"
            "def create_invoice(data):\n"
            "    return CreateInvoiceHandler().handle(data)\n"
        ),
        "invoice/handlers.py": (
            "from invoice.services import InvoiceService\n"
            "\n"
            "class CreateInvoiceHandler:\n"
            "    def handle(self, data):\n"
            "        return InvoiceService().execute(data)\n"
        ),
        "invoice/services.py": (
            "from invoice.processors import InvoiceProcessor\n"
            "\n"
            "class InvoiceService:\n"
            "    def execute(self, data):\n"
            "        return InvoiceProcessor().process(data)\n"
        ),
        "invoice/processors.py": (
            "from invoice.repositories import InvoiceRepository\n"
            "\n"
            "class InvoiceProcessor:\n"
            "    def process(self, data):\n"
            "        return InvoiceRepository().save(data)\n"
        ),
        "invoice/repositories.py": (
            "class InvoiceRepository:\n"
            "    def save(self, data):\n"
            "        return data\n"
        ),
    }


def _good_invoice_flow() -> dict[str, str]:
    return {
        "invoice/create.py": (
            "from invoice.models import build_model\n"
            "from invoice.calculations import calculate_total\n"
            "from invoice.pdf import render_pdf\n"
            "\n"
            "def create_invoice(data):\n"
            "    invoice = build_model(data)\n"
            "    total = calculate_total(invoice)\n"
            "    return render_pdf(invoice, total)\n"
        ),
        "invoice/models.py": (
            "def build_model(data):\n"
            "    return {'items': data['items']}\n"
        ),
        "invoice/calculations.py": (
            "def calculate_total(invoice):\n"
            "    return sum(item['price'] for item in invoice['items'])\n"
        ),
        "invoice/pdf.py": (
            "def render_pdf(invoice, total):\n"
            "    return {'invoice': invoice, 'total': total}\n"
        ),
    }


def test_flags_spread_generic_wrapper_flow(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    flagged = {d.metadata["symbol"] for d in diagnostics}
    assert "create_invoice" in flagged
    create = next(d for d in diagnostics if d.metadata["symbol"] == "create_invoice")
    assert create.code == "AR073"
    assert create.name == "flow-locality-index"
    assert create.severity == "warning"
    assert create.metadata["actual"] > config.max_fli
    assert create.metadata["limit"] == 8
    assert "module_span" in create.metadata["scores"]
    assert "wrapper_chain" in create.metadata["scores"]
    assert len(create.metadata["path"]) >= 4


def test_metadata_includes_dominant(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    dominant = create.metadata["dominant"]
    assert dominant["component"] == "wrapper_chain"
    assert dominant["score"] == create.metadata["scores"]["wrapper_chain"]


def test_measurements_match_score_buckets(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    measurements = create.metadata["measurements"]
    scores = create.metadata["scores"]
    assert measurements["module_count"] == 5
    assert scores["module_span"] == 5
    assert measurements["wrapper_depth"] >= 3
    assert scores["wrapper_chain"] >= 4
    assert measurements["generic_layer_count"] == 4
    assert measurements["traversal_depth_limit"] == 4


def test_wrapper_path_matches_legacy_path(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    assert create.metadata["path"] == create.metadata["wrapper_path"]["labels"]
    assert create.metadata["wrapper_path"]["depth"] == len(create.metadata["path"]) - 1
    assert len(create.metadata["wrapper_path"]["qualified_names"]) == len(
        create.metadata["path"]
    )


def test_reach_modules_covers_traversal(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    modules = create.metadata["reach"]["modules"]
    assert "invoice.api" in modules
    assert "invoice.handlers" in modules
    assert "invoice.repositories" in modules
    assert create.metadata["reach"]["generic_layers"] == [
        "handlers",
        "processors",
        "repositories",
        "services",
    ]


def test_suggestions_ordered_by_score(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    suggestions = create.metadata["suggestions"]
    priorities = [item["priority"] for item in suggestions]
    assert priorities == sorted(priorities)
    assert suggestions[0]["component"] == "wrapper_chain"
    assert suggestions[-1]["component"] == "general"


def test_entry_point_signals_for_named_entry(index_from_source, base_config) -> None:
    source = {
        "jobs/worker.py": (
            "def execute(payload):\n"
            "    return forward(payload)\n"
            "\n"
            "def forward(payload):\n"
            "    return dispatch(payload)\n"
            "\n"
            "def dispatch(payload):\n"
            "    return deliver(payload)\n"
            "\n"
            "def deliver(payload):\n"
            "    return payload\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=3, max_fli_depth=4)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    execute = next(d for d in diagnostics if d.metadata["symbol"] == "execute")
    assert "named_entry" in execute.metadata["entry_point"]["signals"]


def test_entry_point_signals_for_route_decorator(index_from_source, base_config) -> None:
    from archbrace.analysis.flow_locality import analyze_entry_point, build_callable_index

    source = {
        "app/api.py": (
            "import click\n"
            "\n"
            "@click.command()\n"
            "def run(data):\n"
            "    return handle(data)\n"
            "\n"
            "def handle(data):\n"
            "    return data\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=100, max_fli_depth=4)
    index = build_callable_index(project)
    module = project.modules[0]
    function = next(f for f in module.functions if f.name == "run")
    finding = analyze_entry_point(function, module, index, config)
    assert finding is not None
    assert "route_decorator" in finding.entry_point.signals


def test_caveats_when_unresolved(index_from_source, base_config) -> None:
    from archbrace.analysis.flow_locality import analyze_entry_point, build_callable_index

    source = {
        "app/run.py": (
            "def run(data):\n"
            "    callback = registry['handler']\n"
            "    return callback(data)\n"
            "\n"
            "def registry():\n"
            "    return {}\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=1, max_fli_depth=4)
    index = build_callable_index(project)
    module = project.modules[0]
    function = next(f for f in module.functions if f.name == "run")
    finding = analyze_entry_point(function, module, index, config)
    assert finding is not None
    assert any("underestimated" in caveat for caveat in finding.caveats)
    assert not any(
        "unresolved local-looking calls" in reason for reason in finding.reasons
    )


def test_message_is_single_line(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    create = FlowLocalityIndexRule().check(project, config)[0]
    assert "\n" not in create.message
    assert "flow locality" in create.message
    assert "13/8" in create.message or f"{create.metadata['actual']}/8" in create.message


def test_json_includes_documentation_url(index_from_source, base_config) -> None:
    project = index_from_source(_bad_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    payload = json.loads(render_json(diagnostics, base=project.root, files_scanned=1))
    entry = payload["diagnostics"][0]
    assert entry["url"].endswith("#ar073--flow-locality-index")
    assert "dominant" in entry["metadata"]
    assert "suggestions" in entry["metadata"]


def test_same_domain_clear_roles_pass(index_from_source, base_config) -> None:
    project = index_from_source(_good_invoice_flow())
    config = base_config(max_fli=8, max_fli_depth=4)
    assert FlowLocalityIndexRule().check(project, config) == []


def test_at_limit_passes(index_from_source, base_config) -> None:
    source = {
        "app/run.py": (
            "from app.work import execute\n"
            "\n"
            "def run(data):\n"
            "    return execute(data)\n"
        ),
        "app/work.py": (
            "def execute(data):\n"
            "    return transform(data)\n"
            "\n"
            "def transform(data):\n"
            "    return data\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=20, max_fli_depth=4)
    assert FlowLocalityIndexRule().check(project, config) == []


def test_private_helpers_are_not_entry_points(index_from_source, base_config) -> None:
    source = {
        "invoice/create.py": (
            "def create_invoice(data):\n"
            "    row = _parse_row(data)\n"
            "    return _normalize_name(row)\n"
            "\n"
            "def _parse_row(data):\n"
            "    return data\n"
            "\n"
            "def _normalize_name(row):\n"
            "    return row['name']\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=1, max_fli_depth=4)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    flagged = {d.metadata["symbol"] for d in diagnostics}
    assert "_parse_row" not in flagged
    assert "_normalize_name" not in flagged


def test_unresolved_edges_reported_in_metadata(index_from_source, base_config) -> None:
    from archbrace.analysis.flow_locality import analyze_entry_point, build_callable_index

    source = {
        "app/run.py": (
            "def run(data):\n"
            "    callback = registry['handler']\n"
            "    return callback(data)\n"
            "\n"
            "def registry():\n"
            "    return {}\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=100, max_fli_depth=4)
    index = build_callable_index(project)
    module = project.modules[0]
    function = next(f for f in module.functions if f.name == "run")
    finding = analyze_entry_point(function, module, index, config)
    assert finding is not None
    assert finding.unresolved_edges >= 1
    assert finding.scores.unresolved_edge >= 1


def test_ignore_tests_skips_test_modules(index_from_source, base_config) -> None:
    source = {
        "tests/test_invoice.py": (
            "from invoice.api import create_invoice\n"
            "\n"
            "def test_create_invoice():\n"
            "    assert create_invoice({'x': 1})\n"
        ),
        "invoice/api.py": (
            "from invoice.handlers import CreateInvoiceHandler\n"
            "\n"
            "def create_invoice(data):\n"
            "    return CreateInvoiceHandler().handle(data)\n"
        ),
        "invoice/handlers.py": (
            "class CreateInvoiceHandler:\n"
            "    def handle(self, data):\n"
            "        return data\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=1, max_fli_depth=4, fli_ignore_tests=True)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    assert all("test_invoice" not in str(d.path) for d in diagnostics)
    assert all(d.metadata["symbol"] != "test_create_invoice" for d in diagnostics)


def test_remote_domain_and_shared_utils_increase_score(index_from_source, base_config) -> None:
    source = {
        "invoice/create.py": (
            "from shared.utils import normalize\n"
            "from core.services import persist\n"
            "\n"
            "def create_invoice(data):\n"
            "    cleaned = normalize(data)\n"
            "    return persist(cleaned)\n"
        ),
        "shared/utils.py": (
            "def normalize(data):\n"
            "    return data\n"
        ),
        "core/services.py": (
            "def persist(data):\n"
            "    return data\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=3, max_fli_depth=4)
    diagnostic = FlowLocalityIndexRule().check(project, config)[0]
    assert diagnostic.metadata["scores"]["remote_domain"] >= 3


def test_named_entry_point_functions_are_analyzed(index_from_source, base_config) -> None:
    source = {
        "jobs/worker.py": (
            "def execute(payload):\n"
            "    return forward(payload)\n"
            "\n"
            "def forward(payload):\n"
            "    return dispatch(payload)\n"
            "\n"
            "def dispatch(payload):\n"
            "    return deliver(payload)\n"
            "\n"
            "def deliver(payload):\n"
            "    return payload\n"
        ),
    }
    project = index_from_source(source)
    config = base_config(max_fli=3, max_fli_depth=4)
    diagnostics = FlowLocalityIndexRule().check(project, config)
    assert any(d.metadata["symbol"] == "execute" for d in diagnostics)
