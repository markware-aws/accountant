from datetime import date
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
import httpx

from schemas import Invoice, VatSummary, VatRateBucket
from services.mydata import MydataClient, VAT_CATEGORY_RATE

router = APIRouter()


def _get_client(
    aade_user_id: Optional[str],
    aade_subscription_key: Optional[str],
    sandbox: bool,
) -> MydataClient:
    if not aade_user_id or not aade_subscription_key:
        raise HTTPException(
            status_code=401,
            detail="Missing headers: X-Aade-User-Id and X-Aade-Subscription-Key required",
        )
    return MydataClient(aade_user_id, aade_subscription_key, sandbox=sandbox)


@router.get("/income", response_model=list[Invoice])
async def get_income(
    date_from: date = Query(..., description="YYYY-MM-DD"),
    date_to:   date = Query(..., description="YYYY-MM-DD"),
    counterpart_vat: Optional[str] = Query(None),
    sandbox: bool = Query(True, description="Use sandbox environment"),
    x_aade_user_id: Optional[str] = Header(None, alias="X-Aade-User-Id"),
    x_aade_subscription_key: Optional[str] = Header(None, alias="X-Aade-Subscription-Key"),
):
    client = _get_client(x_aade_user_id, x_aade_subscription_key, sandbox)
    try:
        return await client.get_income(date_from, date_to, counterpart_vat)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/expenses", response_model=list[Invoice])
async def get_expenses(
    date_from: date = Query(..., description="YYYY-MM-DD"),
    date_to:   date = Query(..., description="YYYY-MM-DD"),
    counterpart_vat: Optional[str] = Query(None),
    sandbox: bool = Query(True, description="Use sandbox environment"),
    x_aade_user_id: Optional[str] = Header(None, alias="X-Aade-User-Id"),
    x_aade_subscription_key: Optional[str] = Header(None, alias="X-Aade-Subscription-Key"),
):
    client = _get_client(x_aade_user_id, x_aade_subscription_key, sandbox)
    try:
        return await client.get_expenses(date_from, date_to, counterpart_vat)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/vat-summary", response_model=VatSummary)
async def get_vat_summary(
    date_from: date = Query(..., description="YYYY-MM-DD"),
    date_to:   date = Query(..., description="YYYY-MM-DD"),
    sandbox: bool = Query(True, description="Use sandbox environment"),
    x_aade_user_id: Optional[str] = Header(None, alias="X-Aade-User-Id"),
    x_aade_subscription_key: Optional[str] = Header(None, alias="X-Aade-Subscription-Key"),
):
    """
    Pre-fills VAT return data for the given period.
    Returns output VAT (income) and input VAT (expenses) broken down by rate.
    vat_payable = output VAT - input VAT.
    """
    client = _get_client(x_aade_user_id, x_aade_subscription_key, sandbox)

    try:
        income, expenses = await _fetch_both(client, date_from, date_to)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    income_by_rate   = _aggregate_by_rate(income)
    expenses_by_rate = _aggregate_by_rate(expenses)

    income_total_net = sum(i.net_value for i in income)
    income_total_vat = sum(i.vat_amount for i in income)
    expenses_total_net = sum(e.net_value for e in expenses)
    expenses_total_vat = sum(e.vat_amount for e in expenses)

    return VatSummary(
        date_from=date_from,
        date_to=date_to,
        income_total_net=round(income_total_net, 2),
        income_total_vat=round(income_total_vat, 2),
        income_by_rate=income_by_rate,
        expenses_total_net=round(expenses_total_net, 2),
        expenses_total_vat=round(expenses_total_vat, 2),
        expenses_by_rate=expenses_by_rate,
        vat_payable=round(income_total_vat - expenses_total_vat, 2),
        invoice_count_income=len(income),
        invoice_count_expenses=len(expenses),
    )


async def _fetch_both(client: MydataClient, date_from: date, date_to: date):
    import asyncio
    return await asyncio.gather(
        client.get_income(date_from, date_to),
        client.get_expenses(date_from, date_to),
    )


def _aggregate_by_rate(invoices: list[Invoice]) -> list[VatRateBucket]:
    """Aggregate invoice lines by VAT rate percentage."""
    buckets: dict[float, dict] = defaultdict(lambda: {"net": 0.0, "vat": 0.0})

    for inv in invoices:
        if inv.lines:
            # Use line-level detail when available
            for line in inv.lines:
                rate = VAT_CATEGORY_RATE.get(line.vat_category, 0.0)
                buckets[rate]["net"] += line.net_value
                buckets[rate]["vat"] += line.vat_amount
        else:
            # Fall back to invoice summary — assume single rate
            # Infer rate from vat_amount / net_value
            if inv.net_value > 0:
                implied_rate = round((inv.vat_amount / inv.net_value) * 100)
                # Snap to known rates
                rate = min([0.0, 6.0, 13.0, 24.0], key=lambda r: abs(r - implied_rate))
            else:
                rate = 0.0
            buckets[rate]["net"] += inv.net_value
            buckets[rate]["vat"] += inv.vat_amount

    return [
        VatRateBucket(
            rate_pct=rate,
            net_value=round(vals["net"], 2),
            vat_amount=round(vals["vat"], 2),
        )
        for rate, vals in sorted(buckets.items(), reverse=True)
        if vals["net"] != 0 or vals["vat"] != 0
    ]
