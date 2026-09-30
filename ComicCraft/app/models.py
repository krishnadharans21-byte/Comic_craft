"""Typed request and response contracts shared by the UI, API, and AI services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
BodyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1200)]


class ComicRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    story_prompt: BodyText = Field(description="The central idea for the comic.")
    character_name: ShortText = Field(description="Name of the recurring main character.")
    setting: ShortText = Field(description="Where the story takes place.")
    tone: ShortText = Field(description="Mood or tone of the story.")
    art_style: ShortText = Field(description="Visual style requested for the illustrations.")


class OutlinePanel(BaseModel):
    panel_number: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=80)
    scene_description: str = Field(min_length=1, max_length=600)
    image_prompt: str = Field(min_length=1, max_length=1200)


class ComicOutline(BaseModel):
    panels: list[OutlinePanel] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def panels_are_numbered_in_order(self) -> "ComicOutline":
        if [panel.panel_number for panel in self.panels] != [1, 2, 3, 4, 5]:
            raise ValueError("Outline must contain panels numbered 1 through 5 in order.")
        return self


class DialogueLine(BaseModel):
    character: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=180)


class StoryPanel(BaseModel):
    panel_number: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=80)
    scene_description: str = Field(min_length=1, max_length=600)
    caption: str = Field(default="", max_length=160)
    narration: str = Field(min_length=1, max_length=500)
    dialogue: list[DialogueLine] = Field(default_factory=list, max_length=4)


class ComicStory(BaseModel):
    panels: list[StoryPanel] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def panels_are_numbered_in_order(self) -> "ComicStory":
        if [panel.panel_number for panel in self.panels] != [1, 2, 3, 4, 5]:
            raise ValueError("Story must contain panels numbered 1 through 5 in order.")
        return self


class ComicPanel(BaseModel):
    panel_number: int
    title: str
    scene_description: str
    caption: str = ""
    narration: str
    dialogue: list[DialogueLine]
    image_url: str
    image_generated: bool = False


class ComicDocument(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
    request: ComicRequest
    panels: list[ComicPanel] = Field(min_length=5, max_length=5)
    ai_mode: str = "demo"
    ai_notice: str = ""
    image_notice: str = ""
    pdf_filename: str | None = None


class ComicAPIResponse(BaseModel):
    comic_id: str
    title: str
    panels: list[ComicPanel]
    ai_mode: str
    ai_notice: str
    image_notice: str
    pdf_url: str
