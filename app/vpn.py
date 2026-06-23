import json
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from .config import get_settings


@dataclass
class VpnAccess:
    username: str
    access_url: str


class DemoVpnProvider:
    async def create_or_extend(self, username: str, expires_at: datetime, traffic_gb: int, devices: int | None = None) -> VpnAccess:
        token = secrets.token_urlsafe(24)
        return VpnAccess(username, f"https://demo.joot/sub/{token}#{username}")

    async def disable(self, username: str) -> None:
        return None


class MarzbanProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = self.settings.marzban_url.rstrip("/")

    async def _token(self, client: httpx.AsyncClient) -> str:
        response = await client.post("/api/admin/token", data={
            "username": self.settings.marzban_username,
            "password": self.settings.marzban_password,
        })
        response.raise_for_status()
        return response.json()["access_token"]

    async def create_or_extend(self, username: str, expires_at: datetime, traffic_gb: int, devices: int | None = None) -> VpnAccess:
        if not self.base or not self.settings.marzban_username or not self.settings.marzban_password:
            raise RuntimeError("Marzban credentials are not configured")
        async with httpx.AsyncClient(base_url=self.base, verify=self.settings.marzban_verify_ssl, timeout=20) as client:
            token = await self._token(client)
            headers = {"Authorization": f"Bearer {token}"}
            expire = int(expires_at.replace(tzinfo=timezone.utc).timestamp())
            data_limit = traffic_gb * 1024 ** 3 if traffic_gb else 0
            payload = {
                "username": username,
                "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
                "inbounds": {"vless": []},
                "expire": expire,
                "data_limit": data_limit,
                "data_limit_reset_strategy": "no_reset",
                "status": "active",
            }
            current = await client.get(f"/api/user/{username}", headers=headers)
            if current.status_code == 404:
                response = await client.post("/api/user", headers=headers, json=payload)
            else:
                current.raise_for_status()
                response = await client.put(f"/api/user/{username}", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            url = data.get("subscription_url") or f"{self.base}/sub/{data['subscription_token']}"
            return VpnAccess(username, url)

    async def disable(self, username: str) -> None:
        async with httpx.AsyncClient(base_url=self.base, verify=self.settings.marzban_verify_ssl, timeout=20) as client:
            headers = {"Authorization": f"Bearer {await self._token(client)}"}
            response = await client.put(f"/api/user/{username}", headers=headers, json={"status": "disabled"})
            response.raise_for_status()


class ThreeXUiProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = self._normalize_base_url(self.settings.xui_base_url)
        self.inbound_ids = self._parse_inbound_ids(self.settings.xui_inbound_ids, self.settings.xui_inbound_id)
        self.inbound_id = self.inbound_ids[0] if self.inbound_ids else 0
        self.verify_ssl = self.settings.xui_verify_ssl

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        return value.rstrip("/") + "/"

    @staticmethod
    def _parse_inbound_ids(raw: str, fallback: int) -> list[int]:
        values: list[int] = []
        for item in (raw or "").replace(";", ",").split(","):
            item = item.strip()
            if item.isdigit():
                value = int(item)
                if value and value not in values:
                    values.append(value)
        if not values and fallback:
            values.append(int(fallback))
        return values

    def _require_config(self) -> None:
        if not self.base:
            raise RuntimeError("XUI_BASE_URL is not configured")
        if not self.inbound_ids:
            raise RuntimeError("Set XUI_INBOUND_IDS=1,2,3 or XUI_INBOUND_ID=1")
        if not self.settings.xui_api_token and not (self.settings.xui_username and self.settings.xui_password):
            raise RuntimeError("Set XUI_API_TOKEN or XUI_USERNAME/XUI_PASSWORD")

    async def _client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(base_url=self.base, verify=self.verify_ssl, timeout=25, follow_redirects=True)
        client.headers.update({
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })
        if self.settings.xui_api_token:
            client.headers.update({"Authorization": f"Bearer {self.settings.xui_api_token}"})
            return client
        response = await client.post("login", data={
            "username": self.settings.xui_username,
            "password": self.settings.xui_password,
        })
        self._raise_http(response, "login")
        return client

    @staticmethod
    def _raise_http(response: httpx.Response, action: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            text = response.text.strip().replace("\n", " ")[:240]
            if not text:
                text = response.reason_phrase or "empty response"
            attempts = response.extensions.get("joot_attempts")
            if attempts:
                text = f"{text}; attempts: {attempts}"
            raise RuntimeError(f"3x-ui HTTP {response.status_code} during {action}: {text}") from error

    @classmethod
    def _api_ok(cls, response: httpx.Response, action: str = "api request") -> dict:
        cls._raise_http(response, action)
        if not response.content:
            return {"success": True, "obj": None}
        try:
            data = response.json()
        except json.JSONDecodeError:
            text = response.text.strip()
            if not text:
                return {"success": True, "obj": None}
            raise RuntimeError(f"3x-ui returned non-json response: {text[:120]}")
        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(data.get("msg") or "3x-ui API error")
        return data if isinstance(data, dict) else {"success": True, "obj": data}

    @staticmethod
    def _parse_json(raw) -> dict:
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _sub_id(length: int = 20) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _expiry_ms(expires_at: datetime) -> int:
        value = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        return int(value.astimezone(timezone.utc).timestamp() * 1000)

    @staticmethod
    def _tg_id(username: str) -> int:
        raw = username.removeprefix("tg_") if username.startswith("tg_") else ""
        return int(raw) if raw.isdigit() else 0

    def _subscription_url(self, sub_id: str) -> str:
        template = self.settings.xui_sub_url_template.strip()
        if template:
            return template.replace("{sub_id}", quote(sub_id, safe=""))
        base = (self.settings.xui_sub_base_url or self.base).rstrip("/")
        path = self.settings.xui_sub_path or "/sub/"
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path = path + "/"
        return f"{base}{path}{quote(sub_id, safe='')}"

    async def _get_inbound(self, client: httpx.AsyncClient, inbound_id: int | None = None) -> dict:
        inbound_id = int(inbound_id or self.inbound_id)
        response = await client.get(f"panel/api/inbounds/get/{inbound_id}")
        data = self._api_ok(response, f"get inbound {inbound_id}")
        inbound = data.get("obj") or data
        if not inbound:
            raise RuntimeError(f"3x-ui inbound {inbound_id} not found")
        return inbound

    def _settings_clients(self, inbound: dict) -> tuple[dict, list]:
        settings = self._parse_json(inbound.get("settings"))
        clients = settings.get("clients")
        if not isinstance(clients, list):
            clients = []
        return settings, clients

    def _find_client_in_inbound(self, inbound: dict, username: str) -> dict | None:
        _, clients = self._settings_clients(inbound)
        for item in clients:
            if isinstance(item, dict) and item.get("email") == username:
                return item
        return None

    async def _find_first_existing(self, client: httpx.AsyncClient, username: str) -> dict | None:
        for inbound_id in self.inbound_ids:
            inbound = await self._get_inbound(client, inbound_id)
            existing = self._find_client_in_inbound(inbound, username)
            if existing:
                return existing
        return None

    def _flow_for_inbound(self, inbound: dict) -> str:
        protocol = str(inbound.get("protocol") or "").lower()
        stream = self._parse_json(inbound.get("streamSettings"))
        network = str(stream.get("network") or "tcp").lower()
        security = str(stream.get("security") or "").lower()
        if protocol == "vless" and security == "reality" and network in {"tcp", "raw"}:
            return self.settings.xui_client_flow
        return ""

    def _client_payload_for_inbound(
        self,
        inbound: dict,
        username: str,
        expires_at: datetime,
        traffic_gb: int,
        devices: int | None,
        sub_id: str,
        existing: dict | None = None,
    ) -> dict:
        protocol = str(inbound.get("protocol") or "").lower()
        payload = dict(existing or {})
        payload.update({
            "email": username,
            "limitIp": int(devices or self.settings.xui_client_limit_ip or 0),
            "totalGB": traffic_gb * 1024 ** 3 if traffic_gb else 0,
            "expiryTime": self._expiry_ms(expires_at),
            "enable": True,
            "tgId": self._tg_id(username),
            "subId": sub_id,
            "comment": "JOOT VPN",
            "reset": 0,
        })
        if protocol == "trojan":
            payload.pop("id", None)
            payload.pop("flow", None)
            payload["password"] = payload.get("password") or str(uuid.uuid4())
        else:
            payload.pop("password", None)
            payload["id"] = payload.get("id") or str(uuid.uuid4())
            flow = self._flow_for_inbound(inbound)
            if flow:
                payload["flow"] = flow
            else:
                payload.pop("flow", None)
        return payload

    async def _upsert_client_via_inbound_update(self, client: httpx.AsyncClient, inbound: dict, vpn_client: dict, inbound_id: int) -> httpx.Response:
        settings, clients = self._settings_clients(inbound)
        replaced = False
        for index, item in enumerate(clients):
            if isinstance(item, dict) and item.get("email") == vpn_client.get("email"):
                merged = dict(item)
                merged.update(vpn_client)
                for key in ("id", "password", "flow"):
                    if key not in vpn_client:
                        merged.pop(key, None)
                clients[index] = merged
                replaced = True
                break
        if not replaced:
            clients.append(dict(vpn_client))
        settings["clients"] = clients
        inbound_payload = dict(inbound)
        inbound_payload["settings"] = json.dumps(settings, ensure_ascii=False)
        for key in ("clientStats", "client_stats", "tag", "listen"):
            inbound_payload.pop(key, None)
        return await client.post(f"panel/api/inbounds/update/{inbound_id}", json=inbound_payload)

    async def create_or_extend(self, username: str, expires_at: datetime, traffic_gb: int, devices: int | None = None) -> VpnAccess:
        self._require_config()
        async with await self._client() as client:
            existing_any = await self._find_first_existing(client, username)
            sub_id = existing_any.get("subId") if existing_any and existing_any.get("subId") else self._sub_id()
            attempts = []
            for inbound_id in self.inbound_ids:
                inbound = await self._get_inbound(client, inbound_id)
                existing = self._find_client_in_inbound(inbound, username)
                vpn_client = self._client_payload_for_inbound(inbound, username, expires_at, traffic_gb, devices, sub_id, existing)
                response = await self._upsert_client_via_inbound_update(client, inbound, vpn_client, inbound_id)
                if response.status_code >= 400:
                    attempts.append(f"inbound {inbound_id}={response.status_code}")
                    response.extensions["joot_attempts"] = ", ".join(attempts)
                    self._raise_http(response, f"upsert client {username}")
                self._api_ok(response, f"upsert client {username} in inbound {inbound_id}")
                attempts.append(f"inbound {inbound_id}=ok")
            return VpnAccess(username=username, access_url=self._subscription_url(sub_id))

    async def disable(self, username: str) -> None:
        self._require_config()
        async with await self._client() as client:
            for inbound_id in self.inbound_ids:
                inbound = await self._get_inbound(client, inbound_id)
                existing = self._find_client_in_inbound(inbound, username)
                if not existing:
                    continue
                existing = dict(existing)
                existing["enable"] = False
                response = await self._upsert_client_via_inbound_update(client, inbound, existing, inbound_id)
                self._api_ok(response, f"disable client {username} in inbound {inbound_id}")


def get_vpn_provider():
    provider = get_settings().vpn_provider.lower().replace("-", "").replace("_", "")
    if provider == "marzban":
        return MarzbanProvider()
    if provider in {"3xui", "xui", "threexui"}:
        return ThreeXUiProvider()
    return DemoVpnProvider()
