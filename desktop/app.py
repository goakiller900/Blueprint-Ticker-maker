"""Blueprint Ticker Maker desktop application.

Offline Tkinter GUI: no telemetry, no network access, and no automatic file writes.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from .blueprint_core import (
        ANIMATION_LABELS, BUILTIN_PRESETS, CIRCUIT_LAYOUT_LABELS, LAMP_COLORS, MODE_LABELS,
        TickerConfig, generate, generate_blueprint_book, project_as_json, project_from_json,
    )
    from .catalog import FONT_5X7
except ImportError:
    from blueprint_core import (
        ANIMATION_LABELS, BUILTIN_PRESETS, CIRCUIT_LAYOUT_LABELS, LAMP_COLORS, MODE_LABELS,
        TickerConfig, generate, generate_blueprint_book, project_as_json, project_from_json,
    )
    from catalog import FONT_5X7

APP_NAME = "Blueprint Ticker Maker"
APP_VERSION = "0.2.0"


def _reverse_lookup(mapping: dict[str, str], value: str, fallback: str) -> str:
    for key, label in mapping.items():
        if label == value:
            return key
    return fallback


class FontEditor(tk.Toplevel):
    def __init__(self, parent: "BlueprintTickerApp") -> None:
        super().__init__(parent)
        self.parent_app = parent
        self.title("5×7 Font Editor")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.character_var = tk.StringVar(value="A")
        self.cells = [[False] * 5 for _ in range(7)]
        self.buttons: list[list[ttk.Button]] = []
        self._build()
        self._load_character()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        top = ttk.Frame(outer)
        top.pack(fill="x")
        ttk.Label(top, text="Character").pack(side="left")
        chars = sorted(set(FONT_5X7) | set(self.parent_app.custom_font))
        combo = ttk.Combobox(top, textvariable=self.character_var, values=chars, width=8)
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._load_character())
        ttk.Button(top, text="Load", command=self._load_character).pack(side="left")

        grid = ttk.Frame(outer, padding=(0, 10))
        grid.pack()
        for y in range(7):
            row: list[ttk.Button] = []
            for x in range(5):
                button = ttk.Button(grid, width=3, command=lambda yy=y, xx=x: self._toggle(yy, xx))
                button.grid(row=y, column=x, padx=1, pady=1)
                row.append(button)
            self.buttons.append(row)

        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        ttk.Button(actions, text="Save glyph", command=self._save).pack(side="left", padx=2)
        ttk.Button(actions, text="Reset built-in", command=self._reset).pack(side="left", padx=2)
        ttk.Button(actions, text="Import font JSON", command=self._import).pack(side="left", padx=2)
        ttk.Button(actions, text="Export font JSON", command=self._export).pack(side="left", padx=2)
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right", padx=2)

    def _character(self) -> str:
        value = self.character_var.get().upper()
        if len(value) != 1:
            raise ValueError("Enter exactly one character.")
        return value

    def _load_character(self) -> None:
        try:
            character = self._character()
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return
        rows = self.parent_app.custom_font.get(character)
        if rows is None:
            rows = list(FONT_5X7.get(character, ("00000",) * 7))
        self.cells = [[bit == "1" for bit in row] for row in rows]
        self._refresh()

    def _toggle(self, y: int, x: int) -> None:
        self.cells[y][x] = not self.cells[y][x]
        self._refresh()

    def _refresh(self) -> None:
        for y in range(7):
            for x in range(5):
                self.buttons[y][x].configure(text="█" if self.cells[y][x] else "·")

    def _save(self) -> None:
        try:
            character = self._character()
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return
        self.parent_app.custom_font[character] = [
            "".join("1" if cell else "0" for cell in row) for row in self.cells
        ]
        self.parent_app.status_var.set(f"Saved custom glyph {character!r} in the current project.")

    def _reset(self) -> None:
        try:
            character = self._character()
        except ValueError:
            return
        self.parent_app.custom_font.pop(character, None)
        self._load_character()

    def _import(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Import font JSON", filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Font JSON must be an object mapping characters to seven rows.")
            for char, rows in data.items():
                if len(str(char)) != 1 or not isinstance(rows, list):
                    raise ValueError(f"Invalid glyph entry for {char!r}.")
                if len(rows) != 7 or any(len(str(row)) != 5 or set(str(row)) - {"0", "1"} for row in rows):
                    raise ValueError(f"Glyph {char!r} is not 5×7 binary data.")
            self.parent_app.custom_font.update({str(k).upper(): [str(r) for r in v] for k, v in data.items()})
            self._load_character()
        except Exception as error:
            messagebox.showerror(APP_NAME, f"Could not import font:\n\n{error}", parent=self)

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Export font JSON", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self.parent_app.custom_font, indent=2, ensure_ascii=False), encoding="utf-8")


class BlueprintTickerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(1050, 760)
        self.geometry("1280x900")
        self.result = None
        self.preview_index = 0
        self.preview_job: str | None = None
        self.custom_font: dict[str, list[str]] = {}

        self.mode_var = tk.StringVar(value=MODE_LABELS["lamp-compact"])
        self.preset_var = tk.StringVar(value="Standard ticker 24×7")
        self.seconds_var = tk.StringVar(value="0.20")
        self.direction_var = tk.StringVar(value="left")
        self.animation_var = tk.StringVar(value=ANIMATION_LABELS["loop"])
        self.width_var = tk.StringVar(value="24")
        self.height_var = tk.StringVar(value="7")
        self.spacing_var = tk.StringVar(value="1")
        self.gap_var = tk.StringVar(value="6")
        self.start_padding_var = tk.StringVar(value="0")
        self.end_padding_var = tk.StringVar(value="0")
        self.pixel_width_var = tk.StringVar(value="1")
        self.pixel_height_var = tk.StringVar(value="1")
        self.color_var = tk.StringVar(value="yellow")
        self.rom_columns_var = tk.StringVar(value="0")
        self.edge_spaces_var = tk.StringVar(value="1")
        self.pause_var = tk.StringVar(value="0")
        self.full_pause_var = tk.StringVar(value="0")
        self.layout_var = tk.StringVar(value=CIRCUIT_LAYOUT_LABELS["compact-square"])
        self.h_align_var = tk.StringVar(value="center")
        self.v_align_var = tk.StringVar(value="middle")
        self.line_spacing_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value="Offline application — no telemetry and no network access.")
        self.stats_var = tk.StringVar(value="No blueprint generated yet.")
        self.warning_var = tk.StringVar(value="")

        self._build_ui()
        self._set_message("THE FACTORY GROWS!!")
        self._update_mode_state()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x")
        ttk.Label(heading, text=APP_NAME, font=("TkDefaultFont", 18, "bold")).pack(side="left")
        ttk.Label(heading, text="Factorio 2.1 display & ticker generator").pack(side="left", padx=(14, 0), pady=(7, 0))
        ttk.Label(heading, text="OFFLINE", foreground="#138a36", font=("TkDefaultFont", 10, "bold")).pack(side="right")
        ttk.Separator(outer).pack(fill="x", pady=10)

        content = ttk.Panedwindow(outer, orient="horizontal")
        content.pack(fill="both", expand=True)
        left_host = ttk.Frame(content)
        output = ttk.Frame(content)
        content.add(left_host, weight=1)
        content.add(output, weight=2)

        canvas = tk.Canvas(left_host, highlightthickness=0, width=420)
        scrollbar = ttk.Scrollbar(left_host, orient="vertical", command=canvas.yview)
        controls = ttk.Frame(canvas, padding=(0, 0, 10, 0))
        controls.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=controls, anchor="nw", width=400)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._build_controls(controls)
        self._build_output(output)
        ttk.Label(outer, textvariable=self.status_var, anchor="w", relief="sunken", padding=(7, 4)).pack(fill="x", pady=(10, 0))

    def _entry_row(self, frame, row, label, variable):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        return entry

    def _build_controls(self, parent: ttk.Frame) -> None:
        preset = ttk.LabelFrame(parent, text="Presets & project", padding=10)
        preset.pack(fill="x")
        ttk.Combobox(preset, textvariable=self.preset_var, values=tuple(BUILTIN_PRESETS), state="readonly").grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(preset, text="Apply preset", command=self.apply_preset).grid(row=1, column=0, sticky="ew", padx=(0, 2))
        ttk.Button(preset, text="Load project", command=self.load_project).grid(row=1, column=1, sticky="ew", padx=(2, 0))
        ttk.Button(preset, text="Save project", command=self.save_project).grid(row=2, column=0, sticky="ew", padx=(0, 2), pady=2)
        ttk.Button(preset, text="5×7 font editor", command=lambda: FontEditor(self)).grid(row=2, column=1, sticky="ew", padx=(2, 0), pady=2)
        preset.columnconfigure((0, 1), weight=1)

        general = ttk.LabelFrame(parent, text="Display", padding=10)
        general.pack(fill="x", pady=(8, 0))
        ttk.Label(general, text="Mode").grid(row=0, column=0, sticky="w")
        self.mode_combo = ttk.Combobox(general, textvariable=self.mode_var, state="readonly", values=tuple(MODE_LABELS.values()))
        self.mode_combo.grid(row=0, column=1, sticky="ew", pady=2)
        self.mode_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_mode_state())
        ttk.Label(general, text="Message").grid(row=1, column=0, sticky="nw", pady=2)
        self.message_text = tk.Text(general, height=4, width=28, wrap="word")
        self.message_text.grid(row=1, column=1, sticky="ew", pady=2)
        self._entry_row(general, 2, "Logical width", self.width_var)
        self._entry_row(general, 3, "Logical height", self.height_var)
        self._entry_row(general, 4, "Pixel lamps wide", self.pixel_width_var)
        self._entry_row(general, 5, "Pixel lamps high", self.pixel_height_var)
        general.columnconfigure(1, weight=1)

        motion = ttk.LabelFrame(parent, text="Animation", padding=10)
        motion.pack(fill="x", pady=(8, 0))
        ttk.Label(motion, text="Behaviour").grid(row=0, column=0, sticky="w")
        self.animation_combo = ttk.Combobox(motion, textvariable=self.animation_var, values=tuple(ANIMATION_LABELS.values()), state="readonly")
        self.animation_combo.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(motion, text="Direction").grid(row=1, column=0, sticky="w")
        self.direction_combo = ttk.Combobox(motion, textvariable=self.direction_var, values=("left", "right"), state="readonly")
        self.direction_combo.grid(row=1, column=1, sticky="ew", pady=2)
        self._entry_row(motion, 2, "Seconds per step", self.seconds_var)
        self._entry_row(motion, 3, "Pause at repeat (s)", self.pause_var)
        self._entry_row(motion, 4, "Full-message pause (s)", self.full_pause_var)
        motion.columnconfigure(1, weight=1)

        self.lamp_options = ttk.LabelFrame(parent, text="Lamp options", padding=10)
        self.lamp_options.pack(fill="x", pady=(8, 0))
        rows = [
            ("Character spacing", self.spacing_var), ("Blank start padding", self.start_padding_var),
            ("Blank end padding", self.end_padding_var), ("Loop/repeat gap", self.gap_var),
            ("ROM columns (0 auto)", self.rom_columns_var), ("Line spacing", self.line_spacing_var),
        ]
        for row, (label, var) in enumerate(rows):
            self._entry_row(self.lamp_options, row, label, var)
        ttk.Label(self.lamp_options, text="Lamp colour").grid(row=6, column=0, sticky="w")
        ttk.Combobox(self.lamp_options, textvariable=self.color_var, values=tuple(LAMP_COLORS), state="readonly").grid(row=6, column=1, sticky="ew", pady=2)
        ttk.Label(self.lamp_options, text="Circuit/ROM layout").grid(row=7, column=0, sticky="w")
        ttk.Combobox(self.lamp_options, textvariable=self.layout_var, values=tuple(CIRCUIT_LAYOUT_LABELS.values()), state="readonly").grid(row=7, column=1, sticky="ew", pady=2)
        ttk.Label(self.lamp_options, text="Horizontal align").grid(row=8, column=0, sticky="w")
        ttk.Combobox(self.lamp_options, textvariable=self.h_align_var, values=("left", "center", "right"), state="readonly").grid(row=8, column=1, sticky="ew", pady=2)
        ttk.Label(self.lamp_options, text="Vertical align").grid(row=9, column=0, sticky="w")
        ttk.Combobox(self.lamp_options, textvariable=self.v_align_var, values=("top", "middle", "bottom"), state="readonly").grid(row=9, column=1, sticky="ew", pady=2)
        self.lamp_options.columnconfigure(1, weight=1)

        self.nixie_options = ttk.LabelFrame(parent, text="Nixie options", padding=10)
        self.nixie_options.pack(fill="x", pady=(8, 0))
        self._entry_row(self.nixie_options, 0, "Blank edge characters", self.edge_spaces_var)
        self.nixie_options.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(parent, text="Generate & export", padding=10)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Generate blueprint", command=self.generate_blueprint).pack(fill="x", pady=2)
        self.copy_button = ttk.Button(actions, text="Copy blueprint string", command=self.copy_blueprint, state="disabled")
        self.copy_button.pack(fill="x", pady=2)
        self.save_button = ttk.Button(actions, text="Save blueprint .txt", command=self.save_blueprint, state="disabled")
        self.save_button.pack(fill="x", pady=2)
        self.json_button = ttk.Button(actions, text="Save decoded JSON", command=self.save_json, state="disabled")
        self.json_button.pack(fill="x", pady=2)
        ttk.Button(actions, text="Export variant blueprint book", command=self.save_blueprint_book).pack(fill="x", pady=2)

        safety = ttk.LabelFrame(parent, text="Safety", padding=10)
        safety.pack(fill="x", pady=(8, 0))
        ttk.Label(safety, justify="left", wraplength=350, text=(
            "No internet, telemetry, advertisements, automatic updates, Factorio save access, or automatic file writes. "
            "Project/font/blueprint files are written only through an explicit Save action."
        )).pack(anchor="w")

    def _build_output(self, parent: ttk.Frame) -> None:
        preview_box = ttk.LabelFrame(parent, text="Preview", padding=8)
        preview_box.pack(fill="x")
        self.preview_canvas = tk.Canvas(preview_box, height=320, background="#0c0d0f", highlightthickness=0)
        self.preview_canvas.pack(fill="x")
        ttk.Label(preview_box, textvariable=self.stats_var, anchor="w", justify="left", wraplength=760).pack(fill="x", pady=(7, 0))
        ttk.Label(preview_box, textvariable=self.warning_var, anchor="w", justify="left", foreground="#b05a00", wraplength=760).pack(fill="x")
        string_box = ttk.LabelFrame(parent, text="Factorio blueprint string", padding=8)
        string_box.pack(fill="both", expand=True, pady=(10, 0))
        self.output_text = tk.Text(string_box, wrap="char", height=18, font=("TkFixedFont", 9), undo=False)
        scroll = ttk.Scrollbar(string_box, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scroll.set)
        self.output_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _set_message(self, text: str) -> None:
        self.message_text.delete("1.0", "end")
        self.message_text.insert("1.0", text)

    def _message(self) -> str:
        return self.message_text.get("1.0", "end-1c")

    def _mode_key(self) -> str:
        return _reverse_lookup(MODE_LABELS, self.mode_var.get(), "lamp-compact")

    def _animation_key(self) -> str:
        return _reverse_lookup(ANIMATION_LABELS, self.animation_var.get(), "loop")

    def _layout_key(self) -> str:
        return _reverse_lookup(CIRCUIT_LAYOUT_LABELS, self.layout_var.get(), "compact-square")

    def _update_mode_state(self) -> None:
        mode = self._mode_key()
        lamp_mode = mode.startswith("lamp-")
        scrolling = mode in ("lamp-compact", "lamp-compatible", "nixie")
        state = "normal" if lamp_mode else "disabled"
        for child in self.lamp_options.winfo_children():
            try: child.configure(state=state)
            except tk.TclError: pass
        nixie_state = "normal" if mode.startswith("nixie") else "disabled"
        for child in self.nixie_options.winfo_children():
            try: child.configure(state=nixie_state)
            except tk.TclError: pass
        for widget in (self.animation_combo, self.direction_combo):
            widget.configure(state="readonly" if scrolling else "disabled")
        if not scrolling:
            self.animation_var.set(ANIMATION_LABELS["static"])
        elif self._animation_key() == "static":
            self.animation_var.set(ANIMATION_LABELS["loop"])
        if mode == "lamp-compatible":
            try:
                if int(self.width_var.get()) > 36: self.width_var.set("24")
            except ValueError:
                pass

    def _config(self) -> TickerConfig:
        return TickerConfig(
            message=self._message(), mode=self._mode_key(), seconds_per_step=float(self.seconds_var.get()),
            direction=self.direction_var.get(), animation=self._animation_key(), display_width=int(self.width_var.get()),
            display_height=int(self.height_var.get()), character_spacing=int(self.spacing_var.get()),
            repeat_gap=int(self.gap_var.get()), start_padding=int(self.start_padding_var.get()),
            end_padding=int(self.end_padding_var.get()), pixel_width=int(self.pixel_width_var.get()),
            pixel_height=int(self.pixel_height_var.get()), lamp_color=self.color_var.get(),
            rom_columns=int(self.rom_columns_var.get()), nixie_edge_spaces=int(self.edge_spaces_var.get()),
            pause_seconds=float(self.pause_var.get()), full_message_pause_seconds=float(self.full_pause_var.get()),
            circuit_layout=self._layout_key(), horizontal_align=self.h_align_var.get(), vertical_align=self.v_align_var.get(),
            line_spacing=int(self.line_spacing_var.get()), custom_font=dict(self.custom_font),
        )

    def _apply_config(self, config: TickerConfig) -> None:
        self._set_message(config.message)
        self.mode_var.set(MODE_LABELS.get(config.mode, MODE_LABELS["lamp-compact"]))
        self.seconds_var.set(str(config.seconds_per_step)); self.direction_var.set(config.direction)
        self.animation_var.set(ANIMATION_LABELS.get(config.animation, ANIMATION_LABELS["loop"]))
        self.width_var.set(str(config.display_width)); self.height_var.set(str(config.display_height))
        self.spacing_var.set(str(config.character_spacing)); self.gap_var.set(str(config.repeat_gap))
        self.start_padding_var.set(str(config.start_padding)); self.end_padding_var.set(str(config.end_padding))
        self.pixel_width_var.set(str(config.pixel_width)); self.pixel_height_var.set(str(config.pixel_height))
        self.color_var.set(config.lamp_color); self.rom_columns_var.set(str(config.rom_columns))
        self.edge_spaces_var.set(str(config.nixie_edge_spaces)); self.pause_var.set(str(config.pause_seconds))
        self.full_pause_var.set(str(config.full_message_pause_seconds))
        self.layout_var.set(CIRCUIT_LAYOUT_LABELS.get(config.circuit_layout, CIRCUIT_LAYOUT_LABELS["compact-square"]))
        self.h_align_var.set(config.horizontal_align); self.v_align_var.set(config.vertical_align)
        self.line_spacing_var.set(str(config.line_spacing)); self.custom_font = dict(config.custom_font)
        self._update_mode_state()

    def apply_preset(self) -> None:
        name = self.preset_var.get()
        values = BUILTIN_PRESETS.get(name)
        if not values:
            return
        config = self._config()
        data = asdict(config); data.update(values)
        self._apply_config(TickerConfig(**data))
        self.status_var.set(f"Applied preset: {name}")

    def save_project(self) -> None:
        try: config = self._config()
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error), parent=self); return
        path = filedialog.asksaveasfilename(parent=self, title="Save project", defaultextension=".json", filetypes=[("Blueprint Ticker project", "*.json")])
        if path:
            Path(path).write_text(project_as_json(config), encoding="utf-8")
            self.status_var.set(f"Saved project: {Path(path).name}")

    def load_project(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Load project", filetypes=[("Blueprint Ticker project", "*.json"), ("All files", "*.*")])
        if not path: return
        try:
            config = project_from_json(Path(path).read_text(encoding="utf-8"))
            self._apply_config(config)
            self.status_var.set(f"Loaded project: {Path(path).name}")
        except Exception as error:
            messagebox.showerror(APP_NAME, f"Could not load project:\n\n{error}", parent=self)

    def generate_blueprint(self) -> None:
        self.status_var.set("Generating blueprint…"); self.update_idletasks()
        try:
            self.result = generate(self._config())
        except Exception as error:
            self.result = None; self._set_output(""); self._set_action_state(False)
            self.status_var.set(f"Generation failed: {error}")
            messagebox.showerror(APP_NAME, str(error), parent=self); return
        self._set_output(self.result.blueprint_string); self._set_action_state(True)
        s = self.result.stats
        self.stats_var.set(
            f"{s['mode']} | {s['display_lamps_wide']}×{s['display_lamps_high']} physical lamps | "
            f"{s['entities']} entities | {s['deciders']} deciders | {s['arithmetic']} arithmetic | "
            f"{s['frames']} frames | footprint ≈ {s['footprint_width']}×{s['footprint_height']} tiles | "
            f"blueprint {s['blueprint_characters']:,} chars"
        )
        self.warning_var.set("  •  ".join(self.result.warnings))
        self.status_var.set("Blueprint ready.")
        self.preview_index = 0; self._schedule_preview()

    def _set_output(self, text: str) -> None:
        self.output_text.delete("1.0", "end"); self.output_text.insert("1.0", text)

    def _set_action_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in (self.copy_button, self.save_button, self.json_button): button.configure(state=state)

    def copy_blueprint(self) -> None:
        if not self.result: return
        self.clipboard_clear(); self.clipboard_append(self.result.blueprint_string); self.update()
        self.status_var.set("Blueprint copied to clipboard.")

    def save_blueprint(self) -> None:
        if not self.result: return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path: Path(path).write_text(self.result.blueprint_string + "\n", encoding="utf-8")

    def save_json(self) -> None:
        if not self.result: return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path: Path(path).write_text(json.dumps(self.result.blueprint, indent=2, ensure_ascii=False), encoding="utf-8")

    def save_blueprint_book(self) -> None:
        try:
            book, encoded = generate_blueprint_book(self._config())
        except Exception as error:
            messagebox.showerror(APP_NAME, f"Could not generate blueprint book:\n\n{error}", parent=self); return
        path = filedialog.asksaveasfilename(parent=self, title="Save variant blueprint book", defaultextension=".txt", filetypes=[("Factorio blueprint string", "*.txt")])
        if path:
            Path(path).write_text(encoded + "\n", encoding="utf-8")
            self.status_var.set(f"Saved blueprint book with {len(book['blueprint_book']['blueprints'])} variants.")

    def _schedule_preview(self) -> None:
        if self.preview_job:
            self.after_cancel(self.preview_job); self.preview_job = None
        self._draw_preview()
        if self.result and len(self.result.preview_frames) > 1:
            delay = max(40, int(self._config().seconds_per_step * 1000))
            self.preview_job = self.after(delay, self._advance_preview)

    def _advance_preview(self) -> None:
        if not self.result: return
        self.preview_index = (self.preview_index + 1) % len(self.result.preview_frames)
        self._draw_preview(); self.preview_job = self.after(max(40, int(self._config().seconds_per_step * 1000)), self._advance_preview)

    def _draw_preview(self) -> None:
        self.preview_canvas.delete("all")
        if not self.result: return
        frame = self.result.preview_frames[self.preview_index]
        width = max(1, self.preview_canvas.winfo_width()); height = max(1, int(self.preview_canvas["height"]))
        if isinstance(frame, str):
            self.preview_canvas.create_text(width / 2, height / 2, text=frame, fill="#ffd66b", font=("TkFixedFont", max(14, min(36, width // max(1, len(frame))))), anchor="center")
            return
        columns = len(frame); rows = len(frame[0]) if columns else 0
        if not columns or not rows: return
        cfg = self._config()
        ratio_x, ratio_y = cfg.pixel_width, cfg.pixel_height
        cell = min((width - 20) / max(1, columns * ratio_x), (height - 20) / max(1, rows * ratio_y))
        cw, ch = cell * ratio_x, cell * ratio_y
        ox = (width - columns * cw) / 2; oy = (height - rows * ch) / 2
        for x, column in enumerate(frame):
            for y, value in enumerate(column):
                x1, y1 = ox + x * cw, oy + y * ch
                self.preview_canvas.create_rectangle(x1 + 1, y1 + 1, x1 + cw - 1, y1 + ch - 1, fill="#ffd34d" if value else "#202327", outline="#383c42")


def run_self_test() -> int:
    result = generate(TickerConfig(message="TEST", mode="lamp-compact", display_width=16, display_height=9, pixel_width=2, pixel_height=1))
    if not result.blueprint_string.startswith("0") or not result.stats["entities"]:
        return 1
    static = generate(TickerConfig(message="HELLO\nWORLD", mode="lamp-static", animation="static", display_width=32, display_height=16))
    if len(static.preview_frames) != 1:
        return 1
    book, encoded = generate_blueprint_book(TickerConfig(message="TEST"))
    if not encoded.startswith("0") or len(book["blueprint_book"]["blueprints"]) < 2:
        return 1
    print("Blueprint Ticker Maker self-test passed.")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(run_self_test())
    BlueprintTickerApp().mainloop()
