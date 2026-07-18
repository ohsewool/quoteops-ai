from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.domain.customer_requests import CustomerRequestStatus, ProductCode
from backend.models.customer_request import CustomerRequest


class CustomerRequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, request_id: int, *, for_update: bool = False) -> CustomerRequest | None:
        statement = select(CustomerRequest).where(CustomerRequest.id == request_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: CustomerRequestStatus | None,
        product_code: ProductCode | None,
        assignee_user_id: int | None,
        search: str | None,
    ) -> tuple[list[CustomerRequest], int]:
        statement = select(CustomerRequest)
        count_statement = select(func.count()).select_from(CustomerRequest)
        filters = []
        if status is not None:
            filters.append(CustomerRequest.status == status)
        if product_code is not None:
            filters.append(CustomerRequest.product_code == product_code)
        if assignee_user_id is not None:
            filters.append(CustomerRequest.assignee_user_id == assignee_user_id)
        if search:
            filters.append(CustomerRequest.customer_name.ilike(f"%{search}%"))
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        statement = statement.order_by(CustomerRequest.created_at.desc(), CustomerRequest.id.desc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        return list(self.session.scalars(statement)), int(self.session.scalar(count_statement) or 0)
