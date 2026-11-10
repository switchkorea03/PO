from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID
class OrderType(StrEnum):
    domestic="domestic"
    overseas="overseas"
class ERPType(StrEnum):
    domestic="domestic"
    export="export"
    unspecified="unspecified"
class TaskKind(StrEnum):
    domestic_share="domestic_share"
    domestic_request="domestic_request"
    domestic_statement="domestic_statement"
    domestic_excel="domestic_excel"
    domestic_voucher="domestic_voucher"
    overseas_invoice="overseas_invoice"
    overseas_bl_eta="overseas_bl_eta"
    overseas_erp="overseas_erp"
    overseas_mail="overseas_mail"
    overseas_excel="overseas_excel"
@dataclass(frozen=True)
class LineInput:
    id: UUID|None
    code: str
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal|None=None
    currency: str="KRW"
    source_amount: Decimal|None=None
    requested_due: date|None=None
    internal_name: str=""
@dataclass(frozen=True)
class OrderInput:
    customer_id: UUID
    po_number: str
    order_type: OrderType
    erp_type: ERPType=ERPType.unspecified
    ordered_on: date|None=None
    received_on: date|None=None
    contact: str=""
    note: str=""
    lines: tuple[LineInput,...]=()
@dataclass(frozen=True)
class ShipmentInput:
    id: UUID|None
    ship_on: date|None
    etd: date|None
    eta: date|None
    allocations: dict[UUID,Decimal]
@dataclass(frozen=True)
class TaskSpec:
    order_id: UUID
    shipment_id: UUID|None
    kind: TaskKind
    basis_on: date|None
    auto_on: date|None
    title: str
    substeps: tuple[str,...]
@dataclass(frozen=True)
class OrderSnapshot:
    id: UUID
    order_type: OrderType
    erp_type: ERPType
    currency: str
    received_on: date|None
    lines: tuple[LineInput,...]
    shipments: tuple[ShipmentInput,...]
@dataclass(frozen=True)
class TaskView:
    id: UUID
    order_id: UUID
    shipment_id: UUID|None
    customer_id: UUID
    customer_name: str
    po_number: str
    kind: TaskKind
    title: str
    effective_on: date|None
    open_steps: tuple[str,...]
    state: str
    suspended: bool
    notice_revision: int
    row_version: int
@dataclass(frozen=True)
class NoticeCandidate:
    id: UUID
    customer_name: str
    po_number: str
    title: str
    effective_on: date|None
    open_steps: tuple[str,...]
    notice_revision: int
