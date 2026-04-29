import asyncio
import logging
from datetime import date

from sqlalchemy import select

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.invoice_tasks.check_overdue_invoices")  # type: ignore[untyped-decorator]
def check_overdue_invoices() -> None:
    asyncio.run(_check_overdue())


async def _check_overdue() -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from ..config import settings
    from ..models.billing import Invoice

    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    today = date.today()
    async with factory() as session:
        result = await session.execute(
            select(Invoice).where(
                Invoice.status == "sent",
                Invoice.due_date < today,
                Invoice.deleted_at.is_(None),
            )
        )
        overdue = list(result.scalars().all())
        for inv in overdue:
            inv.status = "overdue"
            days = (today - inv.due_date).days
            logger.info("Invoice %s marked overdue (%d days)", inv.invoice_number, days)
        await session.commit()
    await engine.dispose()
