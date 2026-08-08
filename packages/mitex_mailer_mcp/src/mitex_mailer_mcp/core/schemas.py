from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class EmailData(BaseModel):
    subject: str
    sender: str
    body: str
    date: datetime
    attachments: list[str]
    uid: str

    @classmethod
    def from_email(cls, email: dict[str, Any]):
        return cls(
            subject=email["subject"],
            sender=email["from"],
            body=email["body"],
            date=email["date"],
            attachments=email["attachments"],
            uid=email["uid"],
        )


class EmailPageResponse(BaseModel):
    page: int
    page_size: int
    before: datetime | None
    since: datetime | None
    subject: str | None
    body: str | None
    text: str | None
    emails: list[EmailData]
    total: int


class EmailServer(BaseModel):
    user_name: str
    password: str
    host: str
    port: int
    use_ssl: bool = True  # Usually port 465
    start_ssl: bool = False  # Usually port 587
    fullname: Optional[str] = None

    def masked(self) -> "EmailServer":
        return self.model_copy(update={"password": "********"})


class AccountAttributes(BaseModel):
    account_name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def update_updated_at(self) -> "AccountAttributes":
        """Update updated_at field."""
        # must disable validation to avoid infinite loop
        self.model_config["validate_assignment"] = False

        # update updated_at field
        self.updated_at = datetime.now()

        # enable validation again
        self.model_config["validate_assignment"] = True
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AccountAttributes):
            return NotImplemented
        return self.model_dump(
            exclude={"created_at", "updated_at"}
        ) == other.model_dump(exclude={"created_at", "updated_at"})

    def masked(self) -> "AccountAttributes":
        return self.model_copy()


class EmailSettings(AccountAttributes):
    full_name: str
    email_address: str
    incoming: EmailServer
    outgoing: EmailServer

    @classmethod
    def from_params(
        cls,
        *,
        account_name: str,
        full_name: str,
        email_address: str,
        user_name: str,
        password: str,
        imap_host: str,
        smtp_host: str,
        imap_user_name: str | None = None,
        imap_password: str | None = None,
        imap_port: int = 993,
        imap_ssl: bool = True,
        smtp_port: int = 465,
        smtp_ssl: bool = True,
        smtp_start_ssl: bool = False,
        smtp_user_name: str | None = None,
        smtp_password: str | None = None,
    ) -> "EmailSettings":
        return cls(
            account_name=account_name,
            full_name=full_name,
            email_address=email_address,
            incoming=EmailServer(
                user_name=imap_user_name or user_name,
                password=imap_password or password,
                host=imap_host,
                port=imap_port,
                use_ssl=imap_ssl,
            ),
            outgoing=EmailServer(
                user_name=smtp_user_name or user_name,
                password=smtp_password or password,
                host=smtp_host,
                port=smtp_port,
                use_ssl=smtp_ssl,
                start_ssl=smtp_start_ssl,
            ),
        )

    def masked(self) -> "EmailSettings":
        return self.model_copy(
            update={
                "incoming": self.incoming.masked(),
                "outgoing": self.outgoing.masked(),
            }
        )


class ProviderSettings(AccountAttributes):
    provider_name: str
    api_key: str

    def masked(self) -> AccountAttributes:
        return self.model_copy(update={"api_key": "********"})


class EmailTemplate(BaseModel):
    name: str
    subject: str
    body: str
    variables: list[str] = []


class AutoReplyRule(BaseModel):
    name: str
    conditions: dict[
        str, Any
    ]  # e.g., {"from_address": "specific@email.com", "subject_contains": "urgent"}
    reply_subject: str
    reply_body: str
    enabled: bool = True
    mark_as_read: bool = True
    template_name: Optional[str] = None  # If using a template
    variables: Optional[dict[str, str]] = None  # Template variables
