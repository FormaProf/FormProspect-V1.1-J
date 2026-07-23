from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.networks import validate_email


_TRIMMED_FIELDS = {
    "company_name",
    "contact_name",
    "contact_first_name",
    "contact_last_name",
    "job_title",
    "email",
    "phone",
    "mobile",
    "website",
    "siren",
    "siret",
    "naf_code",
    "activity",
    "address",
    "postal_code",
    "city",
    "country",
    "pipeline_stage",
    "priority",
    "source",
    "next_action",
}
_PRIORITY_VALUES = {"basse", "normal", "haute", "urgente"}
_PHONE_ALLOWED = re.compile(r"^[0-9+().\-\s/]*$")
_NAF_CODE = re.compile(r"^\d{2}\.\d{2}[A-Z]$")


def _validate_optional_email(value: str) -> str:
    if not value:
        return ""
    try:
        _, normalized = validate_email(value)
    except ValueError as exc:
        raise ValueError("L'adresse e-mail n'est pas valide.") from exc
    return normalized


def _validate_optional_phone(value: str) -> str:
    if not value:
        return ""
    if not _PHONE_ALLOWED.fullmatch(value):
        raise ValueError("Le numéro de téléphone contient des caractères non autorisés.")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 6 or len(digits) > 15:
        raise ValueError("Le numéro de téléphone doit contenir entre 6 et 15 chiffres.")
    return value


def _validate_optional_website(value: str) -> str:
    if not value:
        return ""
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Le site web n'est pas valide.")
    return candidate


class ProspectBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(default="", max_length=200)
    contact_first_name: str = Field(default="", max_length=100)
    contact_last_name: str = Field(default="", max_length=100)
    job_title: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    website: str = Field(default="", max_length=500)
    siren: str = Field(default="", max_length=9)
    siret: str = Field(default="", max_length=14)
    naf_code: str = Field(default="", max_length=10)
    activity: str = Field(default="", max_length=200)
    workforce: int | None = Field(default=None, ge=0, le=10_000_000)
    annual_revenue: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    address: str = Field(default="", max_length=300)
    postal_code: str = Field(default="", max_length=20)
    city: str = Field(default="", max_length=120)
    country: str = Field(default="France", max_length=120)
    pipeline_stage: str = Field(default="nouveau", max_length=80)
    priority: str = Field(default="normal", max_length=20)
    source: str = Field(default="", max_length=120)
    next_action: str = Field(default="", max_length=300)
    next_action_at: datetime | None = None
    notes: str = Field(default="", max_length=20000)

    @field_validator(*_TRIMMED_FIELDS, mode="before")
    @classmethod
    def trim_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("company_name")
    @classmethod
    def company_name_required(cls, value: str) -> str:
        if not value:
            raise ValueError("Le nom de l'entreprise est obligatoire.")
        return value

    @field_validator("email")
    @classmethod
    def email_valid(cls, value: str) -> str:
        return _validate_optional_email(value)

    @field_validator("phone", "mobile")
    @classmethod
    def phone_valid(cls, value: str) -> str:
        return _validate_optional_phone(value)

    @field_validator("website")
    @classmethod
    def website_valid(cls, value: str) -> str:
        return _validate_optional_website(value)

    @field_validator("siren")
    @classmethod
    def siren_valid(cls, value: str) -> str:
        if value and (len(value) != 9 or not value.isdigit()):
            raise ValueError("Le SIREN doit contenir exactement 9 chiffres.")
        return value

    @field_validator("siret")
    @classmethod
    def siret_valid(cls, value: str) -> str:
        if value and (len(value) != 14 or not value.isdigit()):
            raise ValueError("Le SIRET doit contenir exactement 14 chiffres.")
        return value

    @field_validator("naf_code")
    @classmethod
    def naf_code_valid(cls, value: str) -> str:
        value = value.upper()
        if value and not _NAF_CODE.fullmatch(value):
            raise ValueError("Le code NAF doit respecter le format 00.00A.")
        return value

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, value: str) -> str:
        value = value.lower()
        if value not in _PRIORITY_VALUES:
            raise ValueError("La priorité doit être basse, normal, haute ou urgente.")
        return value


class ProspectCreate(ProspectBase):
    owner_user_id: uuid.UUID | None = None


class ProspectUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_first_name: str | None = Field(default=None, max_length=100)
    contact_last_name: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    mobile: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    siren: str | None = Field(default=None, max_length=9)
    siret: str | None = Field(default=None, max_length=14)
    naf_code: str | None = Field(default=None, max_length=10)
    activity: str | None = Field(default=None, max_length=200)
    workforce: int | None = Field(default=None, ge=0, le=10_000_000)
    annual_revenue: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    address: str | None = Field(default=None, max_length=300)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    pipeline_stage: str | None = Field(default=None, max_length=80)
    priority: str | None = Field(default=None, max_length=20)
    source: str | None = Field(default=None, max_length=120)
    next_action: str | None = Field(default=None, max_length=300)
    next_action_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=20000)
    owner_user_id: uuid.UUID | None = None

    @field_validator(*_TRIMMED_FIELDS, mode="before")
    @classmethod
    def trim_optional_strings(cls, value: object) -> object:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("company_name")
    @classmethod
    def updated_company_name_required(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Le nom de l'entreprise est obligatoire.")
        return value

    @field_validator("email")
    @classmethod
    def optional_email_valid(cls, value: str | None) -> str | None:
        return None if value is None else _validate_optional_email(value)

    @field_validator("phone", "mobile")
    @classmethod
    def optional_phone_valid(cls, value: str | None) -> str | None:
        return None if value is None else _validate_optional_phone(value)

    @field_validator("website")
    @classmethod
    def optional_website_valid(cls, value: str | None) -> str | None:
        return None if value is None else _validate_optional_website(value)

    @field_validator("siren")
    @classmethod
    def optional_siren_valid(cls, value: str | None) -> str | None:
        if value is not None and value and (len(value) != 9 or not value.isdigit()):
            raise ValueError("Le SIREN doit contenir exactement 9 chiffres.")
        return value

    @field_validator("siret")
    @classmethod
    def optional_siret_valid(cls, value: str | None) -> str | None:
        if value is not None and value and (len(value) != 14 or not value.isdigit()):
            raise ValueError("Le SIRET doit contenir exactement 14 chiffres.")
        return value

    @field_validator("naf_code")
    @classmethod
    def optional_naf_code_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if value and not _NAF_CODE.fullmatch(value):
            raise ValueError("Le code NAF doit respecter le format 00.00A.")
        return value

    @field_validator("priority")
    @classmethod
    def optional_priority_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.lower()
        if value not in _PRIORITY_VALUES:
            raise ValueError("La priorité doit être basse, normal, haute ou urgente.")
        return value


class ProspectResponse(ProspectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    owner_user_id: uuid.UUID
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
