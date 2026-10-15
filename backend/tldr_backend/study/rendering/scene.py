"""Trusted Manim program. JSON selects primitives and bounded math, never code."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import textwrap

from manim import (Scene, Text, VGroup, Group, ImageMobject, SVGMobject, Circle, Rectangle, Triangle, Line, Arrow,
                   Dot, Axes, VMobject, FadeIn, FadeOut, Indicate, Create,
                   tempconfig, UP, DOWN, LEFT, RIGHT, BLUE_C, TEAL_C, YELLOW, WHITE,
                   MoveAlongPath, linear)

from .schema import calculate


def label(value, size=24, width=50, color=WHITE):
    value = "\n".join(textwrap.fill(line, width=width) for line in str(value).splitlines())
    return Text(value, font="Arial", font_size=size, color=color, disable_ligatures=True)


def primitive(obj, trusted_assets=None, trusted_math=None):
    title = label(obj["label"], 25, 40, TEAL_C)
    kind = obj["kind"]
    if kind=='equation' and obj.get('latex'):
        import hashlib
        from .math_svg import checked_svg
        asset=(trusted_math or {}).get(obj['id'])
        if not asset or set(asset)!={'path','sha256'}:raise ValueError('Missing trusted equation asset.')
        path=Path(asset['path']).resolve()
        if not path.is_file() or path.suffix!='.svg' or hashlib.sha256(path.read_bytes()).hexdigest()!=asset['sha256']:
            raise ValueError('Equation asset changed or is missing.')
        checked_svg(path.read_text(encoding='utf-8'))
        body=SVGMobject(str(path),color=WHITE,height=1.7)
        if body.height>3:body.scale_to_fit_height(3)
    elif kind in {"text", "equation"}:
        body = label(obj["text"], 32 if kind == "equation" else 25, 42)
    elif kind == "geometry":
        body = {"circle": Circle, "rectangle": Rectangle, "triangle": Triangle}[obj["shape"]](color=BLUE_C)
        body.set_fill(BLUE_C, opacity=.12)
    elif kind == "plot":
        points = calculate(**obj["calculation"])["points"] if obj.get("calculation",{}).get("kind") in {"quadratic_plot","ohms_law_plot"} else obj["points"]
        x, y = zip(*points)
        ymin, ymax = min(y), max(y)
        margin = max((ymax-ymin)*.1, 1e-3)
        axes = Axes(x_range=[min(x), max(x), (max(x)-min(x))/4], y_range=[ymin-margin, ymax+margin, max((ymax-ymin+2*margin)/4, .001)], x_length=7, y_length=2.5, tips=False, axis_config={"include_numbers": False})
        line = axes.plot_line_graph(x_values=x, y_values=y, add_vertex_dots=True, line_color=TEAL_C, vertex_dot_radius=.035)
        ends = VGroup(label(f"x: {min(x):g} to {max(x):g}", 16), label(f"y: {ymin:g} to {ymax:g}", 16)).arrange(RIGHT, buff=.5).next_to(axes, DOWN, buff=.12)
        body = VGroup(axes, line, ends)
    elif kind == "source_image":
        asset=(trusted_assets or {}).get(obj["source_ref"])
        if not asset or set(asset)-{"path","sha256","width","height","crop","provenance"}:
            raise ValueError(f"Missing trusted source asset: {obj['source_ref']}")
        path=Path(asset["path"]).resolve()
        if not path.is_file() or path.suffix.lower()!=".png":
            raise ValueError(f"Invalid trusted source asset: {obj['source_ref']}")
        body=ImageMobject(str(path))
        if body.width>10.5: body.scale_to_fit_width(10.5)
        if body.height>4.35: body.scale_to_fit_height(4.35)
        overlays=VGroup()
        for box in obj.get("overlays",[]):
            rectangle=Rectangle(width=body.width*box["width"],height=body.height*box["height"],color=YELLOW,stroke_width=5)
            rectangle.move_to([body.get_left()[0]+body.width*(box["x"]+box["width"]/2),body.get_top()[1]-body.height*(box["y"]+box["height"]/2),0])
            overlays.add(rectangle)
        body=Group(body,overlays)
    elif kind == "circuit":
        # The only supported electrical topology: ideal DC source and one resistor.
        source_x, resistor_x, top, bottom = -3., 2.8, 1., -1.
        long_plate = Line([source_x-.15, -.55, 0], [source_x-.15, .55, 0], color=YELLOW)
        short_plate = Line([source_x+.15, -.3, 0], [source_x+.15, .3, 0], color=YELLOW)
        # Rotate the two plates so they interrupt the vertical left branch.
        battery = VGroup(long_plate, short_plate).rotate(-1.57079632679).move_to([source_x, 0, 0])
        wire = VGroup(Line([source_x,.15,0],[source_x,top,0]), Line([source_x,top,0],[resistor_x,top,0]),
                      Line([resistor_x,top,0],[resistor_x,.65,0]), Line([resistor_x,-.65,0],[resistor_x,bottom,0]),
                      Line([resistor_x,bottom,0],[source_x,bottom,0]), Line([source_x,bottom,0],[source_x,-.15,0]))
        zig = [[resistor_x, .65, 0]] + [[resistor_x + (.22 if i%2==0 else -.22), .5-i*.2, 0] for i in range(6)] + [[resistor_x,-.65,0]]
        resistor = VMobject(color=TEAL_C).set_points_as_corners(zig)
        ground = VGroup(Line([0,bottom,0],[0,bottom-.3,0]), *[Line([-.35+i*.1,bottom-.3-i*.13,0],[.35-i*.1,bottom-.3-i*.13,0]) for i in range(3)])
        source_label = label(obj["nodes"][0], 22, 18).next_to(battery, LEFT, buff=.3)
        resistor_label = label(obj["nodes"][1], 22, 18).next_to(resistor, RIGHT, buff=.3)
        body = VGroup(wire, battery, resistor, ground, source_label, resistor_label,
                      label("+", 22, color=YELLOW).move_to(battery.get_top()+LEFT*.8+UP*.1),
                      label("−", 22).move_to(battery.get_bottom()+LEFT*.8+DOWN*.1))
        current_path = VMobject().set_points_as_corners([[source_x,top,0],[resistor_x,top,0],[resistor_x,bottom,0],[source_x,bottom,0]])
        # Keep invisible paths in the group so resizing transforms them consistently.
        current_path.set_opacity(0)
        body.add(current_path)
        body.motion_paths = [current_path]
    elif kind in {"process", "bus"}:
        nodes = VGroup()
        for name in obj["nodes"]:
            node_text = label(name, 22, 14)
            box = Rectangle(width=max(1.9, node_text.width+.35), height=max(1.8 if kind == "bus" else 1., node_text.height+.25), color=BLUE_C)
            nodes.add(VGroup(box, node_text))
        nodes.arrange(RIGHT, buff=.65)
        links = VGroup(*[Arrow(nodes[i].get_right(), nodes[i+1].get_left(), buff=.08, color=YELLOW, max_tip_length_to_length_ratio=.2) for i in range(len(nodes)-1)])
        body = VGroup(nodes, links)
        if kind == "bus":
            nodes.arrange(RIGHT, buff=5)
            body.remove(links)
            paths = []
            for i, (name, reverse) in enumerate([("Address", False), ("Read request", False), ("Read data", True)]):
                y = .65-i*.65
                a, b = nodes[0].get_right()+UP*y, nodes[-1].get_left()+UP*y
                arrow = Arrow(b if reverse else a, a if reverse else b, buff=.08, color=TEAL_C if reverse else BLUE_C)
                body.add(arrow, label(name, 18, 25).next_to(arrow, UP, buff=.05))
                paths.append(arrow)
            body.motion_paths = paths
    elif kind == "timing":
        rows = VGroup()
        for signal in obj["signals"]:
            values = signal["values"]
            points = []
            for i, value in enumerate(values):
                points.extend([[i*.5, value*.45, 0], [(i+1)*.5, value*.45, 0]])
            wave = VMobject(color=TEAL_C).set_points_as_corners(points)
            name = label(signal["name"], 18, 16).next_to(wave, LEFT, buff=.3)
            rows.add(VGroup(name, wave))
        # Align waveform endpoints; label widths must not shift the time origin.
        rows.arrange(DOWN, aligned_edge=RIGHT, buff=.4)
        body = VGroup(rows, label("Time →   (pedagogical, not to scale)", 16).next_to(rows, DOWN))
        first_wave = rows[0][1]
        body.cursor_start = Line([first_wave.get_left()[0],rows.get_top()[1]+.15,0], [first_wave.get_left()[0],rows.get_bottom()[1]-.15,0], color=YELLOW)
        body.cursor_end = body.cursor_start.copy().shift(RIGHT*first_wave.width)
        body.cursor_start.set_opacity(0)
        body.cursor_end.set_opacity(0)
        body.add(body.cursor_start, body.cursor_end)
        body.sample_fraction = next((next((i/len(s["values"]) for i,v in enumerate(s["values"]) if v), .6) for s in obj["signals"] if "sample" in s["name"].lower()), .6)
    else:
        raise ValueError(f"Unsupported visual primitive: {kind}")
    if body.width > 10.5:
        body.scale_to_fit_width(10.5)
    group = Group(title, body).arrange(DOWN, buff=.3)
    group.visual_body = body
    group.visual_kind = kind
    if "calculation" in obj:
        result = calculate(**obj["calculation"])
        values = [f"{k.replace('_',' ')}: {v:.6g}" if isinstance(v, (float,int)) else f"{k.replace('_',' ')}: {v}" for k,v in result.items() if k not in {"phases", "verification", "assumptions", "points"}]
        if values:
            summary = label(" | ".join(values), 18, 70, YELLOW)
            group.add(summary.next_to(group, DOWN, buff=.2))
            if kind == "timing":
                summary.set_opacity(0)
                group.sample_result = summary
    return group


def render(request):
    data = request["scene"]
    duration = request["duration_seconds"]

    class DeclarativeScene(Scene):
        def construct(self):
            title = label(data["title"], 33, 64)
            if title.width > 12.5:
                title.scale_to_fit_width(12.5)
            # Use the final title bounds after fitting; reserve a visible top margin.
            title.move_to([0, 3.35-title.height/2, 0])
            self.add(title)
            objects = {o["id"]: o for o in data["objects"]}
            previous = None
            for index, step in enumerate(data["steps"]):
                slot = request.get("step_durations", [duration/len(data["steps"])]*len(data["steps"]))[index]
                groups = Group(*[primitive(objects[id_], request.get("trusted_assets"), request.get('trusted_math')) for id_ in step["object_ids"]])
                groups.arrange_in_grid(cols=1 if len(groups) <= 2 else 2, buff=.45)
                if groups.width > 12:
                    groups.scale_to_fit_width(12)
                if groups.height > 4.8:
                    groups.scale_to_fit_height(4.8)
                groups.move_to([0, .05, 0])
                caption = label(step["caption"], 23, 90, YELLOW).to_edge(DOWN, buff=.45)
                if caption.width > 12.8:
                    caption.scale_to_fit_width(12.8)
                current = Group(groups, caption)
                fade = min(.45, slot*.15)
                animations = [FadeIn(current, shift=UP*.1)]
                if previous is not None:
                    animations.append(FadeOut(previous))
                self.play(*animations, run_time=fade)
                remaining = max(1/30, slot-fade)
                # Animate the domain mechanism, not merely the containing card.
                for visual in groups:
                    body = visual.visual_body
                    allotted = remaining / len(groups)
                    if visual.visual_kind in {"bus", "circuit"}:
                        paths = body.motion_paths
                        for path in paths:
                            token = Dot(path.get_start(), radius=.09, color=YELLOW)
                            self.add(token)
                            self.play(MoveAlongPath(token, path), run_time=allotted/len(paths), rate_func=linear)
                            self.remove(token)
                    elif visual.visual_kind == "timing":
                        cursor = body.cursor_start.copy().set_opacity(1)
                        self.add(cursor)
                        span = body.cursor_end.get_center()-body.cursor_start.get_center()
                        fraction = max(.05, min(.8, body.sample_fraction))
                        self.play(cursor.animate.shift(span*fraction), run_time=allotted*fraction, rate_func=linear)
                        sample_animations = [Indicate(cursor, color=TEAL_C, scale_factor=1.05)]
                        if hasattr(visual, "sample_result"):
                            sample_animations.append(visual.sample_result.animate.set_opacity(1))
                        self.play(*sample_animations, run_time=allotted*.1)
                        self.play(cursor.animate.shift(span*(1-fraction)), run_time=allotted*(.9-fraction), rate_func=linear)
                        self.remove(cursor)
                    elif visual.visual_kind in {"plot", "geometry"}:
                        self.remove(body)
                        self.play(Create(body), run_time=min(3., allotted*.7))
                        self.wait(max(1/30, allotted-min(3., allotted*.7)))
                    elif visual.visual_kind == "source_image":
                        self.wait(allotted)
                    else:
                        self.play(Indicate(body, scale_factor=1.025, color=TEAL_C), run_time=min(1., allotted*.2))
                        self.wait(max(1/30, allotted-min(1., allotted*.2)))
                previous = current

    folder = Path(request["output_dir"])
    config = request["config"]
    with tempconfig({"pixel_width": config["width"], "pixel_height": config["height"], "frame_rate": config["fps"], "media_dir": str(folder / "media"), "output_file": "visual", "disable_caching": True, "write_to_movie": True, "preview": False, "background_color": "#101923", "verbosity": "WARNING"}):
        scene = DeclarativeScene()
        scene.render()
        rendered = Path(scene.renderer.file_writer.movie_file_path)
        import shutil
        shutil.copyfile(rendered, folder / "visual.mp4")


if __name__ == "__main__":
    render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    # This module is a disposable render worker. Scene.render has closed the
    # movie writer and the final file has been copied. Manim/PyAV can leave a
    # native shutdown thread alive on Windows after that point; skip interpreter
    # teardown in this child only. The parent independently probes the completed
    # media before it can receive a cache completion marker.
    if sys.platform == "win32":
        import os
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
