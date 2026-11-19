"""Journey preferences: the rider's cabin choices. They never change the price."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Mode(str, Enum):
    QUIET = "quiet"      # minimal conversation, music off, phone-call friendly
    WORK = "work"        # quiet cabin, charging ready, smooth driving for laptops
    RELAX = "relax"      # soft music, cooler cabin
    FAMILY = "family"    # extra time at pickup for loading, bags first


class Temperature(str, Enum):
    COOL = "cool"
    NORMAL = "normal"
    WARM = "warm"


class Music(str, Enum):
    OFF = "off"
    SOFT = "soft"
    GUEST_CHOICE = "guest_choice"   # rider connects their own phone


class Conversation(str, Enum):
    MINIMAL = "minimal"
    NORMAL = "normal"


class ChildSeat(str, Enum):
    NONE = "none"
    INFANT = "infant"          # rear-facing
    TODDLER = "toddler"        # forward-facing with harness
    BOOSTER = "booster"


# What each mode pre-selects in the form; the rider can still change any field.
MODE_DEFAULTS = {
    Mode.QUIET: {"temperature": Temperature.NORMAL, "music": Music.OFF, "conversation": Conversation.MINIMAL},
    Mode.WORK: {"temperature": Temperature.COOL, "music": Music.OFF, "conversation": Conversation.MINIMAL},
    Mode.RELAX: {"temperature": Temperature.COOL, "music": Music.SOFT, "conversation": Conversation.MINIMAL},
    Mode.FAMILY: {"temperature": Temperature.NORMAL, "music": Music.SOFT, "conversation": Conversation.NORMAL},
}


class JourneyPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    mode: Mode = Mode.QUIET
    temperature: Temperature = Temperature.NORMAL
    music: Music = Music.OFF
    conversation: Conversation = Conversation.MINIMAL
    still_water: bool = True
    child_seat: ChildSeat = ChildSeat.NONE
    child_details: Optional[str] = Field(default=None, max_length=120)   # e.g. "2 years, 28 lb"
    requests: Optional[str] = Field(default=None, max_length=500)

    @field_validator("requests", "child_details")
    @classmethod
    def _clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None

    @property
    def wants_child_seat(self) -> bool:
        return self.child_seat != ChildSeat.NONE.value

    def checklist(self) -> list[str]:
        """Plain-language pre-pickup checklist for the owner."""
        items = [
            {"cool": "Cabin cool (about 68°F)", "normal": "Cabin comfortable (about 71°F)",
             "warm": "Cabin warm (about 74°F)"}[self.temperature],
            {"off": "Music off", "soft": "Soft instrumental music, low",
             "guest_choice": "Bluetooth ready for the guest's phone"}[self.music],
            {"minimal": "Keep conversation minimal", "normal": "Normal conversation welcome"}[self.conversation],
        ]
        if self.still_water:
            items.append("Still water in the rear")
        if self.mode == Mode.WORK:
            items.append("Charging cables out; smooth, steady driving")
        if self.mode == Mode.FAMILY:
            items.append("Allow extra loading time; bags first")
        if self.wants_child_seat:
            kind = {"infant": "rear-facing infant", "toddler": "forward-facing harness",
                    "booster": "booster"}[self.child_seat]
            items.append(f"Child seat: {kind}" + (f" ({self.child_details})" if self.child_details else "")
                         + " — fit and check before pickup")
        if self.requests:
            items.append("Request: " + self.requests)
        return items
