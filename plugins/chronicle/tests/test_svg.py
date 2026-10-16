from __future__ import annotations

import math

import numpy as np
import pytest
from chronicle.core.watercolor.svg import pathdata as pd
from chronicle.core.watercolor.svg.paint import Style, paint_drawing, paint_scene
from chronicle.core.watercolor.svg.parse import SvgError, parse


def ends(d: str) -> list[tuple[tuple[float, float], tuple[float, float], bool]]:
    return [
        (
            (round(s.points[0][0], 3), round(s.points[0][1], 3)),
            (round(s.points[-1][0], 3), round(s.points[-1][1], 3)),
            s.closed,
        )
        for s in pd.parse_path(d)
    ]


def test_path_commands_absolute_relative_and_implicit() -> None:
    assert ends("M10 10 L50 10 50 50 Z") == [((10, 10), (50, 50), True)]
    assert ends("m10,10 h40 v40 h-40 z") == [((10, 10), (10, 50), True)]
    assert ends("M1.5.5L2-3") == [((1.5, 0.5), (2, -3), False)]
    assert ends("M0,0 Q10,10 20,0 T40,0") == [((0, 0), (40, 0), False)]
    assert ends("M0 0 C0-10 20-10 20 0 S40 10 40 0") == [((0, 0), (40, 0), False)]


def test_arc_flags_may_be_unspaced_and_end_on_the_endpoint() -> None:
    (sub,) = pd.parse_path("M0 0a5 5 0 105 5")
    assert sub.points[-1] == (5.0, 5.0)
    (half,) = pd.parse_path("M0 0 A10 10 0 0 1 20 0")
    # A half circle from (0,0) to (20,0), swept clockwise, bulges upward (negative y).
    assert min(p[1] for p in half.points) == pytest.approx(-10, abs=0.5)


def test_transform_lists_compose_in_svg_order() -> None:
    m = pd.parse_transform("translate(10 20) rotate(90 5 5) scale(2)")
    x, y = pd.apply(m, (0.0, 0.0))
    assert (round(x, 6), round(y, 6)) == (20.0, 20.0)
    assert pd.scale_of(pd.parse_transform("scale(3)")) == pytest.approx(3)
    with pytest.raises(pd.PathError):
        pd.parse_transform("wiggle(3)")


SCENE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
  <defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#cfd8d2"/><stop offset="1" stop-color="#ece4d2"/>
  </linearGradient></defs>
  <rect x="0" y="0" width="800" height="300" fill="url(#sky)" data-paint="wet"/>
  <g transform="translate(100 100)" stroke="#2b231d" stroke-width="2">
    <rect width="200" height="150" fill="burnt-sienna" data-shade="0.5"/>
    <circle cx="100" cy="75" r="30" fill="#ffffff" data-anchor="knob"/>
  </g>
  <g data-layer="van" data-motion="cross" data-travel="40"><rect x="500" y="300" width="80"
     height="40" fill="#2f6b4f"/></g>
  <text x="120" y="90" font-size="20" data-label="label" transform="rotate(-10 120 90)">
    Order {{orders.count}}</text>
</svg>"""


def test_parse_scales_a_small_viewbox_and_collects_layers_anchors_and_labels() -> None:
    d = parse(SCENE)
    assert (d.width, d.height) == (1600, 1000)
    assert [layer.name for layer in d.layers] == ["van"]
    assert d.layers[0].travel == pytest.approx(80)
    assert d.anchors["knob"] == pytest.approx((400, 350), abs=1)
    (label,) = d.labels
    assert label.text == "Order {{orders.count}}"
    assert label.style == "label"
    assert label.size == pytest.approx(40)
    assert label.angle == pytest.approx(-10)
    sky = d.items[0]
    assert sky.gradient is not None and len(sky.gradient.stops) == 2
    assert d.items[1].fill == pytest.approx((0xAD / 255, 0x53 / 255, 0x2E / 255))


@pytest.mark.parametrize(
    ("snippet", "message"),
    [
        ('<!DOCTYPE svg><svg viewBox="0 0 10 10"/>', "DOCTYPE"),
        ('<svg viewBox="0 0 400 400"><image href="x.png"/></svg>', "<image> is not supported"),
        ('<svg viewBox="0 0 400 400"><rect width="9" height="9" fill="rgba(1)"/></svg>', "color"),
        ('<svg viewBox="0 0 400 400"><rect width="9" height="9" data-paint="oil"/></svg>', "oil"),
        (
            '<svg viewBox="0 0 400 400"><g data-layer="a"><g data-layer="b"><rect width="9" '
            'height="9"/></g></g></svg>',
            "inside another layer",
        ),
        ('<svg viewBox="0 0 400 400"><use href="#missing"/></svg>', "must point at"),
        ('<svg viewBox="0 0 400 400"></svg>', "no shapes"),
    ],
)
def test_parse_refuses_what_it_cannot_paint(snippet: str, message: str) -> None:
    with pytest.raises(SvgError, match=message):
        parse(snippet)


def test_painting_tints_the_shape_keeps_paper_and_gives_moving_layers_alpha() -> None:
    painting = paint_scene({"svg": "inline", "seed": 3, "vignette": "none"}, SCENE, scale=0.25)
    rgb = painting.base[..., ::-1].astype(float) / 255
    # the brown box spans x 200-600, y 200-500 at the painted size (viewBox doubled)
    box = rgb[int(220 * 0.25) : int(260 * 0.25), int(220 * 0.25) : int(300 * 0.25)]
    assert box[..., 0].mean() > box[..., 2].mean() + 0.1  # burnt sienna is red-brown
    assert rgb[-3:, :20].mean() > 0.9  # unpainted paper stays light
    (van,) = painting.layers
    assert van.image.shape[2] == 4 and van.blend == "normal"
    assert van.image[..., 3].max() == 255 and van.image[..., 3].min() == 0
    assert painting.labels[0]["text"].startswith("Order")


def test_same_seed_paints_the_same_drawing() -> None:
    first = paint_drawing(parse(SCENE), seed=5, scale=0.2).base
    second = paint_drawing(parse(SCENE), seed=5, scale=0.2).base
    np.testing.assert_array_equal(first, second)


def test_lift_line_scrubs_paint_back_toward_paper() -> None:
    dark = """<svg viewBox="0 0 400 200"><rect width="400" height="200" fill="#2d3550"
      data-loose="0" data-shade="0"/><path d="M20 100 L380 100" stroke="#ffffff"
      stroke-width="12" data-line="lift"/></svg>"""
    plain = dark.replace('data-line="lift"', 'data-line="none"')
    lit = paint_scene({"vignette": "none"}, dark, 0.5).base.astype(float)
    flat = paint_scene({"vignette": "none"}, plain, 0.5).base.astype(float)
    row = int(100 * 4 * 0.5)  # 400-wide viewBox paints at 1600 wide, then scale 0.5
    assert lit[row, 200:600].mean() > flat[row, 200:600].mean() + 40


def test_style_rejects_unknown_settings() -> None:
    assert Style.from_spec({"shade": 0.1}).shade == pytest.approx(0.1)
    with pytest.raises(ValueError, match="no setting"):
        Style.from_spec({"glitter": 1})
    assert math.isclose(Style().light, 225.0)
