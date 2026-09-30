"""Deterministic, key-free story content so ComicCraft is always demonstrable."""
from __future__ import annotations

from app.models import ComicOutline, ComicRequest, ComicStory


BEATS = [
    ("A Curious Beginning", "setup"),
    ("A Trouble Appears", "conflict"),
    ("A Clever Plan", "development"),
    ("The Big Moment", "climax"),
    ("A Bright New Day", "resolution"),
]


def generate_demo_outline(request: ComicRequest) -> ComicOutline:
    name = request.character_name
    setting = request.setting
    idea = request.story_prompt.rstrip(".!? ")
    scenes = [
        f"{name} arrives in {setting}, where a small clue connected to {idea} catches their eye.",
        f"The clue reveals a problem in {setting}; {name} realizes there is little time to help.",
        f"{name} studies the scene, gathers a useful object, and tries a thoughtful plan.",
        f"At the story's turning point, {name} faces the challenge directly and makes a brave choice.",
        f"The problem is resolved; {name} and the people of {setting} celebrate what they learned.",
    ]
    panels = []
    for number, ((title, beat), scene) in enumerate(zip(BEATS, scenes, strict=True), start=1):
        image_prompt = (
            f"{request.art_style} illustration, {beat} moment in {request.tone} tone; "
            f"{name}, the same recurring main character, is clearly visible in {setting}. {scene} "
            "Keep the character's appearance consistent across the five panels."
        )
        panels.append(
            {
                "panel_number": number,
                "title": title,
                "scene_description": scene,
                "image_prompt": image_prompt,
            }
        )
    return ComicOutline(panels=panels)


def generate_demo_story(outline: ComicOutline, request: ComicRequest) -> ComicStory:
    name = request.character_name
    idea = request.story_prompt.rstrip(".!? ")
    narration = [
        f"{name} had come to {request.setting} with one thought in mind: {idea}.",
        f"Then a sudden snag threatened to stop everything. {name} took a breath and looked closer.",
        f"A simple idea began to take shape. {name} gathered the right clues and set the plan in motion.",
        f"There was no time left to hesitate. {name} made one bold move—and the whole scene changed.",
        f"By sunset, the trouble had passed. {name} left {request.setting} proud, hopeful, and ready for a new adventure.",
    ]
    captions = [
        "Every adventure starts with a spark.",
        "But every spark brings a little surprise.",
        "A clever idea can change the story.",
        "This is the moment that matters.",
        "And that's how a new chapter begins.",
    ]
    dialogue = [
        ("", "Let's see where this leads!"),
        ("", "We have to do something!"),
        ("", "I think I know how."),
        ("", "Now! Together!"),
        ("", "We did it—and learned a lot."),
    ]
    panels = []
    for index, source in enumerate(outline.panels):
        speaker = name if index != 1 else "Friend"
        line = dialogue[index][1]
        panels.append(
            {
                "panel_number": source.panel_number,
                "title": source.title,
                "scene_description": source.scene_description,
                "caption": captions[index],
                "narration": narration[index],
                "dialogue": [{"character": speaker, "text": line}],
            }
        )
    return ComicStory(panels=panels)
