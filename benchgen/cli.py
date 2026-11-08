"""rhscan-bench CLI: generate | tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from benchgen.gen import generate, write_dataset
from benchgen.tasks import materialize_tasks

app = typer.Typer(name="rhscan-bench", help="Generate labeled benchmark trajectories")


@app.command()
def tasks(out: Annotated[str, typer.Option("--out")] = "bench/tasks") -> None:
    """Materialize the task bank (mini-repos) under bench/tasks/<task_id>/."""
    materialize_tasks(Path(out))
    typer.echo(f"task bank written to {out}")


@app.command()
def generate_cmd(
    seed: Annotated[int, typer.Option("--seed")] = 42,
    n_per_class: Annotated[int, typer.Option("--n-per-class")] = 40,
    out: Annotated[str, typer.Option("--out")] = "bench",
    no_adversarial: Annotated[bool, typer.Option("--no-adversarial")] = False,
) -> None:
    """Generate trajectories.parquet + labels.parquet + manifest.json."""
    trajectories, labels = generate(
        seed=seed, n_per_class=n_per_class, adversarial=not no_adversarial
    )
    manifest = write_dataset(trajectories, labels, Path(out), seed)
    typer.echo(
        f"wrote {manifest['n_trajectories']} trajectories to {out} "
        f"(rules hash {manifest['rules_hash']})"
    )


generate_cmd.__name__ = "generate"


def main() -> None:
    app()


if __name__ == "__main__":
    main()
