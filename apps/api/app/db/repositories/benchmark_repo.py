"""Repository layer for Benchmark runs, results, and finding evaluations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.repositories.base_repo import BaseRepository
from app.models.benchmark import (
    BenchmarkFindingEvaluationModel,
    BenchmarkResultModel,
    BenchmarkRunModel,
)


class BenchmarkRunRepository(BaseRepository[BenchmarkRunModel]):
    """Data access repository for benchmark execution runs."""

    def __init__(self, db: Session):
        super().__init__(BenchmarkRunModel, db)

    def get_run_with_results(self, run_id: str) -> BenchmarkRunModel | None:
        """Fetch benchmark run with all scenario results and finding evaluations."""
        stmt = (
            select(BenchmarkRunModel)
            .options(
                selectinload(BenchmarkRunModel.results).selectinload(
                    BenchmarkResultModel.evaluations
                )
            )
            .where(BenchmarkRunModel.id == run_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_runs(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[BenchmarkRunModel], int]:
        """Fetch paginated benchmark runs ordered by creation date descending."""
        return self.get_all(
            page=page,
            page_size=page_size,
            order_by=BenchmarkRunModel.created_at.desc(),
        )


class BenchmarkResultRepository(BaseRepository[BenchmarkResultModel]):
    """Data access repository for individual scenario benchmark results."""

    def __init__(self, db: Session):
        super().__init__(BenchmarkResultModel, db)

    def get_results_for_run(self, run_id: str) -> list[BenchmarkResultModel]:
        """Fetch all results belonging to a specific benchmark run."""
        stmt = (
            select(BenchmarkResultModel)
            .options(selectinload(BenchmarkResultModel.evaluations))
            .where(BenchmarkResultModel.run_id == run_id)
            .order_by(BenchmarkResultModel.scenario_id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())


class BenchmarkFindingEvaluationRepository(
    BaseRepository[BenchmarkFindingEvaluationModel]
):
    """Data access repository for finding-level evaluations."""

    def __init__(self, db: Session):
        super().__init__(BenchmarkFindingEvaluationModel, db)
