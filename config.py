from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    WHATSAPP_VERIFY_TOKEN: str

    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    OPENAI_CHAT_MODEL: str = "gpt-oss-120b"

    MONGODB_URL: str
    MONGODB_DB: str = "cyne-crm"

    OWNER_API_KEY: str


settings = Settings()
