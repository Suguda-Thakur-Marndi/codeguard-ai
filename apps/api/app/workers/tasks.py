"""Background worker tasks for review job orchestration."""

import asyncio

from sqlalchemy.orm import Session

from app.core.exceptions import GitHubAPIError
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.review_job_service import ReviewJobService
from app.workers.celery_app import celery_app


def run_review_job_sync(job_id: str, db: Session | None = None) -> dict:
    """Synchronous execution helper for testing and standalone dev environments."""
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        service = ReviewJobService(db)
        # Run async execute_job in an event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If in an already running loop (e.g. inside an async test), schedule task or run with nest_asyncio / sub-thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                job = pool.submit(lambda: asyncio.run(service.execute_job(job_id))).result()
        else:
            job = asyncio.run(service.execute_job(job_id))

        return {
            "status": "success",
            "job_id": job.id,
            "job_status": job.status.value,
        }
    finally:
        if owns_session:
            db.close()


@celery_app.task(
    bind=True,
    name="process_review_job",
    max_retries=3,
    autoretry_for=(GitHubAPIError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_review_job(self: object, job_id: str) -> dict:
    """
    Celery task to asynchronously process a review job.
    Retrieves PR metadata & raw unified diff, persisting them as review artifacts.
    """
    logger.info(f"Worker received review job task: {job_id}")
    db = SessionLocal()
    try:
        service = ReviewJobService(db)
        job = asyncio.run(service.execute_job(job_id))
        return {
            "status": "success",
            "job_id": job.id,
            "job_status": job.status.value,
        }
    except GitHubAPIError as exc:
        if exc.retryable:
            logger.warning(f"Transient GitHub API error on review job {job_id}. Retrying task: {exc}")
            raise self.retry(exc=exc) from exc
        logger.error(f"Non-retryable GitHub API error on review job {job_id}: {exc}")
        return {"status": "failed", "job_id": job_id, "error": str(exc)}
    except Exception as exc:
        logger.error(f"Unexpected error processing review job {job_id}: {exc}", exc_info=True)
        return {"status": "failed", "job_id": job_id, "error": str(exc)}
    finally:
        db.close()


def publish_review_sync(
    publication_id: str,
    db: Session | None = None,
    current_head_sha_override: str | None = None,
    publisher: object | None = None,
) -> dict:
    """Synchronous review publication helper for testing and development environments."""
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        from app.services.publication_service import PublicationService
        service = PublicationService(db)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pub = pool.submit(
                    lambda: asyncio.run(
                        service.execute_publication(
                            publication_id=publication_id,
                            current_head_sha_override=current_head_sha_override,
                            publisher=publisher,
                        )
                    )
                ).result()
        else:
            pub = asyncio.run(
                service.execute_publication(
                    publication_id=publication_id,
                    current_head_sha_override=current_head_sha_override,
                    publisher=publisher,
                )
            )

        return {
            "status": "success",
            "publication_id": pub.id,
            "publication_status": pub.status.value,
            "github_review_id": pub.github_review_id,
        }
    finally:
        if owns_session:
            db.close()


@celery_app.task(
    bind=True,
    name="publish_review_job",
    max_retries=3,
    autoretry_for=(GitHubAPIError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def publish_review_task(self: object, publication_id: str) -> dict:
    """Celery background worker task for atomic GitHub review publication."""
    logger.info(f"Worker received review publication task: {publication_id}")
    db = SessionLocal()
    try:
        from app.services.publication_service import PublicationService
        service = PublicationService(db)
        pub = asyncio.run(service.execute_publication(publication_id=publication_id))
        return {
            "status": "success",
            "publication_id": pub.id,
            "publication_status": pub.status.value,
            "github_review_id": pub.github_review_id,
        }
    except GitHubAPIError as exc:
        if exc.retryable:
            logger.warning(f"Transient GitHub API error on review publication {publication_id}. Retrying: {exc}")
            raise self.retry(exc=exc) from exc
        logger.error(f"Non-retryable GitHub API error on review publication {publication_id}: {exc}")
        return {"status": "failed", "publication_id": publication_id, "error": str(exc)}
    except Exception as exc:
        logger.error(f"Unexpected error publishing review {publication_id}: {exc}", exc_info=True)
        return {"status": "failed", "publication_id": publication_id, "error": str(exc)}
    finally:
        db.close()

