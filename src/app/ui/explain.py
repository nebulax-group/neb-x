"""Draw the panels a subsystem offers to explain its own prediction.

Rendering only, and deliberately generic: this file switches on a panel's
``kind``, never on which subsystem produced it, so a second subsystem that grows
an ``explain`` module gets these charts for free. The panel shapes are documented
in ``src/app/services.py``.

Charts are Altair because Streamlit already depends on it, and because it draws
SVG — text stays crisp and selectable when the demo video is scaled up.
"""

import math
from html import escape
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.app.config import (
    CHART_AXIS_ALLOWANCE,
    CHART_LABEL_FONT_SIZE,
    CHART_LABEL_OFFSET,
    CHART_PADDING,
    CHART_PADDING_LEFT,
    CHART_ROW_HEIGHT,
    CHART_ROW_PADDING,
    CHART_TITLE_FONT_SIZE,
    EXPLAIN_HEADING,
    EXPLAIN_STANDFIRST,
    MONO_STACK,
    PALETTE,
    PANEL_STATE_KEY,
    SANS_STACK,
    STEP_BACK,
    STEP_COUNTER,
    STEP_NEXT,
    STEP_NUMBER,
    TRACE_PLOT_HEIGHT,
)

EMPTY_PANEL_MESSAGE = "Nothing to show for this file."
UNKNOWN_PANEL_MESSAGE = "This result includes a panel this version cannot draw yet ({kind})."

# A bar at least this much of the axis has room to hold its own value; shorter ones
# get it printed past their end. A fixed column at the right would be simpler, but it
# has to be sized for the longest number at the narrowest window, and on a phone that
# column either swallows the chart or collides with the bars.
_LABEL_INSIDE_SHARE = 0.65
_LABEL_GAP = 6
_INSIDE = "_inside"
_TICK_TARGET = 9
_RAIL_SLACK = 4

_HEADING = """<div class="nx-explain-head">
<h2 class="nx-explain-title">{heading}</h2>
<p class="nx-explain-standfirst">{standfirst}</p>
</div>"""

_DECK_STATUS = """<div class="nx-deck-status">
<span class="nx-deck-counter">{counter}</span>
<span class="nx-deck-title">{title}</span>
{subject}
</div>"""

_PANEL_CAPTION = '<p class="nx-panel-caption">{caption}</p>'


# Vega-Lite merges a layered chart down to one axis per channel, and a single
# ``axis=None`` anywhere in the stack removes it for the whole chart. Every layer of
# a bar panel therefore declares the same axes through the two helpers below; there
# is no opting out of them per layer.
def _axis(
    title: str | None,
    *,
    grid: bool,
    number_format: str | None = None,
    values: list[float] | None = None,
) -> alt.Axis:
    # Altair rejects an explicit None for either of these; absence is its own sentinel.
    return alt.Axis(
        title=title,
        format=alt.Undefined if number_format is None else number_format,
        values=alt.Undefined if values is None else values,
        grid=grid,
        gridColor=PALETTE["hairline"],
        gridOpacity=0.7,
        domainColor=PALETTE["hairline-strong"],
        tickColor=PALETTE["hairline-strong"],
        labelColor=PALETTE["chalk-dim"],
        labelFont=SANS_STACK,
        labelFontSize=CHART_LABEL_FONT_SIZE,
        titleColor=PALETTE["chalk-dim"],
        titleFont=SANS_STACK,
        titleFontSize=CHART_TITLE_FONT_SIZE,
        titleFontWeight=600,
        titlePadding=CHART_LABEL_OFFSET,
    )


def _row_y() -> alt.Y:
    """The shared band scale every layer of a bar panel sits on."""
    axis = alt.Axis(
        labelFont=MONO_STACK,
        labelFontSize=CHART_LABEL_FONT_SIZE,
        labelColor=PALETTE["chalk"],
        labelLimit=280,
        labelPadding=CHART_LABEL_OFFSET,
        domain=False,
        ticks=False,
        grid=False,
        title=None,
    )
    return alt.Y(
        "label:N",
        sort=None,
        title=None,
        axis=axis,
        scale=alt.Scale(paddingInner=CHART_ROW_PADDING),
    )


def _ticks(span: float) -> list[float]:
    """Round tick positions covering 0 to ``span``.

    Chosen rather than left to Vega-Lite so that the last tick lands on the span
    itself — on the failure threshold, for the bullet chart — instead of a round
    number a little past it.
    """
    if span <= 0:
        return [0.0]
    raw = span / _TICK_TARGET
    magnitude = 10 ** math.floor(math.log10(raw))
    step = min(
        (option * magnitude for option in (1, 2, 2.5, 5, 10)),
        key=lambda candidate: abs(candidate - raw),
    )
    return [round(index * step, 10) for index in range(int(span / step) + 1)]


def _row_x(field: str, title: str, span: float, number_format: str | None) -> alt.X:
    return alt.X(
        f"{field}:Q",
        title=title,
        scale=alt.Scale(domain=[0, span], nice=False),
        axis=_axis(title, grid=True, number_format=number_format, values=_ticks(span)),
    )


