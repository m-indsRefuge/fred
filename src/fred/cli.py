from __future__ import annotations

import argparse
import asyncio
import json
import re
from typing import Any

from fred.bootstrap import build_runtime, surreal_client
from fred.config import FredConfig
from fred.db.health import health_report
from fred.db.migrate import apply_schema
from fred.experiments.memory_v1 import ExperimentHarness

_EXPERIMENT_DB_RE = re.compile(r"^fred_mem01_exp0[1-4]_[0-9a-f]{12}$")


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


async def _health(config: FredConfig) -> int:
    report = await health_report(config)
    _print(report)
    surreal_ok = bool(report["surreal"]["ok"])
    ollama = report["ollama"]
    models_ok = bool(
        ollama["ok"]
        and ollama["cognitive_model_present"]
        and ollama["embedding_model_present"]
    )
    return 0 if surreal_ok and models_ok else 2


async def _migrate(config: FredConfig) -> int:
    await apply_schema(surreal_client(config))
    _print({"status": "OK", "database": config.surreal_database})
    return 0


async def _observer(config: FredConfig, session_id: str | None) -> int:
    _runtime, observer, _repositories = build_runtime(config)
    _print(await observer.snapshot(session_id=session_id))
    return 0


async def _experiment(config: FredConfig, name: str, runs: int) -> int:
    harness = ExperimentHarness(config)
    result = (
        await harness.run_all(runs=runs)
        if name == "all"
        else await harness.run(name, runs=runs)
    )
    _print(result)
    return 0 if result["accepted"] else 3


async def _reset_experiment_db(config: FredConfig, database: str) -> int:
    if not _EXPERIMENT_DB_RE.fullmatch(database):
        raise ValueError(
            "refusing reset: database must match fred_mem01_exp0[1-4]_<12 hex chars>"
        )
    client = surreal_client(config.for_database(database))
    await client.query(f"REMOVE DATABASE {database};")
    _print({"status": "REMOVED", "database": database})
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fred", description="Fred Memory Complex V1")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="check SurrealDB, Ollama, and required models")
    sub.add_parser("migrate", help="apply the MEM-01 SurrealDB schema")

    observer = sub.add_parser("observer", help="print a read-only Memory Observer snapshot")
    observer.add_argument("--session-id")

    experiment = sub.add_parser("experiment", help="run behavioural acceptance experiments")
    experiment.add_argument("name", choices=["EXP-01", "EXP-02", "EXP-03", "EXP-04", "all"])
    experiment.add_argument("--runs", type=int, default=5)

    reset = sub.add_parser(
        "reset-experiment-db",
        help="remove one exact isolated experiment database",
    )
    reset.add_argument("database")
    return parser


async def _main_async(args: argparse.Namespace) -> int:
    config = FredConfig.from_env()
    if args.command == "health":
        return await _health(config)
    if args.command == "migrate":
        return await _migrate(config)
    if args.command == "observer":
        return await _observer(config, args.session_id)
    if args.command == "experiment":
        if args.runs < 1:
            raise ValueError("--runs must be >= 1")
        return await _experiment(config, args.name, args.runs)
    if args.command == "reset-experiment-db":
        return await _reset_experiment_db(config, args.database)
    raise AssertionError(args.command)


def main() -> None:
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
