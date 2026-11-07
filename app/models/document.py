"""MongoDB records with explicit unique keys and API-compatible integer IDs."""
from dataclasses import asdict, fields
from datetime import date
from typing import ClassVar


class Document:
    collection: ClassVar[str]
    key_fields: ClassVar[tuple]
    unique_fields: ClassVar[tuple] = ()

    def identity_filter(self):
        return {name: getattr(self, name) for name in self.key_fields}

    def to_document(self):
        return {key: value.isoformat() if isinstance(value, date) else value
                for key, value in asdict(self).items()}

    @classmethod
    def from_document(cls, value):
        data = {f.name: value[f.name] for f in fields(cls) if f.name in value}
        if "expense_date" in data and isinstance(data["expense_date"], str):
            data["expense_date"] = date.fromisoformat(data["expense_date"])
        return cls(**data)