def _bar_layers(
    frame: pd.DataFrame,
    value_title: str,
    formatter: str,
    axis_format: str | None,
    span: float,
) -> list[alt.Chart]:
    """A bar per row, with its value printed on it.

    Printed as well as drawn because these bars span several orders of magnitude:
    the smallest are under a pixel wide, and a reader still has to be able to tell
    a 0.04% share from a 0.001% one.

    Two text layers rather than one, split on whether the bar is long enough to
    contain its own label. Vega-Lite has no per-datum offset channel, so the
    alternative to splitting would be one compromise position that sits wrong for
    half the rows.
    """
    text = alt.Text("value:Q", format=formatter)
    bars = alt.Chart(frame).mark_bar(color=PALETTE["instrument"], cornerRadiusEnd=1).encode(
        y=_row_y(),
        x=_row_x("value", value_title, span, axis_format),
        tooltip=[
            alt.Tooltip("label:N", title="Item"),
            alt.Tooltip("value:Q", title=value_title, format=formatter),
            alt.Tooltip("detail:N", title="Detail"),
        ],
    )

    def label(inside: bool) -> alt.Chart:
        return alt.Chart(frame[frame[_INSIDE] == inside]).mark_text(
            align="right" if inside else "left",
            baseline="middle",
            dx=-_LABEL_GAP if inside else _LABEL_GAP,
            font=MONO_STACK,
            fontSize=CHART_LABEL_FONT_SIZE,
            fontWeight=500,
            color=PALETTE["abyss"] if inside else PALETTE["chalk"],
        ).encode(
            y=_row_y(),
            x=_row_x("value", value_title, span, axis_format),
            text=text,
        )

    return [bars, label(True), label(False)]


def _prepare(rows: list[dict], target: float | None) -> tuple[pd.DataFrame, float]:
    frame = pd.DataFrame(rows)
    span = float(max(frame["value"].max(), target or 0.0))
    if target is not None:
        frame["target"] = target
    frame[_INSIDE] = frame["value"] >= _LABEL_INSIDE_SHARE * span if span > 0 else False
    return frame, span


def _finish(layers: list[alt.Chart], height: int) -> alt.Chart:
    # Padding has to be the four-sided object, never a single number: Streamlit sets
    # ``autosize.contains = "padding"`` and its chart wrapper then writes
    # ``padding.bottom`` onto the spec, which throws on a bare number and takes the
    # whole chart down in the browser with nothing showing in the Python logs.
    padding = dict.fromkeys(("top", "right", "bottom"), CHART_PADDING)
    padding["left"] = CHART_PADDING_LEFT
    return (
        alt.layer(*layers)
        .properties(width="container", height=height, padding=padding)
        .configure_view(stroke=None)
    )


def _draw(layers: list[alt.Chart], height: int) -> None:
    # theme=None because Streamlit's own chart theme would repaint these in its
    # default blues, and the palette check in ui/theme.py cannot see inside a chart.
    st.altair_chart(_finish(layers, height), width="stretch", theme=None)


def _chart_height(plot_height: int) -> int:
    """Total SVG height for a given plotting area, chrome included."""
    return plot_height + CHART_PADDING * 2 + CHART_AXIS_ALLOWANCE


def _rows_height(count: int) -> int:
    return _chart_height(max(count, 1) * CHART_ROW_HEIGHT)


def _render_bullet(panel: dict[str, Any]) -> None:
    frame, span = _prepare(panel["rows"], panel["target"])

    # The track is the whole of the structure's fatigue life, so a short bar reads
    # as margin remaining rather than merely as a small number.
    value_title = "Cumulative damage (D)"
    track = alt.Chart(frame).mark_bar(color=PALETTE["deck-high"], cornerRadiusEnd=1).encode(
        y=_row_y(),
        x=_row_x("target", value_title, span, None),
    )
    marker = alt.Chart(frame).mark_tick(
        color=PALETTE["chalk"],
        thickness=2,
        size=CHART_ROW_HEIGHT * (1 - CHART_ROW_PADDING),
    ).encode(
        y=_row_y(),
        x=_row_x("target", value_title, span, None),
    )

    layers = [track, *_bar_layers(frame, value_title, ".3f", None, span), marker]
    _draw(layers, _rows_height(len(panel["rows"])))
    st.markdown(
        f'<p class="nx-panel-key"><span class="nx-key-mark"></span>'
        f'{escape(panel["target_label"])}</p>',
        unsafe_allow_html=True,
    )


def _render_bars(panel: dict[str, Any]) -> None:
    frame, span = _prepare(panel["rows"], None)
    layers = _bar_layers(frame, panel["value_title"], ".2%", ".0%", span)
    _draw(layers, _rows_height(len(panel["rows"])))


