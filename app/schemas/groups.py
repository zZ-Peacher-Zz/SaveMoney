from pydantic import BaseModel, Field, field_validator


class GroupPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Group name cannot be blank")
        return value.strip()


class InvitePayload(BaseModel):
    username: str = Field(min_length=3, max_length=50)
