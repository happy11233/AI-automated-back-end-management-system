"""Business task contracts. Registration never implies external execution."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


TaskStatus = Literal['draft', 'awaiting_input', 'queued', 'running', 'awaiting_approval',
                     'awaiting_external', 'partially_completed', 'succeeded', 'failed', 'cancelled']
Position = Literal['operations', 'finance', 'customer_service']
ObjectType = Literal['order', 'order_line', 'sku', 'refund', 'settlement', 'bank_transaction',
                     'ticket', 'shipment', 'purchase', 'campaign', 'accounting_entry']


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class StoreCreate(StrictInput):
    platform: str = Field(min_length=1, max_length=40, pattern=r'^[a-z][a-z0-9_]*$')
    external_store_id: str = Field(min_length=1, max_length=160)
    marketplace: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)


class StoreGrant(StrictInput):
    user_id: UUID
    position: Position
    enabled: bool = True


class BusinessObjectRef(StrictInput):
    object_type: ObjectType
    external_id: str = Field(min_length=1, max_length=200)
    line_id: str = Field(default='', max_length=160)

    @model_validator(mode='after')
    def require_line_identity(self):
        if self.object_type == 'order_line' and not self.line_id:
            raise ValueError('订单行必须提供 line_id，不能只用订单号定位')
        return self


class TaskCreate(StrictInput):
    workflow_id: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1, max_length=4000)
    store_id: UUID | None = None
    thread_id: str | None = Field(default=None, min_length=1, max_length=160)
    expected_outputs: list[str] = Field(default_factory=list, max_length=20)
    completion_criteria: list[str] = Field(default_factory=list, max_length=20)
    objects: list[BusinessObjectRef] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def validate_scope_and_text(self):
        if self.objects and not self.store_id:
            raise ValueError('业务对象必须指定已授权店铺')
        for items in (self.expected_outputs, self.completion_criteria):
            if any(not v.strip() or len(v) > 500 for v in items):
                raise ValueError('交付物及完成条件必须为 1–500 字符的非空文本')
        return self


class TaskRunLink(StrictInput):
    run_id: UUID
