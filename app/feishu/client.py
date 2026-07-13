from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings


@dataclass(frozen=True)
class FeishuDocumentRef:
    document_id: str
    title: str


class FeishuApiError(RuntimeError):
    pass


class FeishuClient:
    base_url = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        timeout_seconds: int = 15,
    ):
        self.app_id = app_id or settings.feishu_app_id
        self.app_secret = app_secret or settings.feishu_app_secret
        self.timeout_seconds = timeout_seconds
        self._tenant_access_token: str | None = None
        self._tenant_access_token_expire_at = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def get_document_raw_content(self, document_id: str) -> str:
        data = self.request(
            "GET",
            f"/docx/v1/documents/{document_id}/raw_content",
        )
        content = data.get("content") or data.get("raw_content") or ""

        if not isinstance(content, str):
            raise FeishuApiError(f"飞书文档内容格式异常：{document_id}")

        return content

    def create_bitable_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        data = self.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            query={"user_id_type": "open_id"},
            body={"fields": fields},
        )
        return data.get("record", data)

    def list_bitable_records(
        self,
        app_token: str,
        table_id: str,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        records = []
        page_token: str | None = None

        while True:
            query: dict[str, Any] = {"page_size": min(page_size, 500)}
            if page_token:
                query["page_token"] = page_token

            data = self.request(
                "GET",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                query=query,
            )
            records.extend(data.get("items") or data.get("records") or [])

            if not data.get("has_more"):
                break

            page_token = data.get("page_token")
            if not page_token:
                break

        return records

    def request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        with_auth: bool = True,
    ) -> dict[str, Any]:
        if with_auth and not self.is_configured:
            raise FeishuApiError("缺少飞书配置：FEISHU_APP_ID 或 FEISHU_APP_SECRET 未设置")

        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if with_auth:
            headers["Authorization"] = f"Bearer {self.tenant_access_token()}"

        payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = Request(url, data=payload, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise FeishuApiError(f"飞书 HTTP 调用失败：status={error.code}, body={error_body}") from error
        except URLError as error:
            raise FeishuApiError(f"飞书网络调用失败：{error.reason}") from error

        try:
            result = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise FeishuApiError(f"飞书响应不是合法 JSON：{response_body[:300]}") from error

        code = result.get("code", 0)
        if code != 0:
            message = result.get("msg") or result.get("message") or "unknown error"
            raise FeishuApiError(f"飞书 API 调用失败：code={code}, msg={message}, path={path}")

        return result.get("data", result)

    def tenant_access_token(self) -> str:
        now = time.time()
        if self._tenant_access_token and now < self._tenant_access_token_expire_at - 60:
            return self._tenant_access_token

        if not self.is_configured:
            raise FeishuApiError("缺少飞书配置：FEISHU_APP_ID 或 FEISHU_APP_SECRET 未设置")

        result = self.request(
            "POST",
            "/auth/v3/tenant_access_token/internal",
            body={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
            with_auth=False,
        )

        token = result.get("tenant_access_token")
        if not token:
            raise FeishuApiError("飞书没有返回 tenant_access_token")

        expire_seconds = int(result.get("expire", 7200))
        self._tenant_access_token = token
        self._tenant_access_token_expire_at = now + expire_seconds
        return token


def get_configured_document_refs() -> list[FeishuDocumentRef]:
    refs = []

    for raw_item in settings.feishu_document_ids.split(","):
        item = raw_item.strip()
        if not item:
            continue

        if "|" in item:
            document_id, title = item.split("|", 1)
            refs.append(
                FeishuDocumentRef(
                    document_id=document_id.strip(),
                    title=title.strip() or document_id.strip(),
                )
            )
        else:
            refs.append(
                FeishuDocumentRef(
                    document_id=item,
                    title=f"飞书文档-{item}",
                )
            )

    return refs


def get_feishu_client() -> FeishuClient:
    return FeishuClient()
