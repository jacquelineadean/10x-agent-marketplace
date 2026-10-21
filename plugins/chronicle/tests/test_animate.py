"""Diagram and scene animations, the GIF and video writers, and `chronicle animate`."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from chronicle.connectors.browser import shoot
from chronicle.connectors.files import store
from chronicle.connectors.video import encode
from chronicle.core.motion import gif, render
from chronicle.entrypoints.cli.main import main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
CSS = store.asset_parts("motion", ".css") + store.asset("css/40-drawn.css")
DRAWING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120">
  <g id="a"><rect class="box" x="0" y="20" width="120" height="80"/>
    <text x="60" y="64"><tspan id="num">{{ci.median_minutes}}</tspan></text></g>
  <path id="hop" class="line" d="M120 60 L280 60"/>
  <rect id="b" class="box accent" x="280" y="20" width="120" height="80"/>
</svg>"""


def _diagram(steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": "diagram",
        "meta": {"title": "Hop", "description": "A packet hops from a to b."},
        "diagram": {"svg": "drawing.svg"},
        "steps": steps,
    }


def _example(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (EXAMPLES / name / "animation.json").read_text(encoding="utf-8")
    )
    return data


FACTS = {"ci": {"median_minutes": {"value": 14, "unit": "min"}}}


# ---------------------------------------------------------------------- diagram
def test_diagram_steps_must_name_parts_of_the_drawing() -> None:
    anim = _diagram([{"show": ["c"]}, {"flow": ["b"]}, {"focus": ["num"]}])
    report = render.check(anim, FACTS, store.fonts(), render.Sources(drawing=DRAWING))
    text = " ".join(report.errors)
    assert "steps[0].show names 'c'; the drawing has no such id" in text
    assert "flow runs along a path, line or polyline" in text
    assert "sits inside text" in text


def test_the_sanitizer_still_guards_a_diagram() -> None:
    bad = DRAWING.replace("<path", "<script>alert(1)</script><path")
    report = render.check(_diagram([]), FACTS, store.fonts(), render.Sources(drawing=bad))
    assert any(e.startswith("diagram:") for e in report.errors)


def test_a_diagram_draws_lines_runs_packets_and_dims_by_id() -> None:
    anim = _diagram([{"show": ["a", "b"], "draw": ["hop"], "flow": ["hop"]}, {"focus": ["b"]}])
    result = render.render(anim, FACTS, store.fonts(), CSS, render.Sources(drawing=DRAWING))
    svg = result.svg
    slug = result.plan.slug
    assert 'pathLength="1"' in svg  # the line strokes on
    assert 'class="m-packet"' in svg
    assert f'id="{slug}-d-a-d"' in svg  # dimmed parts sit in their own group
    assert "14 min</tspan>" in svg  # fact tokens in the drawing are filled


def test_a_story_diagram_plays_as_it_is() -> None:
    jam = (EXAMPLES / "keystone" / "diagrams" / "jam.svg").read_text(encoding="utf-8")
    facts = _keystone_facts()
    anim = _diagram(
        [
            {"caption": "Events pile up.", "show": ["sync", "topic", "consumer", "flood"]},
            {"caption": "The pool runs dry.", "show": ["pool", "errors"], "focus": ["pool"]},
            {"caption": "The fallback.", "show": ["lever", "oldpath"], "pulse": ["lever"]},
        ]
    )
    sources = render.Sources(drawing=jam)
    assert render.check(anim, facts, store.fonts(), sources).ok
    assert "Fallback switch" in render.render(anim, facts, store.fonts(), CSS, sources).svg


# ------------------------------------------------------------------------ scene
def test_scene_spots_need_anchors_the_drawing_has() -> None:
    anim = _example("animation-scene")
    anim["scene"]["spots"].append({"id": "door", "anchor": "door", "label": "Exit"})
    anim["steps"].append({"show": ["window"]})
    art = (EXAMPLES / "keystone" / "art" / "jam.svg").read_text(encoding="utf-8")
    report = render.check(anim, {}, store.fonts(), render.Sources(drawing=art))
    text = " ".join(report.errors)
    assert "anchor 'door' is not in the drawing" in text
    assert "names 'window'; name a spot id or a data-layer name" in text


