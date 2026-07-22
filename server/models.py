from typing import Literal, Optional

from pydantic import BaseModel, Field

field_source_text = Field(max_length=5000)
field_source_lang = Field(max_length=50)
field_target_lang = Field(max_length=50)
field_source_instructions = Field(default=None, optional=True, max_length=5000) # type: ignore
field_source_media = Field(default=None, optional=True, max_length=1500000) # type: ignore

class TranslateReq(BaseModel):
    text: str = field_source_text 
    source_lang: str = field_source_lang
    target_lang: str = field_target_lang
    source_media: Optional[str] = field_source_media
    source_instructions: Optional[str] = field_source_instructions

class Rule(BaseModel):
    value: str = Field(max_length=500)

class VerifyReq(BaseModel):
    source_text: str = field_source_text
    translations: list[str] = Field(max_length=5000)
    verification_rules: list[Rule]
    source_media: Optional[str] = field_source_media

class TranslationEntry(BaseModel):
    model: str
    translation: str
    verified: Optional[list[bool]] = None

class SubmissionReq(BaseModel):
    # Restrict to an appropriate character limit, e.g., 5000 chars
    source_text: str = Field(max_length=5000)
    source_lang: str = Field(max_length=50)
    target_lang: str = Field(max_length=50)
    verification_rules: list[Rule]
    translations: list[TranslationEntry]
    
    # source_media is base64-encoded (1500000 chars for ~1MB of binary data).
    source_media: Optional[str] = field_source_media
    source_instructions: Optional[str] = field_source_instructions

class ScoreReq(BaseModel):
    action: str  # "return" | "accept" | "pending"
    comment: Optional[str] = None


class ProfileAffiliationReq(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ror_id: Optional[str] = Field(
        default=None,
        max_length=100,
        pattern=r"^https://ror\.org/0[0-9a-z]{8}$",
    )
    kind: Literal["ror", "independent", "other"]


class ProfileReq(BaseModel):
    name: str = Field(max_length=50)
    affiliation: str = Field(max_length=200)
    affiliation_ror_id: Optional[str] = Field(
        default=None,
        max_length=100,
        pattern=r"^https://ror\.org/0[0-9a-z]{8}$",
    )
    affiliations: Optional[list[ProfileAffiliationReq]] = Field(
        default=None,
        min_length=1,
        max_length=5,
    )
    email: str = Field(max_length=100)
    credit_consent: bool
    notification_consent: bool

class RecoverLinkReq(BaseModel):
    email: str = Field(max_length=100)

class CommentReq(BaseModel):
    comment: str = Field(max_length=1000)

class QuotaReq(BaseModel):
    delta: int

class RolesReq(BaseModel):
    roles: list[str]

class ReviewScopeReq(BaseModel):
    review_langs: list[str]

class NotificationActionReq(BaseModel):
    action: str  # "view" | "clear"


class AffiliationLocationUpdateReq(BaseModel):
    affiliation_name: str = Field(min_length=1, max_length=200)
    address: str = Field(default="", max_length=500)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    logo_domain: str = Field(default="", max_length=200)
    website: str = Field(default="", max_length=500)
    precision: Literal["city", "exact"] = "city"
    status: Literal["pending", "approved"] = "pending"


class AffiliationLocationGeocodeReq(BaseModel):
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)
    country: str = Field(default="", max_length=100)
