from __future__ import annotations

from datetime import timedelta

from loguru import logger

from app.core.celery_app import celery_app


def _requeue_task(task_id: str, candidate_id: str | None) -> None:
    celery_app.send_task(
        "app.worker.celery_tasks.process_files_task",
        args=[task_id, candidate_id],
    )


@celery_app.task  # type: ignore[arg-type]
def reclaim_stuck_tasks() -> None:
    """Return RUNNING tasks with stale heartbeat back to PENDING and re-queue them."""
    import asyncio

    from app.infrastructure.database.repositories import SQLAlchemyTaskRepository
    from app.infrastructure.database.session import create_session_factory

    async def _run() -> None:
        async_session_maker, engine = create_session_factory()
        try:
            async with async_session_maker() as session:
                repo = SQLAlchemyTaskRepository(session)
                stuck = await repo.reclaim_stuck(max_heartbeat_age=timedelta(minutes=5), limit=20)
                await session.commit()
                if stuck:
                    logger.info(
                        "reclaimed_stuck_tasks",
                        count=len(stuck),
                        ids=[t.id for t in stuck],
                    )
                    for task in stuck:
                        _requeue_task(task.id, task.candidate_id or None)
                        logger.info(
                            "requeued_task",
                            task_id=task.id,
                            worker_id=str(task.worker_id),
                        )
        finally:
            await engine.dispose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_run())


@celery_app.task  # type: ignore[arg-type]
def reclaim_blocked_tasks() -> None:
    """Return BLOCKED tasks past their blocked_until back to PENDING and re-queue them."""
    import asyncio

    from app.infrastructure.database.repositories import SQLAlchemyTaskRepository
    from app.infrastructure.database.session import create_session_factory

    async def _run() -> None:
        async_session_maker, engine = create_session_factory()
        try:
            async with async_session_maker() as session:
                repo = SQLAlchemyTaskRepository(session)
                released = await repo.reclaim_blocked(limit=20)
                await session.commit()
                if released:
                    logger.info(
                        "reclaimed_blocked_tasks",
                        count=len(released),
                        ids=[t.id for t in released],
                    )
                    for task in released:
                        _requeue_task(task.id, task.candidate_id or None)
                        logger.info(
                            "requeued_blocked_task",
                            task_id=task.id,
                        )
        finally:
            await engine.dispose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_run())