def _render_metrics(panel: dict[str, Any]) -> None:
    cells = "".join(
        f'<div class="nx-metric"><dt>{escape(item["label"])}</dt>'
        f'<dd>{escape(item["value"])}'
        f'<span>{escape(item["detail"])}</span></dd></div>'
        for item in panel["items"]
    )
    st.markdown(f'<dl class="nx-metrics">{cells}</dl>', unsafe_allow_html=True)


def _render_line(panel: dict[str, Any]) -> None:
    x_title, y_title = panel["x_title"], panel["y_title"]
    x, y = panel["points"]
    frame = pd.DataFrame({x_title: x, y_title: y})

    line = alt.Chart(frame).mark_line(color=PALETTE["instrument"], strokeWidth=0.7).encode(
        x=alt.X(f"{x_title}:Q", axis=_axis(x_title, grid=False), scale=alt.Scale(nice=False)),
        y=alt.Y(f"{y_title}:Q", axis=_axis(y_title, grid=True)),
        tooltip=[
            alt.Tooltip(f"{x_title}:Q", title=x_title, format=","),
            alt.Tooltip(f"{y_title}:Q", title=y_title, format=".3f"),
        ],
    )
    # Fatigue counts swings about the mean, so the zero line is the reference the
    # eye needs to read an amplitude off the trace.
    zero = alt.Chart(frame).mark_rule(color=PALETTE["chalk-dim"], strokeWidth=1, opacity=0.5).encode(
        y=alt.datum(0)
    )
    _draw([zero, line], _chart_height(TRACE_PLOT_HEIGHT))


_RENDERERS = {
    "bullet": _render_bullet,
    "bars": _render_bars,
    "metrics": _render_metrics,
    "line": _render_line,
}


def _has_content(panel: dict[str, Any]) -> bool:
    for key in ("rows", "items"):
        if key in panel:
            return bool(panel[key])
    if "points" in panel:
        return bool(panel["points"][0])
    return True


def _goto(index: int) -> None:
    # A callback rather than a return value: Streamlit runs it before the rerun, so the
    # rail and the panel below it always agree about which step is showing.
    st.session_state[PANEL_STATE_KEY] = index


def _current_step(count: int) -> int:
    """The selected step, clamped: a shorter batch must not strand the index."""
    return max(0, min(int(st.session_state.get(PANEL_STATE_KEY, 0)), count - 1))


def _render_rail(panels: list[dict[str, Any]], index: int) -> None:
    """The step rail: one numbered cell per panel, plus back and next."""
    count = len(panels)
    st.markdown(
        _DECK_STATUS.format(
            counter=escape(STEP_COUNTER.format(current=index + 1, total=count)),
            title=escape(panels[index]["title"]),
            subject=(
                f'<span class="nx-panel-subject">{escape(subject)}</span>'
                if (subject := panels[index].get("subject"))
                else ""
            ),
        ),
        unsafe_allow_html=True,
    )

    with st.container(key="nx-deck-nav"):
        with st.container(key="nx-deck-steps"):
            # More columns than steps: the cells are controls, not a progress bar, and
            # stretching four of them across the full width reads as empty furniture.
            for step, column in enumerate(st.columns(count + _RAIL_SLACK)[:count]):
                with column:
                    st.button(
                        STEP_NUMBER.format(number=step + 1),
                        key=f"nx-step-{step}",
                        type="primary" if step == index else "secondary",
                        width="stretch",
                        on_click=_goto,
                        args=(step,),
                        help=panels[step]["title"],
                    )

        # Back and next sit on their own row rather than sharing the numbers' one. A
        # single row needs a spacer column between them, and Streamlit keeps that
        # spacer's width when the numbers are hidden on a phone, leaving the two
        # buttons squeezed to nothing.
        for column, label, target, spent in zip(
            st.columns([1.5, 1.5, _RAIL_SLACK]),
            (STEP_BACK, STEP_NEXT),
            (index - 1, index + 1),
            (index == 0, index == count - 1),
        ):
            with column:
                st.button(
                    label,
                    key=f"nx-{label.lower()}",
                    disabled=spent,
                    width="stretch",
                    on_click=_goto,
                    args=(target,),
                )


def render(panels: list[dict[str, Any]]) -> None:
    """Draw the panels as a deck, one step at a time. Silent when there are none."""
    if not panels:
        return

    st.markdown(
        _HEADING.format(heading=escape(EXPLAIN_HEADING), standfirst=escape(EXPLAIN_STANDFIRST)),
        unsafe_allow_html=True,
    )

    index = _current_step(len(panels))
    _render_rail(panels, index)

    panel = panels[index]
    if caption := panel.get("caption"):
        st.markdown(_PANEL_CAPTION.format(caption=escape(caption)), unsafe_allow_html=True)

    renderer = _RENDERERS.get(panel["kind"])
    if renderer is None:
        st.warning(UNKNOWN_PANEL_MESSAGE.format(kind=panel["kind"]))
    elif not _has_content(panel):
        st.caption(EMPTY_PANEL_MESSAGE)
    else:
        renderer(panel)
