from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.domain.quotes import QuoteStatus
from backend.models.quote import Quote, QuoteLine, QuoteRevision, QuoteRevisionLine


class QuoteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, quote_id: int, *, for_update: bool = False) -> Quote | None:
        statement = select(Quote).where(Quote.id == quote_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: QuoteStatus | None,
        assignee_user_id: int | None,
        customer: str | None,
    ) -> tuple[list[Quote], int]:
        statement = select(Quote)
        count_statement = select(func.count()).select_from(Quote)
        filters = []
        if status is not None:
            filters.append(Quote.status == status)
        if assignee_user_id is not None:
            filters.append(Quote.assignee_user_id == assignee_user_id)
        if customer:
            filters.append(Quote.customer_name_snapshot.ilike(f"%{customer}%"))
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        statement = statement.order_by(Quote.updated_at.desc(), Quote.id.desc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def lines_for_quote(self, quote_id: int) -> list[QuoteLine]:
        statement = select(QuoteLine).where(QuoteLine.quote_id == quote_id).order_by(QuoteLine.position.asc())
        return list(self.session.scalars(statement))

    def revisions_for_quote(self, quote_id: int, *, page: int, page_size: int) -> tuple[list[QuoteRevision], int]:
        statement = select(QuoteRevision).where(QuoteRevision.quote_id == quote_id)
        count_statement = select(func.count()).select_from(QuoteRevision).where(QuoteRevision.quote_id == quote_id)
        statement = statement.order_by(QuoteRevision.revision_number.desc()).offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)

    def revision_for_quote(self, quote_id: int, revision_number: int) -> QuoteRevision | None:
        return self.session.scalar(
            select(QuoteRevision).where(
                QuoteRevision.quote_id == quote_id,
                QuoteRevision.revision_number == revision_number,
            )
        )

    def get_revision(self, revision_id: int) -> QuoteRevision | None:
        return self.session.scalar(select(QuoteRevision).where(QuoteRevision.id == revision_id))

    def lines_for_revision(self, revision_id: int) -> list[QuoteRevisionLine]:
        statement = (
            select(QuoteRevisionLine)
            .where(QuoteRevisionLine.quote_revision_id == revision_id)
            .order_by(QuoteRevisionLine.position.asc())
        )
        return list(self.session.scalars(statement))
