from __future__ import annotations

import numpy as np
import pytest
from chronicle.core.watercolor.canvas import Canvas
from chronicle.core.watercolor.presets import PRESETS, paint_preset
from chronicle.core.watercolor.scene import SceneError, paint_elements

SQUARE = [[40, 40], [160, 40], [160, 160], [40, 160]]


def test_wash_tints_inside_the_shape_and_leaves_paper_outside() -> None:
    c = Canvas(200, 200, seed=1)
    before = c.rgb.copy()
    c.wash([SQUARE], "ultramarine", opacity=0.7, wobble_px=0)
    inside = c.rgb[90:110, 90:110]
    outside = c.rgb[5:15, 5:15]
    assert inside[..., 2].mean() > inside[..., 0].mean() + 0.1
    np.testing.assert_allclose(outside, before[5:15, 5:15])


def test_same_seed_paints_the_same_picture() -> None:
    def paint() -> np.ndarray:
        c = Canvas(200, 120, seed=7)
        c.wash([SQUARE], "burnt-sienna", blooms=1, wet=0.4)
        c.ink([[10, 10], [190, 110]])
        return c.finish("deckle")

    np.testing.assert_array_equal(paint(), paint())


def test_occlude_hides_what_is_behind() -> None:
    c = Canvas(200, 200, seed=2)
    c.wash([SQUARE], "indigo", opacity=1.0, wobble_px=0)
    c.wash([SQUARE], "lemon", opacity=0.5, wobble_px=0, occlude=True)
    center = c.rgb[95:105, 95:105].mean(axis=(0, 1))
    assert center[0] > 0.8 and center[1] > 0.7, "the indigo underneath should be gone"


def test_sprite_reports_where_its_paint_is() -> None:
    c = Canvas(300, 200, seed=3)
    c.wash([[[100, 50], [140, 50], [140, 90], [100, 90]]], "vermilion", wobble_px=0)
    _, box = c.sprite()
    assert box is not None
    x, y, w, h = box
    assert 90 <= x <= 100 and 40 <= y <= 50 and 40 <= w <= 60 and 40 <= h <= 60


def test_scene_elements_paint_and_name_bad_input() -> None:
    painting = paint_elements(
        {
            "size": [400, 240],
            "seed": 4,
            "elements": [
                {"motif": "sky", "horizon": 150, "mood": "dawn", "clouds": 2},
                {"motif": "mountains", "base": 160, "height": 60},
            ],
            "layers": [
                {
                    "name": "birds",
                    "motion": "drift",
                    "elements": [{"motif": "birds", "x": 200, "y": 60, "count": 3}],
                }
            ],
        },
        scale=0.5,
    )
    assert painting.base.shape == (120, 200, 3)
    assert painting.layers[0].name == "birds"
    with pytest.raises(SceneError, match="unknown motif 'castle'"):
        paint_elements({"size": [400, 240], "elements": [{"motif": "castle"}]}, scale=0.3)
    with pytest.raises(SceneError, match="has no parameter color"):
        paint_elements(
            {"size": [400, 240], "elements": [{"motif": "sky", "horizon": 100, "color": "red"}]},
            scale=0.3,
        )


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_every_preset_paints(name: str) -> None:
    painting = paint_preset(name, {}, scale=0.12)
    assert painting.base.ndim == 3
    assert painting.base.mean() < 254, "a preset should leave paint on the paper"


def test_hero_keystone_hangs_above_its_slot() -> None:
    painting = paint_preset("bridge-hero", {"built": 3.75}, scale=0.12)
    layer = next(layer for layer in painting.layers if layer.name == "keystone")
    assert layer.motion == "descend"
    assert painting.anchors["load"][1] < painting.anchors["slot"][1]
