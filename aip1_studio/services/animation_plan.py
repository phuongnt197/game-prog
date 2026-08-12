from __future__ import annotations

import json
import re
import textwrap
from typing import Any


ANIMATION_PLAN_MARKER = "===ANIMATION_PLAN==="
SCENE_NAME = "ConceptScene"
OBJECT_KINDS = frozenset({"text", "box", "circle", "dot", "arrow", "line"})
ACTION_TYPES = frozenset({
    "show", "create", "write", "move", "shift", "highlight", "color", "fade_out",
    "transform_text", "scale", "rotate", "wait",
})
COLORS = frozenset({
    "WHITE", "GRAY", "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE", "PINK",
    "TEAL", "GOLD", "MAROON",
})
DYNAMIC_ACTIONS = frozenset({"move", "shift", "color", "fade_out", "transform_text", "scale", "rotate"})
SPATIAL_ACTIONS = frozenset({"move", "shift", "fade_out", "scale", "rotate"})


def parse_animation_response(raw: str) -> dict[str, Any]:
    if ANIMATION_PLAN_MARKER not in raw:
        raise ValueError(f"The response must contain the {ANIMATION_PLAN_MARKER} marker.")
    explanation, plan_source = raw.split(ANIMATION_PLAN_MARKER, 1)
    explanation = extract_explanation(explanation)
    if not explanation:
        raise ValueError("The visual lesson must include an explanation.")
    if len(explanation) > 5_000:
        raise ValueError("The visual lesson explanation is too long.")
    plan_source = re.sub(r"^\s*```(?:json)?\s*", "", plan_source, flags=re.IGNORECASE)
    plan_source = re.sub(r"\s*```\s*$", "", plan_source).strip()
    start, end = plan_source.find("{"), plan_source.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The response must contain one JSON animation plan.")
    try:
        payload = json.loads(plan_source[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"The animation plan is invalid JSON near line {exc.lineno}.") from exc
    return {"explanation": explanation, "animation_plan": validate_animation_plan(payload)}


def validate_animation_plan(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("The animation plan must be a JSON object.")
    title = _text(payload.get("title"), "title", 72)
    raw_objects = payload.get("objects")
    raw_actions = payload.get("actions")
    if not isinstance(raw_objects, list) or not 3 <= len(raw_objects) <= 16:
        raise ValueError("The animation plan needs between 3 and 16 visual objects.")
    if not isinstance(raw_actions, list) or not 5 <= len(raw_actions) <= 32:
        raise ValueError("The animation plan needs between 5 and 32 animation actions.")

    objects: list[dict[str, Any]] = []
    object_by_id: dict[str, dict[str, Any]] = {}
    for raw_object in raw_objects:
        visual = _validate_object(raw_object)
        if visual["id"] in object_by_id:
            raise ValueError(f"The visual object id {visual['id']!r} is duplicated.")
        object_by_id[visual["id"]] = visual
        objects.append(visual)
    if sum(visual["kind"] != "text" for visual in objects) < 2:
        raise ValueError("The animation needs at least two non-text visual objects.")

    actions: list[dict[str, Any]] = []
    referenced: set[str] = set()
    visible: set[str] = set()
    for raw_action in raw_actions:
        action = _validate_action(raw_action, object_by_id)
        targets = set(action.get("targets", []))
        if action["type"] in {"show", "create", "write"}:
            visible.update(targets)
        elif action["type"] != "wait":
            hidden = targets - visible
            if hidden:
                raise ValueError(
                    "Visual objects must be shown before they change; hidden: "
                    + ", ".join(sorted(hidden))
                    + "."
                )
        if action["type"] == "fade_out":
            visible.difference_update(targets)
        actions.append(action)
        referenced.update(targets)
    dynamic_actions = [action for action in actions if action["type"] in DYNAMIC_ACTIONS]
    if not dynamic_actions:
        raise ValueError("The plan must move, transform, recolor, rotate, scale, or remove a visual object.")
    if len(dynamic_actions) < 2:
        raise ValueError("The plan needs at least two meaningful visual changes.")
    if not any(
        action["type"] in SPATIAL_ACTIONS
        and any(object_by_id[target]["kind"] != "text" for target in action.get("targets", []))
        for action in actions
    ):
        raise ValueError("At least one visible shape must move, shift, rotate, scale, or disappear.")
    unused = set(object_by_id) - referenced
    if unused:
        raise ValueError(f"Every visual object must be animated; unused: {', '.join(sorted(unused))}.")
    return {"title": title, "objects": objects, "actions": actions}


def compile_animation_plan(plan: dict[str, Any]) -> str:
    objects = {visual["id"]: visual for visual in plan["objects"]}
    positions = {visual["id"]: _object_center(visual) for visual in plan["objects"]}
    lines = [
        "from manim import Scene, Text, VGroup, RoundedRectangle, Circle, Dot, Arrow, Line, Write, FadeIn, FadeOut, Create, Indicate, Transform, Rotate, UP, DEGREES, WHITE, GRAY, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK, TEAL, GOLD, MAROON",
        "",
        f"class {SCENE_NAME}(Scene):",
        "    def construct(self):",
        f"        lesson_title = Text({_literal(plan['title'])}, font_size=34, color=BLUE).scale(0.82)",
        "        lesson_title.to_edge(UP)",
        "        self.play(Write(lesson_title), run_time=0.8)",
    ]
    for visual in plan["objects"]:
        lines.extend(_compile_object(visual))

    transform_index = 0
    for action in plan["actions"]:
        action_type = action["type"]
        duration = _format_number(action["duration"])
        targets = action.get("targets", [])
        variables = [_variable(target) for target in targets]
        if action_type == "wait":
            lines.append(f"        self.wait({duration})")
            continue
        if action_type in {"show", "create", "write", "highlight", "color", "fade_out"}:
            animations: list[str] = []
            for variable in variables:
                if action_type == "show":
                    animations.append(f"FadeIn({variable}, shift=UP * 0.12)")
                elif action_type == "create":
                    animations.append(f"Create({variable})")
                elif action_type == "write":
                    animations.append(f"Write({variable})")
                elif action_type == "highlight":
                    animations.append(f"Indicate({variable}, color={action['color']})")
                elif action_type == "color":
                    animations.append(f"{variable}.animate.set_color({action['color']})")
                else:
                    animations.append(f"FadeOut({variable})")
            lines.append(f"        self.play({', '.join(animations)}, run_time={duration})")
            continue

        target = targets[0]
        variable = variables[0]
        if action_type == "move":
            x, y = action["x"], action["y"]
            lines.append(f"        self.play({variable}.animate.move_to([{_format_number(x)}, {_format_number(y)}, 0]), run_time={duration})")
            positions[target] = (x, y)
        elif action_type == "shift":
            dx, dy = action["dx"], action["dy"]
            lines.append(f"        self.play({variable}.animate.shift([{_format_number(dx)}, {_format_number(dy)}, 0]), run_time={duration})")
            old_x, old_y = positions[target]
            positions[target] = (old_x + dx, old_y + dy)
        elif action_type == "scale":
            lines.append(f"        self.play({variable}.animate.scale({_format_number(action['factor'])}), run_time={duration})")
        elif action_type == "rotate":
            lines.append(f"        self.play(Rotate({variable}, angle=DEGREES * {_format_number(action['angle'])}), run_time={duration})")
        elif action_type == "transform_text":
            transform_index += 1
            next_variable = f"{variable}_next_{transform_index}"
            x, y = positions[target]
            font_size = objects[target]["font_size"]
            color = action["color"]
            lines.extend([
                f"        {next_variable} = Text({_literal(action['text'])}, font_size={font_size}, color={color})",
                f"        {next_variable}.move_to([{_format_number(x)}, {_format_number(y)}, 0])",
                f"        self.play(Transform({variable}, {next_variable}), run_time={duration})",
            ])
    lines.append("        self.wait(1.5)")
    return "\n".join(lines) + "\n"


def build_fallback_animation_plan(question: str, explanation: str) -> dict[str, Any]:
    lowered = question.lower()
    if any(word in lowered for word in ("loop", "iterate", "iteration", "list")):
        plan = _loop_plan(question)
    elif any(word in lowered for word in ("recursion", "recursive", "call stack", "stack frame")):
        plan = _recursion_plan(question)
    elif "binary search" in lowered:
        plan = _binary_search_plan(question)
    else:
        plan = _concept_flow_plan(question, explanation)
    return validate_animation_plan(plan)


def extract_explanation(raw: str) -> str:
    candidate = raw.split(ANIMATION_PLAN_MARKER, 1)[0]
    candidate = re.sub(r"^\s*EXPLANATION\s*:\s*", "", candidate, flags=re.IGNORECASE).strip()
    return candidate[:5_000]


def _validate_object(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Every visual object must be a JSON object.")
    object_id = str(raw.get("id") or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,24}", object_id):
        raise ValueError("Visual object ids must use lowercase letters, digits, and underscores.")
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in OBJECT_KINDS:
        raise ValueError(f"The visual object type {kind!r} is not supported.")
    visual: dict[str, Any] = {
        "id": object_id,
        "kind": kind,
        "x": _number(raw.get("x", 0), "x", -6.4, 6.4),
        "y": _number(raw.get("y", 0), "y", -2.8, 2.5),
        "color": _color(raw.get("color", "BLUE")),
    }
    if kind in {"text", "box", "circle"}:
        visual["label"] = _text(raw.get("label"), f"{object_id} label", 80)
        visual["font_size"] = int(_number(raw.get("font_size", 24), "font_size", 14, 38))
    if kind == "box":
        visual["width"] = _number(raw.get("width", 2.2), "width", 0.8, 5.5)
        visual["height"] = _number(raw.get("height", 1.0), "height", 0.5, 2.2)
    elif kind == "circle":
        visual["radius"] = _number(raw.get("radius", 0.7), "radius", 0.25, 1.6)
    elif kind == "dot":
        visual["radius"] = _number(raw.get("radius", 0.12), "radius", 0.06, 0.3)
    elif kind in {"arrow", "line"}:
        visual["to_x"] = _number(raw.get("to_x"), "to_x", -6.4, 6.4)
        visual["to_y"] = _number(raw.get("to_y"), "to_y", -2.8, 2.5)
        if abs(visual["x"] - visual["to_x"]) + abs(visual["y"] - visual["to_y"]) < 0.2:
            raise ValueError(f"The {kind} {object_id!r} needs different start and end points.")
        label = str(raw.get("label") or "").strip()
        visual["label"] = _plain_text(label)[:36]
        visual["font_size"] = int(_number(raw.get("font_size", 18), "font_size", 14, 28))
    return visual


def _validate_action(raw: Any, object_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Every animation action must be a JSON object.")
    action_type = str(raw.get("type") or "").strip().lower()
    if action_type not in ACTION_TYPES:
        raise ValueError(f"The animation action {action_type!r} is not supported.")
    duration = _number(raw.get("duration", 0.8), "duration", 0.15, 3.0)
    if action_type == "wait":
        return {"type": "wait", "duration": duration}
    raw_targets = raw.get("targets", raw.get("target"))
    targets = [raw_targets] if isinstance(raw_targets, str) else raw_targets
    if not isinstance(targets, list) or not targets or len(targets) > 8:
        raise ValueError(f"The {action_type} action needs one to eight targets.")
    targets = [str(target) for target in targets]
    if len(set(targets)) != len(targets) or any(target not in object_by_id for target in targets):
        raise ValueError(f"The {action_type} action references an unknown or duplicate target.")
    if action_type in {"move", "shift", "transform_text", "scale", "rotate"} and len(targets) != 1:
        raise ValueError(f"The {action_type} action requires exactly one target.")
    action: dict[str, Any] = {"type": action_type, "targets": targets, "duration": duration}
    if action_type == "move":
        action["x"] = _number(raw.get("x"), "move x", -6.4, 6.4)
        action["y"] = _number(raw.get("y"), "move y", -2.8, 2.5)
    elif action_type == "shift":
        action["dx"] = _number(raw.get("dx"), "shift dx", -6.0, 6.0)
        action["dy"] = _number(raw.get("dy"), "shift dy", -4.0, 4.0)
    elif action_type in {"highlight", "color"}:
        action["color"] = _color(raw.get("color", "YELLOW"))
    elif action_type == "transform_text":
        target = targets[0]
        if object_by_id[target]["kind"] != "text":
            raise ValueError("transform_text can target only a text object.")
        action["text"] = _text(raw.get("text"), "replacement text", 90)
        action["color"] = _color(raw.get("color", object_by_id[target]["color"]))
    elif action_type == "scale":
        action["factor"] = _number(raw.get("factor"), "scale factor", 0.5, 1.8)
    elif action_type == "rotate":
        action["angle"] = _number(raw.get("angle"), "rotation angle", -180, 180)
    return action


def _compile_object(visual: dict[str, Any]) -> list[str]:
    variable = _variable(visual["id"])
    x, y = _format_number(visual["x"]), _format_number(visual["y"])
    color = visual["color"]
    kind = visual["kind"]
    if kind == "text":
        return [
            f"        {variable} = Text({_literal(visual['label'])}, font_size={visual['font_size']}, color={color})",
            f"        {variable}.move_to([{x}, {y}, 0])",
        ]
    if kind in {"box", "circle"}:
        shape = f"{variable}_shape"
        label = f"{variable}_label"
        if kind == "box":
            shape_call = (
                f"RoundedRectangle(width={_format_number(visual['width'])}, height={_format_number(visual['height'])}, "
                f"corner_radius=0.14, color={color}, fill_color={color}, fill_opacity=0.16)"
            )
            label_text = _wrapped_label(visual["label"], visual["width"])
        else:
            shape_call = f"Circle(radius={_format_number(visual['radius'])}, color={color}, fill_color={color}, fill_opacity=0.16)"
            label_text = _wrapped_label(visual["label"], visual["radius"] * 2)
        return [
            f"        {shape} = {shape_call}",
            f"        {label} = Text({_literal(label_text)}, font_size={visual['font_size']}, color=WHITE)",
            f"        {variable} = VGroup({shape}, {label})",
            f"        {variable}.move_to([{x}, {y}, 0])",
        ]
    if kind == "dot":
        return [f"        {variable} = Dot([{x}, {y}, 0], radius={_format_number(visual['radius'])}, color={color})"]

    to_x, to_y = _format_number(visual["to_x"]), _format_number(visual["to_y"])
    constructor = "Arrow" if kind == "arrow" else "Line"
    base = f"{constructor}([{x}, {y}, 0], [{to_x}, {to_y}, 0], color={color}"
    base += ", buff=0.08)" if kind == "arrow" else ")"
    if not visual["label"]:
        return [f"        {variable} = {base}"]
    line = f"{variable}_line"
    label = f"{variable}_label"
    midpoint_x = (visual["x"] + visual["to_x"]) / 2
    midpoint_y = (visual["y"] + visual["to_y"]) / 2 + 0.28
    return [
        f"        {line} = {base}",
        f"        {label} = Text({_literal(visual['label'])}, font_size={visual['font_size']}, color={color})",
        f"        {label}.move_to([{_format_number(midpoint_x)}, {_format_number(midpoint_y)}, 0])",
        f"        {variable} = VGroup({line}, {label})",
    ]


def _loop_plan(question: str) -> dict[str, Any]:
    objects: list[dict[str, Any]] = [
        {"id": "item_a", "kind": "box", "label": "A", "x": -3, "y": 0, "width": 1.2, "color": "BLUE"},
        {"id": "item_b", "kind": "box", "label": "B", "x": -1, "y": 0, "width": 1.2, "color": "BLUE"},
        {"id": "item_c", "kind": "box", "label": "C", "x": 1, "y": 0, "width": 1.2, "color": "BLUE"},
        {"id": "item_d", "kind": "box", "label": "D", "x": 3, "y": 0, "width": 1.2, "color": "BLUE"},
        {"id": "pointer", "kind": "arrow", "x": -3, "y": 2.1, "to_x": -3, "to_y": 0.8, "color": "YELLOW"},
        {"id": "status", "kind": "text", "label": "Start the loop", "x": 0, "y": -1.8, "color": "WHITE", "font_size": 25},
    ]
    actions: list[dict[str, Any]] = [
        {"type": "create", "targets": ["item_a", "item_b", "item_c", "item_d"], "duration": 1},
        {"type": "create", "target": "pointer", "duration": 0.6},
        {"type": "write", "target": "status", "duration": 0.6},
    ]
    for index, (item, x, label) in enumerate((("item_a", -3, "A"), ("item_b", -1, "B"), ("item_c", 1, "C"), ("item_d", 3, "D"))):
        if index:
            actions.append({"type": "move", "target": "pointer", "x": x, "y": 1.45, "duration": 0.6})
        actions.extend([
            {"type": "highlight", "target": item, "color": "YELLOW", "duration": 0.55},
            {"type": "transform_text", "target": "status", "text": f"Current item: {label}", "color": "GREEN", "duration": 0.45},
            {"type": "color", "target": item, "color": "GREEN", "duration": 0.35},
        ])
    actions.extend([
        {"type": "transform_text", "target": "status", "text": "Every item was visited", "color": "GREEN", "duration": 0.6},
        {"type": "wait", "duration": 1.5},
    ])
    return {"title": _plain_text(question)[:72], "objects": objects, "actions": actions}


def _recursion_plan(question: str) -> dict[str, Any]:
    objects = [
        {"id": "frame_3", "kind": "box", "label": "call(3)", "x": 0, "y": -1.35, "width": 3.2, "color": "BLUE"},
        {"id": "frame_2", "kind": "box", "label": "call(2)", "x": 0, "y": -0.35, "width": 3.2, "color": "TEAL"},
        {"id": "frame_1", "kind": "box", "label": "call(1)", "x": 0, "y": 0.65, "width": 3.2, "color": "PURPLE"},
        {"id": "base", "kind": "box", "label": "base case", "x": 0, "y": 1.65, "width": 3.2, "color": "GREEN"},
        {"id": "status", "kind": "text", "label": "Calls enter the stack", "x": -3.8, "y": 0, "color": "WHITE", "font_size": 23},
    ]
    actions = [
        {"type": "write", "target": "status", "duration": 0.5},
        {"type": "show", "target": "frame_3", "duration": 0.55},
        {"type": "show", "target": "frame_2", "duration": 0.55},
        {"type": "show", "target": "frame_1", "duration": 0.55},
        {"type": "show", "target": "base", "duration": 0.55},
        {"type": "highlight", "target": "base", "color": "YELLOW", "duration": 0.7},
        {"type": "transform_text", "target": "status", "text": "Base case returns", "color": "GREEN", "duration": 0.5},
        {"type": "fade_out", "target": "base", "duration": 0.45},
        {"type": "fade_out", "target": "frame_1", "duration": 0.45},
        {"type": "fade_out", "target": "frame_2", "duration": 0.45},
        {"type": "fade_out", "target": "frame_3", "duration": 0.45},
        {"type": "transform_text", "target": "status", "text": "Results unwind to the caller", "color": "GREEN", "duration": 0.6},
        {"type": "wait", "duration": 1.5},
    ]
    return {"title": _plain_text(question)[:72], "objects": objects, "actions": actions}


def _binary_search_plan(question: str) -> dict[str, Any]:
    values = (2, 5, 8, 12, 16, 23, 38)
    positions = (-4.5, -3, -1.5, 0, 1.5, 3, 4.5)
    objects: list[dict[str, Any]] = [
        {"id": f"value_{index}", "kind": "box", "label": str(value), "x": x, "y": 0, "width": 1.15, "color": "BLUE"}
        for index, (value, x) in enumerate(zip(values, positions))
    ]
    objects.extend([
        {"id": "pointer", "kind": "arrow", "x": 0, "y": 2.0, "to_x": 0, "to_y": 0.8, "color": "YELLOW"},
        {"id": "status", "kind": "text", "label": "Check the middle", "x": 0, "y": -1.7, "color": "WHITE", "font_size": 24},
    ])
    actions = [
        {"type": "create", "targets": [f"value_{index}" for index in range(7)], "duration": 1},
        {"type": "create", "target": "pointer", "duration": 0.5},
        {"type": "write", "target": "status", "duration": 0.5},
        {"type": "highlight", "target": "value_3", "color": "YELLOW", "duration": 0.7},
        {"type": "transform_text", "target": "status", "text": "Discard one impossible half", "color": "ORANGE", "duration": 0.5},
        {"type": "fade_out", "targets": ["value_0", "value_1", "value_2"], "duration": 0.8},
        {"type": "move", "target": "pointer", "x": 3, "y": 1.4, "duration": 0.65},
        {"type": "highlight", "target": "value_5", "color": "YELLOW", "duration": 0.7},
        {"type": "fade_out", "targets": ["value_3", "value_4"], "duration": 0.65},
        {"type": "color", "target": "value_5", "color": "GREEN", "duration": 0.5},
        {"type": "transform_text", "target": "status", "text": "Search space shrinks each step", "color": "GREEN", "duration": 0.6},
        {"type": "wait", "duration": 1.5},
        {"type": "fade_out", "target": "value_6", "duration": 0.4},
    ]
    return {"title": _plain_text(question)[:72], "objects": objects, "actions": actions}


def _concept_flow_plan(question: str, explanation: str) -> dict[str, Any]:
    points = _learning_points(explanation)
    objects = [
        {"id": "input", "kind": "circle", "label": points[0], "x": -4.2, "y": 0.5, "radius": 1.15, "font_size": 18, "color": "BLUE"},
        {"id": "process", "kind": "box", "label": points[1], "x": 0, "y": 0.5, "width": 3.2, "height": 1.6, "font_size": 18, "color": "PURPLE"},
        {"id": "result", "kind": "circle", "label": points[2], "x": 4.2, "y": 0.5, "radius": 1.15, "font_size": 18, "color": "GREEN"},
        {"id": "flow_1", "kind": "arrow", "x": -2.9, "y": 0.5, "to_x": -1.8, "to_y": 0.5, "color": "WHITE"},
        {"id": "flow_2", "kind": "arrow", "x": 1.8, "y": 0.5, "to_x": 2.9, "to_y": 0.5, "color": "WHITE"},
        {"id": "token", "kind": "dot", "x": -4.2, "y": -1.45, "radius": 0.16, "color": "YELLOW"},
        {"id": "status", "kind": "text", "label": points[0], "x": 0, "y": -2.2, "font_size": 22, "color": "WHITE"},
    ]
    actions = [
        {"type": "create", "targets": ["input", "process", "result"], "duration": 0.9},
        {"type": "create", "targets": ["flow_1", "flow_2"], "duration": 0.65},
        {"type": "show", "target": "token", "duration": 0.35},
        {"type": "write", "target": "status", "duration": 0.5},
        {"type": "highlight", "target": "input", "color": "YELLOW", "duration": 0.6},
        {"type": "move", "target": "token", "x": 0, "y": -1.45, "duration": 0.9},
        {"type": "transform_text", "target": "status", "text": points[1], "color": "PURPLE", "duration": 0.5},
        {"type": "highlight", "target": "process", "color": "YELLOW", "duration": 0.6},
        {"type": "rotate", "target": "process", "angle": 5, "duration": 0.35},
        {"type": "move", "target": "token", "x": 4.2, "y": -1.45, "duration": 0.9},
        {"type": "transform_text", "target": "status", "text": points[2], "color": "GREEN", "duration": 0.5},
        {"type": "highlight", "target": "result", "color": "YELLOW", "duration": 0.6},
        {"type": "wait", "duration": 1.5},
    ]
    return {"title": _plain_text(question)[:72], "objects": objects, "actions": actions}


def _learning_points(explanation: str) -> list[str]:
    points: list[str] = []
    for line in explanation.splitlines():
        line = re.sub(r"^\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)", "", line)
        line = _plain_text(line)
        if len(line) >= 5 and line not in points:
            points.append(line)
    defaults = ("Input", "Transformation", "Result")
    for default in defaults:
        if len(points) >= 3:
            break
        points.append(default)
    return [_short_label(point) for point in points[:3]]


def _short_label(value: str) -> str:
    words = value.split()
    text = " ".join(words[:6])
    return text[:42]


def _wrapped_label(value: str, width: float) -> str:
    characters = max(8, min(26, int(width * 7)))
    return "\n".join(textwrap.wrap(value, width=characters, break_long_words=False)[:2])


def _object_center(visual: dict[str, Any]) -> tuple[float, float]:
    if visual["kind"] in {"arrow", "line"}:
        return ((visual["x"] + visual["to_x"]) / 2, (visual["y"] + visual["to_y"]) / 2)
    return (visual["x"], visual["y"])


def _variable(object_id: str) -> str:
    return f"visual_{object_id}"


def _text(value: Any, field: str, maximum: int) -> str:
    text = _plain_text(str(value or ""))
    if not text or len(text) > maximum:
        raise ValueError(f"The animation {field} must contain 1 to {maximum} characters.")
    return text


def _plain_text(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    text = re.sub(r"[`*_~<>]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _color(value: Any) -> str:
    color = str(value or "").strip().upper()
    if color not in COLORS:
        raise ValueError(f"The animation color {color!r} is not supported.")
    return color


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"The animation {field} must be a number.")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"The animation {field} must be between {minimum} and {maximum}.")
    return number


def _format_number(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".") or "0"


def _literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
