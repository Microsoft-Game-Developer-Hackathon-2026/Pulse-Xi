"""Observational checkpoint metadata; never part of deterministic snapshots."""
from datetime import datetime
from pydantic import Field, field_validator
from .models import CheckpointView, Model, MutationResult


class CheckpointMetadata(Model):
    created_at_utc: str | None = Field(max_length=40, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')

    @field_validator('created_at_utc')
    @classmethod
    def valid_utc(cls, value):
        if value is not None:
            datetime.fromisoformat(value)
        return value


class StoredCheckpoint(CheckpointView, CheckpointMetadata):
    pass


class CommandReceipt(MutationResult):
    checkpoint_created_at_utc: str | None = None
