"""Places to explore: rooms through doorways, a panorama with animals, a map tour."""

from __future__ import annotations

import copy
import re
from typing import Any

import pytest
from chronicle.core.story import panorama, rooms, tour
from chronicle.core.watercolor.svg.parse import parse
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Assets, render

HOG = {
    "file": "art/hog.webp",
    "width": 600,
    "height": 400,
    "anchors": {},
    "labels": [],
    "layers": [
        {
            "name": "hog--leg",
            "file": "art/hog--hog--leg.webp",
            "box": [100, 200, 40, 150],
            "rig": "hog",
            "part": {"role": "leg", "name": "leg", "amp": 20, "phase": 0},
            "pivot": [120, 210],
        },
        {
            "name": "hog--body",
            "file": "art/hog--hog--body.webp",
            "box": [50, 100, 400, 200],
            "rig": "hog",
            "part": {"role": "static", "name": "body", "phase": 0},
        },
    ],
    "rigs": {"hog": {"gait": "root", "bob": 3, "speed": 30, "stride": 60, "foot": [250, 350]}},
}
MANIFEST: dict[str, Any] = {
    "front": {
        "file": "art/front.webp",
        "width": 1600,
        "height": 900,
        "anchors": {"door": [800, 560], "lamp": [900, 490]},
        "layers": [],
        "labels": [],
    },
    "hall": {
        "file": "art/hall.webp",
        "width": 1600,
        "height": 900,
        "anchors": {"out": [800, 820]},
        "layers": [],
        "labels": [],
    },
    "marsh": {
        "file": "art/marsh.webp",
        "width": 3200,
        "height": 1000,
        "anchors": {},
        "labels": [],
        "layers": [
            {"name": "tide", "file": "art/marsh--tide.webp", "box": [1300, 640, 1100, 360]},
            {"name": "grass", "file": "art/marsh--grass.webp", "box": [0, 900, 1300, 100]},
        ],
    },
    "map": {
        "file": "art/map.webp",
        "width": 1600,
        "height": 1200,
        "anchors": {"dock": [1250, 200], "house": [930, 360]},
        "layers": [],
        "labels": [],
    },
    "hog": HOG,
}
ROOMS: dict[str, Any] = {
    "type": "rooms",
    "id": "house",
    "rooms": [
        {
            "id": "front",
            "art": "front",
            "short": "Front",
            "title": "The front",
            "text": "Pink stucco.",
            "details": [{"at": "lamp", "title": "The lamp", "text": "Lit every night."}],
            "exits": [{"at": "door", "to": "hall", "label": "Step inside", "arrow": "up"}],
        },
        {
            "id": "hall",
            "art": "hall",
            "short": "Hall",
            "title": "The hall",
            "exits": [{"at": "out", "to": "front", "label": "Back outside", "arrow": "down"}],
        },
    ],
}
PANORAMA: dict[str, Any] = {
    "type": "panorama",
    "id": "marsh-view",
    "art": "marsh",
    "intro": "Pick an animal.",
    "journal": True,
    "front": ["grass"],
    "zones": [{"label": "Marsh", "from": 0, "to": 1300, "text": "Cordgrass."}],
    "tide": {"layer": "tide", "start": 0.2, "notes": [{"from": 0, "text": "Low."}]},
    "animals": [
        {
            "id": "hog",
            "art": "hog",
            "name": "Marsh hog",
            "latin": "Sus scrofa",
            "fact": "Roots for crab.",
            "at": [400, 960],
            "scale": 0.5,
            "range": [200, 700],
            "tide": "low",
        }
    ],
}


def _with(story: dict[str, Any], *blocks: dict[str, Any]) -> dict[str, Any]:
    changed = copy.deepcopy(story)
    changed["art"] = {key: {"svg": f"art/{key}.svg"} for key in MANIFEST}
    changed["chapters"][0]["blocks"][0:0] = [copy.deepcopy(b) for b in blocks]
    return changed


def _page(story: dict[str, Any], facts: dict[str, Any], assets: Assets, *blocks: Any) -> str:
    return render(_with(story, *blocks), facts, MANIFEST, assets).fragment


