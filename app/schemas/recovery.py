from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailPayload(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize(cls, value):
        return str(value).lower()


class SetRecoveryEmail(EmailPayload):
    password: str = Field(min_length=8, max_length=128)


class TokenPayload(BaseModel):
    token: str = Field(min_length=20, max_length=128)


class ResetPassword(TokenPayload):
    password: str = Field(min_length=8, max_length=128)
