"""Tests for AR070 Wrapper Chain Too Deep."""

from __future__ import annotations

from archbrace.rules.indirection import WrapperChainTooDeepRule


def _chain_source(prefix: str = "") -> str:
    return (
        f"{prefix}"
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
        "\n"
        "def process_job(config):\n"
        "    return build_report(config)\n"
        "\n"
        "def build_report(config):\n"
        "    return config\n"
    )


def test_flags_direct_wrapper_chain_exceeding_limit(index_from_source, base_config) -> None:
    project = index_from_source({"chain.py": _chain_source()})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.code == "AR070"
    assert diagnostic.name == "wrapper-chain-too-deep"
    assert diagnostic.severity == "warning"
    assert diagnostic.metadata["actual"] == 3
    assert diagnostic.metadata["limit"] == 2
    assert diagnostic.metadata["symbol"] == "run_job"
    assert diagnostic.metadata["chain"] == [
        "chain.run_job",
        "chain.execute_job",
        "chain.process_job",
        "chain.build_report",
    ]


def test_chain_at_limit_passes(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
        "\n"
        "def process_job(config):\n"
        "    return config\n"
    )
    project = index_from_source({"limit_ok.py": source})
    config = base_config(max_wrapper_chain_depth=2)
    assert WrapperChainTooDeepRule().check(project, config) == []


def test_branching_function_is_not_wrapper(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    if config.enabled:\n"
        "        return process_job(config)\n"
        "    return default_value()\n"
        "\n"
        "def process_job(config):\n"
        "    return config\n"
        "\n"
        "def default_value():\n"
        "    return 0\n"
    )
    project = index_from_source({"branching.py": source})
    config = base_config(max_wrapper_chain_depth=1)
    assert WrapperChainTooDeepRule().check(project, config) == []


def test_multiple_meaningful_calls_are_not_wrapper(index_from_source, base_config) -> None:
    source = (
        "def run_job(x):\n"
        "    a = load_a(x)\n"
        "    b = load_b(x)\n"
        "    return combine(a, b)\n"
        "\n"
        "def load_a(x):\n"
        "    return x\n"
        "\n"
        "def load_b(x):\n"
        "    return x\n"
        "\n"
        "def combine(a, b):\n"
        "    return a + b\n"
    )
    project = index_from_source({"multi_call.py": source})
    config = base_config(max_wrapper_chain_depth=1)
    assert WrapperChainTooDeepRule().check(project, config) == []


def test_logging_plus_delegation_still_counts_as_wrapper(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    logger.info('Running job')\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
        "\n"
        "def process_job(config):\n"
        "    return build_report(config)\n"
        "\n"
        "def build_report(config):\n"
        "    return config\n"
    )
    project = index_from_source({"logged.py": source})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["symbol"] == "run_job"


def test_validation_plus_delegation_still_counts_as_wrapper(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    validate_config(config)\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
        "\n"
        "def process_job(config):\n"
        "    return build_report(config)\n"
        "\n"
        "def build_report(config):\n"
        "    return config\n"
        "\n"
        "def validate_config(config):\n"
        "    return config\n"
    )
    project = index_from_source({"validated.py": source})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["symbol"] == "run_job"


def test_async_wrapper_is_detected(index_from_source, base_config) -> None:
    source = (
        "async def run_job(config):\n"
        "    return await execute_job(config)\n"
        "\n"
        "async def execute_job(config):\n"
        "    return await process_job(config)\n"
        "\n"
        "async def process_job(config):\n"
        "    return await build_report(config)\n"
        "\n"
        "async def build_report(config):\n"
        "    return config\n"
    )
    project = index_from_source({"async_chain.py": source})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["symbol"] == "run_job"


def test_unresolved_external_calls_do_not_flag(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return external_service(config)\n"
    )
    project = index_from_source({"external.py": source})
    config = base_config(max_wrapper_chain_depth=1)
    assert WrapperChainTooDeepRule().check(project, config) == []


def test_cycle_does_not_crash(index_from_source, base_config) -> None:
    source = (
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return run_job(config)\n"
    )
    project = index_from_source({"cycle.py": source})
    config = base_config(max_wrapper_chain_depth=1)
    assert WrapperChainTooDeepRule().check(project, config) == []


def test_exempt_decorated_cli_function_is_not_flagged(index_from_source, base_config) -> None:
    source = (
        "def command():\n"
        "    def decorator(func):\n"
        "        func.__click_command__ = True\n"
        "        return func\n"
        "    return decorator\n"
        "\n"
        "@command()\n"
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
        "\n"
        "def process_job(config):\n"
        "    return build_report(config)\n"
        "\n"
        "def build_report(config):\n"
        "    return config\n"
    )
    project = index_from_source({"cli.py": source})
    config = base_config(
        max_wrapper_chain_depth=1,
        wrapper_chain_exempt_decorators=("command",),
    )
    flagged = {d.metadata["symbol"] for d in WrapperChainTooDeepRule().check(project, config)}
    assert "run_job" not in flagged


def test_method_chain_using_self_is_detected(index_from_source, base_config) -> None:
    source = (
        "class Runner:\n"
        "    def run_job(self, config):\n"
        "        return self.execute_job(config)\n"
        "\n"
        "    def execute_job(self, config):\n"
        "        return self.process_job(config)\n"
        "\n"
        "    def process_job(self, config):\n"
        "        return self.build_report(config)\n"
        "\n"
        "    def build_report(self, config):\n"
        "        return config\n"
    )
    project = index_from_source({"methods.py": source})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["symbol"] == "run_job"


def test_cross_file_chain_is_detected_when_imports_resolve(index_from_source, base_config) -> None:
    worker = (
        "def process_job(config):\n"
        "    return build_report(config)\n"
        "\n"
        "def build_report(config):\n"
        "    return config\n"
    )
    runner = (
        "from worker import process_job\n"
        "\n"
        "def run_job(config):\n"
        "    return execute_job(config)\n"
        "\n"
        "def execute_job(config):\n"
        "    return process_job(config)\n"
    )
    project = index_from_source({"worker.py": worker, "runner.py": runner})
    config = base_config(max_wrapper_chain_depth=2)
    diagnostics = WrapperChainTooDeepRule().check(project, config)
    assert len(diagnostics) == 1
    assert diagnostics[0].metadata["chain"] == [
        "runner.run_job",
        "runner.execute_job",
        "worker.process_job",
        "worker.build_report",
    ]
