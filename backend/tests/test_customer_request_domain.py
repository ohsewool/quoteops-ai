from backend.domain.customer_requests import CustomerRequestStatus, ProductCode, allowed_transitions, is_terminal


def test_customer_request_transition_table_preserves_quote_conversion_boundary() -> None:
    assert allowed_transitions(CustomerRequestStatus.NEW) == (
        CustomerRequestStatus.REVIEWING,
        CustomerRequestStatus.CANCELLED,
    )
    assert CustomerRequestStatus.QUOTED in allowed_transitions(CustomerRequestStatus.REVIEWING)
    assert is_terminal(CustomerRequestStatus.CLOSED)
    assert is_terminal(CustomerRequestStatus.CANCELLED)
    assert not is_terminal(CustomerRequestStatus.REVIEWING)
    assert ProductCode.A3_FLYER.value == "a3_flyer"
