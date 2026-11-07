from pydantic import BaseModel, EmailStr, Field, field_validator


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class Registration(Credentials):
    email: EmailStr | None = Field(default=None, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower() if value else None
