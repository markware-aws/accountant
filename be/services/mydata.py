"""
AADE myDATA API client.

Docs: https://mydata.aade.gr/
Sandbox: https://mydata-dev.aade.gr/myDATA/
Production: https://mydata.aade.gr/myDATA/

Authentication headers (passed per-request — one accountant, many clients):
  aade-user-id              : client's myDATA username (not AFM)
  ocp-apim-subscription-key : client's myDATA subscription key
"""
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional

import httpx

from schemas import Invoice, InvoiceLine

SANDBOX_URL = "https://mydataapidev.aade.gr/"
PRODUCTION_URL = "https://mydatapi.aade.gr/myDATA/"

# myDATA VAT category → rate mapping
VAT_CATEGORY_RATE: dict[int, float] = {
    1: 24.0,
    2: 13.0,
    3: 6.0,
    4: 17.0,  # island rate
    5: 9.0,   # island rate
    6: 4.0,   # island rate
    7: 0.0,   # exempt
    8: 0.0,   # not applicable
}


class MydataClient:
    def __init__(self, user_id: str, subscription_key: str, sandbox: bool = False):
        self.base_url = SANDBOX_URL if sandbox else PRODUCTION_URL
        self.headers = {
            "aade-user-id": user_id,
            "ocp-apim-subscription-key": subscription_key,
        }

    async def _get_all_pages(self, endpoint: str, params: dict) -> list[ET.Element]:
        """Fetches all pages for a paginated myDATA endpoint."""
        all_invoices: list[ET.Element] = []
        next_partition_key: Optional[str] = None
        next_row_key: Optional[str] = None

        async with httpx.AsyncClient(headers=self.headers, timeout=30, follow_redirects=True) as client:
            while True:
                page_params = dict(params)
                if next_partition_key:
                    page_params["nextPartitionKey"] = next_partition_key
                if next_row_key:
                    page_params["nextRowKey"] = next_row_key

                qs = "&".join(f"{k}={v}" for k, v in page_params.items())
                r = await client.get(f"{self.base_url}{endpoint}?{qs}")
                r.raise_for_status()

                root = ET.fromstring(r.text)
                ns = _detect_namespace(root)

                # Collect invoices from this page
                for inv in root.findall(f"{ns}invoicesDoc/{ns}invoice"):
                    all_invoices.append(inv)

                # Check for continuation token
                token = root.find(f"{ns}continuationToken")
                if token is None:
                    break

                npk = token.findtext(f"{ns}nextPartitionKey")
                nrk = token.findtext(f"{ns}nextRowKey")
                if not npk or not nrk:
                    break

                next_partition_key = npk
                next_row_key = nrk

        return all_invoices

    async def get_income(
        self,
        date_from: date,
        date_to: date,
        counterpart_vat: Optional[str] = None,
    ) -> list[Invoice]:
        params = {
            "dateFrom": date_from.strftime("%d/%m/%Y"),
            "dateTo":   date_to.strftime("%d/%m/%Y"),
        }
        if counterpart_vat:
            params["counterVatNumber"] = counterpart_vat

        elements = await self._get_all_pages("RequestMyIncome", params)
        return [_parse_invoice(el) for el in elements]

    async def get_expenses(
        self,
        date_from: date,
        date_to: date,
        counterpart_vat: Optional[str] = None,
    ) -> list[Invoice]:
        params = {
            "dateFrom": date_from.strftime("%d/%m/%Y"),
            "dateTo":   date_to.strftime("%d/%m/%Y"),
        }
        if counterpart_vat:
            params["counterVatNumber"] = counterpart_vat

        elements = await self._get_all_pages("RequestMyExpenses", params)
        return [_parse_invoice(el) for el in elements]


# ── XML helpers ──────────────────────────────────────────────────────────────

def _detect_namespace(root: ET.Element) -> str:
    """Returns namespace prefix string e.g. '{http://...}' or ''."""
    tag = root.tag
    if tag.startswith("{"):
        return "{" + tag[1:tag.index("}")] + "}"
    return ""


def _parse_invoice(element: ET.Element) -> Invoice:
    ns = _detect_namespace(element)

    mark = element.findtext(f"{ns}mark") or ""

    payload = element.find(f"{ns}payload/{ns}invoice")
    if payload is None:
        # Some cancelled invoices have no payload
        return Invoice(
            mark=mark,
            issue_date=date.today(),
            invoice_type="",
            counterpart_vat=None,
            net_value=0.0,
            vat_amount=0.0,
            gross_value=0.0,
        )

    header = payload.find(f"{ns}invoiceHeader") or ET.Element("_")
    summary = payload.find(f"{ns}invoiceSummary") or ET.Element("_")
    counterpart = payload.find(f"{ns}counterpart")

    issue_date_str = header.findtext(f"{ns}issueDate") or ""
    try:
        issue_date = date.fromisoformat(issue_date_str)
    except ValueError:
        issue_date = date.today()

    lines: list[InvoiceLine] = []
    for detail in payload.findall(f"{ns}invoiceDetails"):
        try:
            cat = int(detail.findtext(f"{ns}vatCategory") or "8")
            lines.append(InvoiceLine(
                net_value=float(detail.findtext(f"{ns}netValue") or 0),
                vat_category=cat,
                vat_amount=float(detail.findtext(f"{ns}vatAmount") or 0),
            ))
        except (ValueError, TypeError):
            continue

    return Invoice(
        mark=mark,
        issue_date=issue_date,
        invoice_type=header.findtext(f"{ns}invoiceType") or "",
        counterpart_vat=(
            counterpart.findtext(f"{ns}vatNumber") if counterpart is not None else None
        ),
        net_value=float(summary.findtext(f"{ns}totalNetValue") or 0),
        vat_amount=float(summary.findtext(f"{ns}totalVatAmount") or 0),
        gross_value=float(summary.findtext(f"{ns}totalGrossValue") or 0),
        lines=lines,
    )
