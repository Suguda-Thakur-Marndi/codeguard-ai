"""Dataset and scenario loader for CodeGuard AI benchmarks."""

import json
import os
from pathlib import Path
from typing import Any

from evaluation.scenarios.schema import (
    BenchmarkDataset,
    BenchmarkScenario,
    ScenarioCategory,
    ScenarioType,
)


class ScenarioLoader:
    """Discovers, parses, and strictly validates benchmark scenarios."""

    def __init__(self, base_dir: str | Path | None = None):
        if base_dir is None:
            # Default to codeguard-ai/evaluation/datasets
            current_file = Path(__file__).resolve()
            base_dir = current_file.parent.parent / "datasets"
        self.base_dir = Path(base_dir)

    def list_datasets(self) -> list[str]:
        """List available dataset versions (e.g. ['v1'])."""
        if not self.base_dir.exists():
            return []
        return [
            d.name
            for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "scenarios.json").exists()
        ]

    def load_dataset(self, version: str = "v1") -> BenchmarkDataset:
        """Load and validate an entire dataset version."""
        dataset_path = self.base_dir / version / "scenarios.json"
        if not dataset_path.exists():
            raise FileNotFoundError(f"Benchmark dataset '{version}' not found at {dataset_path}")

        with open(dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict) and "scenarios" in raw_data:
            dataset = BenchmarkDataset.model_validate(raw_data)
        elif isinstance(raw_data, list):
            dataset = BenchmarkDataset(
                dataset_version=version,
                description=f"Dataset {version}",
                scenarios=[BenchmarkScenario.model_validate(item) for item in raw_data],
            )
        else:
            raise ValueError(f"Invalid dataset format at {dataset_path}: expected dict or list")

        return dataset

    def load_scenarios(
        self,
        version: str = "v1",
        category: ScenarioCategory | str | None = None,
        scenario_type: ScenarioType | str | None = None,
        language: str | None = None,
        difficulty: str | None = None,
        tags: list[str] | None = None,
        scenario_id: str | None = None,
    ) -> list[BenchmarkScenario]:
        """Filter scenarios from a dataset based on criteria."""
        dataset = self.load_dataset(version)
        results: list[BenchmarkScenario] = []

        cat_str = category.value if isinstance(category, ScenarioCategory) else category
        type_str = scenario_type.value if isinstance(scenario_type, ScenarioType) else scenario_type

        for s in dataset.scenarios:
            if scenario_id and s.scenario_id != scenario_id:
                continue
            if cat_str and s.category != cat_str:
                continue
            if type_str and s.scenario_type != type_str:
                continue
            if language and s.language.lower() != language.lower():
                continue
            if difficulty and s.difficulty.upper() != difficulty.upper():
                continue
            if tags and not any(tag in s.tags for tag in tags):
                continue
            results.append(s)

        return results

    def get_scenario(self, scenario_id: str, version: str = "v1") -> BenchmarkScenario:
        """Retrieve a specific scenario by its ID."""
        scenarios = self.load_scenarios(version=version, scenario_id=scenario_id)
        if not scenarios:
            raise KeyError(f"Scenario '{scenario_id}' not found in dataset '{version}'")
        return scenarios[0]
