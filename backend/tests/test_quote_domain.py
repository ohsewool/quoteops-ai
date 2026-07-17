from decimal import Decimal

from sqlalchemy import Numeric

from backend.domain.customer_requests import ProductCode
from backend.domain.quotes import QuoteStatus, quote_is_editable, quote_is_terminal
from backend.models.quote import Quote, QuoteLine, QuoteRevision, QuoteRevisionLine


def test_only_draft_quotes_are_editable() -> None:
    assert quote_is_editable(QuoteStatus.DRAFT)
    assert not quote_is_editable(QuoteStatus.PRICING_REVIEW)
    assert not quote_is_editable(QuoteStatus.APPROVAL_PENDING)
    assert not quote_is_editable(QuoteStatus.APPROVED)
    assert not quote_is_editable(QuoteStatus.REJECTED)
    assert not quote_is_editable(QuoteStatus.CANCELLED)
    assert quote_is_terminal(QuoteStatus.APPROVED)
    assert quote_is_terminal(QuoteStatus.CANCELLED)
    assert not quote_is_terminal(QuoteStatus.DRAFT)


def test_quote_models_use_krw_numeric_columns_and_shared_product_codes() -> None:
    for column in (
        Quote.__table__.c.total_amount,
        QuoteLine.__table__.c.unit_price,
        QuoteLine.__table__.c.line_total,
        QuoteRevision.__table__.c.total_amount,
        QuoteRevisionLine.__table__.c.unit_price,
        QuoteRevisionLine.__table__.c.line_total,
    ):
        assert isinstance(column.type, Numeric)
        assert (column.type.precision, column.type.scale) == (18, 2)

    assert Quote.__table__.c.request_product_code.type.enums == [member.value for member in ProductCode]
    assert Quote.__table__.c.status.type.enums == [member.value for member in QuoteStatus]
    assert Quote.__table__.c.total_amount.default.arg == Decimal("0.00")