# ---------------------------------------------------------------------- rooms
def test_rooms_are_tab_panels_with_dots_and_doorways_that_link_without_scripts(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = _page(story, facts, assets, ROOMS)
    assert page.count('role="tab"') == 2 and page.count('role="tabpanel"') == 2
    assert 'id="house-tab-0" aria-controls="house-room-0" aria-selected="true" tabindex="0"' in page
    # The doorway links to the room it opens, at its point in the painting (800 of 1600).
    door = re.search(r'<a class="rm-exit"[^>]*>', page)
    assert door is not None
    assert 'href="#house-room-1"' in door.group(0) and 'data-to="1"' in door.group(0)
    assert "left:50.00%;top:62.22%" in door.group(0)
    assert 'aria-label="Detail 1: The lamp" style="left:56.25%;top:54.44%"' in page
    assert 'href="#house-d0-0"' in page and 'id="house-d0-0"' in page
    assert page.count('class="plate inset"') == 2
    assert "js/35-rooms.js" in page and "css/18-rooms.css" in page


def test_rooms_check_names_bad_rooms_details_and_doorways(story: dict[str, Any]) -> None:
    bad = copy.deepcopy(ROOMS)
    bad["rooms"][0]["exits"].append({"at": "door", "to": "attic", "label": "Up"})
    bad["rooms"][0]["exits"].append({"at": [1, 2], "to": "hall", "label": "Over", "arrow": "x"})
    bad["rooms"][0]["details"].append({"at": "chimney", "text": "no title"})
    bad["rooms"].append(copy.deepcopy(ROOMS["rooms"][1]))
    bad["rooms"][1]["focus"] = "left"
    report = Report()
    rooms.check(_with(story, bad), {"front": {"door", "lamp"}, "hall": {"out"}}, report)
    where = "chapters[0].blocks[0].rooms"
    assert report.errors == [
        f"{where}[0].details[1].at 'chimney' is no data-anchor in the drawing",
        f"{where}[0].details[1].title is required",
        f"{where}[0].exits[1].to must name another room of this block",
        f"{where}[0].exits[2].arrow must be one of up, down, left, right",
        f"{where}[1].id 'hall' must be unique, lowercase letters and -",
        f"{where}[1].focus must be between 0 and 1",
        f"{where}[2].id 'hall' must be unique, lowercase letters and -",
    ]


# ------------------------------------------------------------------- panorama
def test_a_panorama_places_animals_by_their_foot_and_layers_by_role(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = _page(story, facts, assets, PANORAMA)
    assert 'class="pa-world" style="width:3200px;height:1000px"' in page
    animal = re.search(r'<button type="button" class="pa-animal"[^>]*>', page)
    assert animal is not None
    # The rig box spans x 50 to 450 and y 100 to 350; its foot (250, 350) sits 200 and 250
    # into it, so at scale 0.5 the button's corner is 100 and 125 short of the point.
    assert "left:300.0px;top:835.0px;width:200.0px;height:125.0px;z-index:960" in animal.group(0)
    assert 'data-foot="100.0 125.0"' in animal.group(0) and 'data-tide="low"' in animal.group(0)
    # Speed and stride default to the rig's, scaled with the animal.
    assert 'data-speed="15.0"' in animal.group(0) and 'data-stride="30.0"' in animal.group(0)
    assert page.count('class="part"') == 2
    assert 'class="pa-layer pa-l-tide mult"' in page
    assert re.search(r'class="pa-layer pa-l-front mult"[^>]*z-index:1010', page)
    assert '<input type="range" id="marsh-view-tide" class="pa-tide-range"' in page
    assert 'value="20"' in page and '<label for="marsh-view-tide"' in page
    assert '"journal":"chronicle-journal:keystone"' in page.replace(" ", "")
    assert "<b>Marsh hog</b> <i>Sus scrofa</i>: Roots for crab." in page
    for part in ("js/33-rigs.js", "js/34-panorama.js", "css/17-panorama.css"):
        assert part in page


def test_panorama_check_names_rigs_layers_and_behaviors(story: dict[str, Any]) -> None:
    bad = copy.deepcopy(PANORAMA)
    bad["tide"]["layer"] = "flood"
    bad["front"] = ["reeds"]
    bad["journal"] = "Field Journal"
    bad["animals"][0].update({"behavior": "gallop", "rig": "boar", "tide": "spring"})
    bad["animals"].append({"id": "gull", "art": "map", "name": "Gull", "at": [1, 1]})
    bad["animals"].append(
        {"id": "eel", "art": "hog", "name": "Eel", "at": "creek", "scale": 0, "speed": "fast"}
    )
    bad["zones"].append({"label": "Beach", "from": "dunes", "to": 3200})
    bad["tide"].update({"start": "low", "shift": [1], "watch": [[0]], "notes": ["Low."]})
    bad["view"] = {"desktop": "tall"}
    hog = parse(
        '<svg viewBox="0 0 600 400"><g data-rig="hog"><g data-part="body">'
        '<rect width="90" height="40"/></g></g></svg>'
    )
    marsh = parse(
        '<svg viewBox="0 0 3200 1000"><rect width="9" height="9"/><g data-layer="tide">'
        '<rect width="9" height="9"/></g></svg>'
    )
    flat = parse('<svg viewBox="0 0 1600 1200"><rect width="9" height="9"/></svg>')
    report = Report()
    panorama.check(_with(story, bad), {"hog": hog, "marsh": marsh, "map": flat}, report)
    where = "chapters[0].blocks[0]"
    assert report.errors == [
        f"{where}.animals[0].rig 'boar' is no data-rig in art 'hog'",
        f"{where}.animals[0].behavior must be one of "
        "wander, scuttle, swim, crawl, glide, arc, hop, stay",
        f"{where}.animals[0].tide must be low or high",
        f"{where}.animals[1]: art 'map' has 0 rigs; name one in rig",
        f"{where}.animals[2].at must be [x, y] in painting pixels",
        f"{where}.animals[2].scale must be a number above 0",
        f"{where}.animals[2].speed must be a number",
        f"{where}.zones[1]: from and to are pixels, to past from",
        f"{where}.tide names layer 'flood'; draw a data-layer",
        f"{where}.tide.start must be between 0 and 1",
        f"{where}.tide.shift must be [x, y] in painting pixels",
        f"{where}.tide.watch must be [from, to] stretches",
        f"{where}.tide.notes are {{from: 0 to 1, text}} objects",
        f"{where}.view takes desktop and phone heights and a start, numbers",
        f"{where}.front names layer 'reeds'; draw a data-layer",
        f"{where}.journal must be true or a key of lowercase letters and -",
    ]


# ----------------------------------------------------------------------- tour
TOUR: dict[str, Any] = {
    "type": "tour",
    "id": "isle",
    "art": "map",
    "title": "The isle",
    "stops": [
        {"id": "dock", "title": "The dock", "short": "Dock", "at": "dock", "intro": "Land here."},
        {
            "id": "house",
            "title": "The house",
            "at": "house",
            "chapter": "ch1",
            "scene": ROOMS,
        },
    ],
    "pins": [{"title": "The well", "at": [640, 320], "text": "Brackish now."}],
}


def test_a_tour_routes_its_stops_and_opens_their_scenes(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    changed = _with(story, TOUR)
    changed["chapters"][0]["id"] = "ch1"
    page = render(changed, facts, MANIFEST, assets).fragment
    assert 'class="tr-route" d="M1250 200 L930 360"' in page
    stop = re.search(r'<a class="tr-stop lbl-left"[^>]*>', page)
    assert stop is not None and 'href="#isle-stop-0"' in stop.group(0)
    assert 'aria-label="Stop 1: The dock"' in stop.group(0)
    assert 'aria-label="Map of The isle with 2 stops"' in page
    assert '<p class="tr-kicker">Stop 2 of 2</p>' in page
    # The house stop holds the rooms block, and its foot links back, on, and to its chapter.
    assert page.count('class="fig rooms wide"') == 1 and 'id="house-room-1"' in page
    assert 'href="#isle-stop-1" data-stop="1">Next stop: The house ›</a>' in page
    assert 'class="tr-btn ghost tr-read" href="#ch1"' in page
    assert '<button type="button" class="tr-pin" data-pin="0" aria-label="The well"' in page
    assert "<dt>The well</dt>" in page
    assert '"key":"chronicle-tour:keystone"' in page.replace(" ", "")
    assert "js/36-tour.js" in page and "js/35-rooms.js" in page


def test_tour_check_names_stops_scenes_and_pins(story: dict[str, Any]) -> None:
    bad = copy.deepcopy(TOUR)
    bad["stops"][0].update({"at": "pier", "chapter": "nowhere", "scene": {"type": "chart"}})
    bad["stops"][1]["scene"]["rooms"][0]["exits"][0]["to"] = "cellar"
    bad["pins"].append({"at": [1, 2]})
    changed = _with(story, bad)
    changed["chapters"][0]["id"] = "ch1"
    report = Report()
    tour.check(changed, {"map": {"dock", "house"}}, report)
    rooms.check(changed, {"front": {"door", "lamp"}, "hall": {"out"}}, report)
    where = "chapters[0].blocks[0]"
    assert report.errors == [
        f"{where}.stops[0].at 'pier' is no data-anchor in the drawing",
        f"{where}.stops[0].chapter 'nowhere' is no chapter id",
        f"{where}.stops[0].scene must be a block of type plate, rooms, panorama",
        f"{where}.pins[1] needs a title, at and text",
        f"{where}.stops[1].scene.rooms[0].exits[0].to must name another room of this block",
    ]


@pytest.mark.parametrize("kind", ["rooms", "panorama", "tour"])
def test_pages_without_places_ship_none_of_their_parts(
    kind: str, story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(story, facts, {}, assets).fragment
    names = {"rooms": "35-rooms", "panorama": "34-panorama", "tour": "36-tour"}
    assert names[kind] not in page and "33-rigs" not in page