def _keystone_facts() -> dict[str, Any]:
    from chronicle.core.story import derive

    raw = json.loads((EXAMPLES / "keystone" / "facts.json").read_text(encoding="utf-8"))
    facts: dict[str, Any] = derive.apply(raw)
    return facts


def test_a_scene_develops_from_gray_and_moves_its_layers() -> None:
    anim = _example("animation-scene")
    painting = {
        "file": "art/scene.webp",
        "width": 1600,
        "height": 900,
        "anchors": {"clock": [600, 200], "pile": [1200, 600], "lever": [400, 380]},
        "layers": [
            {
                "name": "beacon",
                "file": "art/beacon.webp",
                "box": [1400, 40, 120, 90],
                "motion": "spin",
            }
        ],
        "labels": [],
    }
    hrefs = {"art/scene.webp": "data:image/webp;base64,AA", "art/beacon.webp": "data:,"}
    sources = render.Sources(painting=painting, images=hrefs)
    result = render.render(anim, _keystone_facts(), store.fonts(), CSS, sources)
    slug = result.plan.slug
    assert f"#{slug}-s-color" in result.svg  # the color copy fades in over the gray one
    # The beacon spins whole turns over the loop, so the loop restarts without a jump.
    turn = re.search(r"100% \{ rotate: (\d+)\.00deg; \}", result.svg)
    assert turn and int(turn.group(1)) % 360 == 0 and int(turn.group(1)) > 0
    assert result.svg.count('class="m-spot"') == 3


def test_a_scene_needs_its_painting() -> None:
    with pytest.raises(ValueError, match="paint it first"):
        render.render(
            _example("animation-scene"), _keystone_facts(), store.fonts(), CSS, render.Sources()
        )


# ---------------------------------------------------------------- gif and video
def _frames() -> list[np.ndarray[Any, np.dtype[np.uint8]]]:
    out = []
    for i in range(6):
        frame = np.full((48, 80, 3), (240, 244, 246), np.uint8)
        frame[10:30, 5 + i * 8 : 25 + i * 8] = (200, 90, 30)
        out.append(frame)
    out.insert(3, out[2].copy())  # a frame that changes nothing lengthens the one before
    return out


def test_the_gif_decodes_to_the_frames_with_exact_flat_colors() -> None:
    cv2 = pytest.importorskip("cv2")
    frames = _frames()
    writer = gif.Writer(80, 48, gif.palette(frames), loop=True)
    for frame in frames:
        writer.add(frame, 0.1)
    data = writer.finish()
    assert data.startswith(b"GIF89a") and data.endswith(b"\x3b")
    assert b"NETSCAPE2.0" in data
    path = Path(pytest.importorskip("tempfile").mkdtemp()) / "t.gif"
    path.write_bytes(data)
    video = cv2.VideoCapture(str(path))
    decoded = []
    while True:
        ok, image = video.read()
        if not ok:
            break
        decoded.append(image)
    assert len(decoded) == 6
    unique = [f for k, f in enumerate(frames) if k != 3]
    for got, want in zip(decoded, unique, strict=True):
        assert np.abs(got.astype(int) - want.astype(int)).max() <= 8


def test_a_gif_frame_must_match_the_size() -> None:
    writer = gif.Writer(80, 48, gif.palette(_frames()), loop=False)
    with pytest.raises(ValueError, match="not 80x48"):
        writer.add(np.zeros((10, 10, 3), np.uint8), 0.1)


