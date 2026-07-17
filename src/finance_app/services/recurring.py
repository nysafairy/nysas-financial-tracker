"""Subscriptions, standing orders, and recurring income."""

from __future__ import annotations

from sqlalchemy import select

from finance_app.db.models import Frequency, RecurringItem, RecurringKind
from finance_app.db.session import get_session


def list_recurring(*, active_only: bool = False) -> list[RecurringItem]:
    with get_session() as session:
        stmt = select(RecurringItem).order_by(RecurringItem.kind, RecurringItem.name)
        if active_only:
            stmt = stmt.where(RecurringItem.active.is_(True))
        return list(session.scalars(stmt).all())


def create_recurring(
    name: str,
    kind: RecurringKind | str,
    amount: float,
    frequency: Frequency | str = Frequency.MONTHLY,
    *,
    from_account_id: int | None = None,
    to_account_id: int | None = None,
    day_of_month: int | None = None,
    notes: str | None = None,
    affects_net_worth: bool | None = None,
) -> RecurringItem:
    if isinstance(kind, str):
        kind = RecurringKind(kind)
    if isinstance(frequency, str):
        frequency = Frequency(frequency)
    if affects_net_worth is None:
        affects_net_worth = kind != RecurringKind.STANDING_ORDER

    with get_session() as session:
        item = RecurringItem(
            name=name.strip(),
            kind=kind,
            amount=float(amount),
            frequency=frequency,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            day_of_month=day_of_month,
            notes=notes,
            affects_net_worth=affects_net_worth,
            active=True,
        )
        session.add(item)
        session.flush()
        session.refresh(item)
        session.expunge(item)
        return item


def delete_recurring(item_id: int) -> None:
    with get_session() as session:
        item = session.get(RecurringItem, item_id)
        if item is None:
            return
        session.delete(item)


def set_recurring_active(item_id: int, active: bool) -> None:
    with get_session() as session:
        item = session.get(RecurringItem, item_id)
        if item is None:
            raise ValueError("Recurring item not found")
        item.active = active


def monthly_equivalent(amount: float, frequency: Frequency | str) -> float:
    if isinstance(frequency, str):
        frequency = Frequency(frequency)
    if frequency == Frequency.WEEKLY:
        return float(amount) * 52.0 / 12.0
    if frequency == Frequency.YEARLY:
        return float(amount) / 12.0
    return float(amount)


def recurring_monthly_totals() -> dict[str, float]:
    """Cashflow totals that affect net worth (excludes standing orders)."""
    items = list_recurring(active_only=True)
    out = {"subscriptions": 0.0, "income": 0.0, "standing_orders": 0.0}
    for item in items:
        monthly = monthly_equivalent(item.amount, item.frequency)
        if item.kind == RecurringKind.SUBSCRIPTION:
            out["subscriptions"] += monthly
        elif item.kind == RecurringKind.INCOME:
            out["income"] += monthly
        elif item.kind == RecurringKind.STANDING_ORDER:
            out["standing_orders"] += monthly
    return out
