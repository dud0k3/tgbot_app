from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    app_url: str = "http://localhost:8000"
    admin_ids: str = ""
    database_url: str = "sqlite:///./data/joot.db"
    bot_mode: str = "polling"
    dev_mode: bool = False
    vpn_provider: str = "demo"
    marzban_url: str = ""
    marzban_username: str = ""
    marzban_password: str = ""
    marzban_verify_ssl: bool = True
    xui_base_url: str = ""
    xui_username: str = ""
    xui_password: str = ""
    xui_api_token: str = ""
    xui_inbound_id: int = 0
    xui_inbound_ids: str = ""
    xui_verify_ssl: bool = True
    xui_sub_url_template: str = ""
    xui_sub_base_url: str = ""
    xui_sub_path: str = "/sub/"
    xui_client_flow: str = "xtls-rprx-vision"
    xui_client_limit_ip: int = 3
    support_username: str = ""
    trial_enabled: bool = False
    trial_days: int = 3
    trial_traffic_gb: int = 5
    default_subscription_days: int = 30
    default_subscription_traffic_gb: int = 0
    default_subscription_devices: int = 3
    subscription_protocols: str = "VLESS Reality 443,Trojan Reality,VLESS XHTTP,VLESS TLS"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admins(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    @property
    def protocols(self) -> list[str]:
        return [x.strip() for x in self.subscription_protocols.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