def test_video_writers_write_files(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    sinks: list[encode.Mp4 | encode.Webm] = [encode.Webm(tmp_path / "a.webm", 80, 48, 10)]
    program = encode.ffmpeg()
    if program:
        sinks.append(encode.Mp4(program, tmp_path / "a.mp4", 80, 48, 10))
    for sink in sinks:
        try:
            with sink:
                for frame in _frames():
                    sink.add(frame)
        except encode.VideoError as exc:
            pytest.skip(str(exc))
        assert sink.path.stat().st_size > 0


# -------------------------------------------------------------------------- CLI
@pytest.mark.parametrize("name", ["animation-tad", "animation-diagram", "animation-scene"])
def test_the_examples_check_clean(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["animate", "check", str(EXAMPLES / name / "animation.json")]) == 0
    assert "0 warning(s)" in capsys.readouterr().out


def test_new_starts_each_kind_and_check_asks_for_the_description(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for kind in ("tad", "diagram", "scene"):
        folder = tmp_path / "chronicle-runs" / kind
        assert main(["animate", "new", str(folder), "--kind", kind]) == 0
        anim = json.loads((folder / "animation.json").read_text(encoding="utf-8"))
        assert anim["kind"] == kind and kind in anim
    assert (tmp_path / "chronicle-runs" / "diagram" / "drawing.svg").exists()
    assert main(["animate", "new", str(tmp_path / "chronicle-runs" / "tad")]) == 1
    capsys.readouterr()
    assert (
        main(["animate", "check", str(tmp_path / "chronicle-runs" / "tad" / "animation.json")]) == 1
    )
    assert "meta.description is required" in capsys.readouterr().err


def test_build_writes_the_svg_and_the_embed_without_a_browser(tmp_path: Path) -> None:
    anim = EXAMPLES / "animation-diagram" / "animation.json"
    assert (
        main(["animate", "build", str(anim), "--out", str(tmp_path), "--formats", "svg,html"]) == 0
    )
    svg = (tmp_path / "animation.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and "From pull request to production" in svg
    fragment = (tmp_path / "embed.html").read_text(encoding="utf-8")
    assert fragment.startswith("<style>") and svg.strip() in fragment
    assert (tmp_path / "index.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    assert not (tmp_path / "capture.html").exists()


def test_build_refuses_an_unknown_format(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    anim = EXAMPLES / "animation-tad" / "animation.json"
    assert main(["animate", "build", str(anim), "--out", str(tmp_path), "--formats", "avi"]) == 1
    assert "unknown format avi" in capsys.readouterr().err


def test_build_paints_a_scene_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("cv2")
    anim = EXAMPLES / "animation-scene" / "animation.json"
    args = ["animate", "build", str(anim), "--out", str(tmp_path), "--formats", "svg"]
    assert main(args) == 0
    assert "scene painted" in capsys.readouterr().out
    assert "data:image/webp;base64," in (tmp_path / "animation.svg").read_text(encoding="utf-8")
    assert main(args) == 0
    assert "scene painted" not in capsys.readouterr().out


def test_build_captures_frames_in_a_browser(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    try:
        shoot.find()
    except shoot.BrowserError:
        pytest.skip("no Chromium on this machine")
    folder = tmp_path / "hop"
    folder.mkdir()
    (folder / "drawing.svg").write_text(DRAWING, encoding="utf-8")
    (folder / "facts.json").write_text(json.dumps(FACTS), encoding="utf-8")
    anim = copy.deepcopy(_diagram([{"caption": "A hop.", "draw": ["hop"], "flow": ["hop"]}]))
    anim["frame"] = {"width": 480, "height": 360}
    (folder / "animation.json").write_text(json.dumps(anim), encoding="utf-8")
    out = tmp_path / "out"
    code = main(
        [
            "animate", "build", str(folder / "animation.json"), "--out", str(out),
            "--formats", "png,gif", "--gif-fps", "4", "--gif-width", "200",
        ]
    )  # fmt: skip
    assert code == 0
    assert store.decode_png((out / "poster.png").read_bytes()).shape == (360, 480, 3)
    assert (out / "steps.png").exists()
    assert (out / "animation.gif").read_bytes()[:6] == b"GIF89a"
    assert not (out / "capture.html").exists()
