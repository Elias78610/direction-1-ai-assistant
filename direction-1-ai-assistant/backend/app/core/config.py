from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量 / .env 读取配置，容器内由 docker compose 注入。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI 记账助手"
    log_level: str = "INFO"

    # 仅作占位；真实连接串由 .env 或环境变量 DATABASE_URL 注入
    database_url: str = (
        "mysql+pymysql://ledger:change_me_db@localhost:13306/ledger?charset=utf8mb4"
    )

    # 文本大模型（OpenAI 兼容接口）
    llm_api_key: str = ""
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # 小票 / 截图 OCR 使用的视觉模型
    vision_api_key: str = ""
    vision_api_base: str = ""
    vision_model: str = ""

    cors_origins: str = "http://localhost:8501"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
