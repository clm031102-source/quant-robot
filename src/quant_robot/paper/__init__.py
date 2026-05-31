"""Local paper trading simulation. Research-only, no broker integration."""

from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation, write_paper_simulation_artifacts

__all__ = [
    "PaperSimulationConfig",
    "run_paper_simulation",
    "write_paper_simulation_artifacts",
]
