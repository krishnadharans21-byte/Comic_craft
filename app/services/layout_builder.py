"""Bind story text and illustration results into ordered comic panels."""
from __future__ import annotations

from app.models import ComicPanel, ComicStory
from app.services.image_generator import ImageResult


def build_comic_layout(story: ComicStory, images: list[ImageResult]) -> list[ComicPanel]:
    if len(story.panels) != 5 or len(images) != 5:
        raise ValueError("A ComicCraft layout requires exactly five story panels and five images.")
    return [
        ComicPanel(
            panel_number=story_panel.panel_number,
            title=story_panel.title,
            scene_description=story_panel.scene_description,
            caption=story_panel.caption,
            narration=story_panel.narration,
            dialogue=story_panel.dialogue,
            image_url=image.url,
            image_generated=image.generated,
        )
        for story_panel, image in zip(story.panels, images, strict=True)
    ]
