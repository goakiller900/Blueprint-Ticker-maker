"""Blueprint Ticker Maker desktop application.

A small, offline Tkinter GUI. No telemetry, no network access, and no automatic
file writes. Blueprint generation is performed by blueprint_core.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from .blueprint_core import (
        LAMP_COLORS,
        MODE_LABELS,
        TickerConfig,
        generate,
    )
except ImportError:
    from blueprint_core import (
        LAMP_COLORS,
        MODE_LABELS,
        TickerConfig,
        generate,
    )


APP_NAME = "Blueprint Ticker Maker"
APP_VERSION = "0.1.0"


class BlueprintTickerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.minsize(900, 700)
        self.geometry("1080x820")

        self.result = None
        self.preview_index = 0
        self.preview_job: str | None = None

        self.mode_var = tk.StringVar(value=MODE_LABELS["lamp-compact"])
        self.message_var = tk.StringVar(value="THE FACTORY GROWS!!")
        self.seconds_var = tk.StringVar(value="0.20")
        self.direction_var = tk.StringVar(value="left")
        self.width_var = tk.StringVar(value="24")
        self.spacing_var = tk.StringVar(value="1")
        self.gap_var = tk.StringVar(value="6")
        self.scale_var = tk.StringVar(value="1")
        self.color_var = tk.StringVar(value="yellow")
        self.rom_columns_var = tk.StringVar(value="0")
        self.edge_spaces_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(
            value="Offline application — no telemetry and no network access."
        )
        self.stats_var = tk.StringVar(value="No blueprint generated yet.")

        self._build_ui()
        self._update_mode_state()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        heading = ttk.Frame(outer)
        heading.pack(fill="x")
        ttk.Label(
            heading,
            text=APP_NAME,
            font=("TkDefaultFont", 18, "bold"),
        ).pack(side="left")
        ttk.Label(
            heading,
            text="Factorio 2.1 blueprint generator",
        ).pack(side="left", padx=(14, 0), pady=(7, 0))
        ttk.Label(
            heading,
            text="OFFLINE",
            foreground="#138a36",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="right")

        ttk.Separator(outer).pack(fill="x", pady=10)

        content = ttk.Panedwindow(outer, orient="horizontal")
        content.pack(fill="both", expand=True)

        controls = ttk.Frame(content, padding=(0, 0, 12, 0))
        output = ttk.Frame(content)
        content.add(controls, weight=1)
        content.add(output, weight=2)

        self._build_controls(controls)
        self._build_output(output)

        status = ttk.Label(
            outer,
            textvariable=self.status_var,
            anchor="w",
            relief="sunken",
            padding=(7, 4),
        )
        status.pack(fill="x", pady=(10, 0))

    def _build_controls(self, parent: ttk.Frame) -> None:
        general = ttk.LabelFrame(parent, text="Generator", padding=10)
        general.pack(fill="x")

        ttk.Label(general, text="Mode").grid(row=0, column=0, sticky="w")
        self.mode_combo = ttk.Combobox(
            general,
            textvariable=self.mode_var,
            state="readonly",
            values=tuple(MODE_LABELS.values()),
            width=24,
        )
        self.mode_combo.grid(row=0, column=1, sticky="ew", pady=3)
        self.mode_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._update_mode_state(),
        )

        ttk.Label(general, text="Message").grid(row=1, column=0, sticky="w")
        ttk.Entry(general, textvariable=self.message_var).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(general, text="Seconds per step").grid(
            row=2,
            column=0,
            sticky="w",
        )
        ttk.Entry(general, textvariable=self.seconds_var, width=10).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=3,
        )

        ttk.Label(general, text="Direction").grid(row=3, column=0, sticky="w")
        ttk.Combobox(
            general,
            textvariable=self.direction_var,
            values=("left", "right"),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=3)

        ttk.Label(general, text="Display width").grid(
            row=4,
            column=0,
            sticky="w",
        )
        ttk.Entry(general, textvariable=self.width_var).grid(
            row=4,
            column=1,
            sticky="ew",
            pady=3,
        )
        general.columnconfigure(1, weight=1)

        self.lamp_options = ttk.LabelFrame(parent, text="Lamp options", padding=10)
        self.lamp_options.pack(fill="x", pady=(10, 0))

        labels = (
            ("Character spacing", self.spacing_var),
            ("Repeat gap", self.gap_var),
            ("Pixel scale", self.scale_var),
            ("ROM columns (0 = auto)", self.rom_columns_var),
        )
        for row, (label, variable) in enumerate(labels):
            ttk.Label(self.lamp_options, text=label).grid(
                row=row,
                column=0,
                sticky="w",
            )
            ttk.Entry(self.lamp_options, textvariable=variable).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=3,
            )

        ttk.Label(self.lamp_options, text="Lamp colour").grid(
            row=4,
            column=0,
            sticky="w",
        )
        ttk.Combobox(
            self.lamp_options,
            textvariable=self.color_var,
            values=tuple(LAMP_COLORS),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", pady=3)
        self.lamp_options.columnconfigure(1, weight=1)

        self.nixie_options = ttk.LabelFrame(parent, text="Nixie options", padding=10)
        self.nixie_options.pack(fill="x", pady=(10, 0))
        ttk.Label(self.nixie_options, text="Blank edge characters").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Entry(self.nixie_options, textvariable=self.edge_spaces_var).grid(
            row=0,
            column=1,
            sticky="ew",
        )
        self.nixie_options.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(parent, text="Actions", padding=10)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="Generate blueprint",
            command=self.generate_blueprint,
        ).pack(fill="x", pady=2)
        self.copy_button = ttk.Button(
            actions,
            text="Copy blueprint string",
            command=self.copy_blueprint,
            state="disabled",
        )
        self.copy_button.pack(fill="x", pady=2)
        self.save_button = ttk.Button(
            actions,
            text="Save blueprint .txt",
            command=self.save_blueprint,
            state="disabled",
        )
        self.save_button.pack(fill="x", pady=2)
        self.json_button = ttk.Button(
            actions,
            text="Save decoded JSON",
            command=self.save_json,
            state="disabled",
        )
        self.json_button.pack(fill="x", pady=2)

        safety = ttk.LabelFrame(parent, text="Safety", padding=10)
        safety.pack(fill="x", pady=(10, 0))
        ttk.Label(
            safety,
            justify="left",
            wraplength=310,
            text=(
                "This program does not use the internet, collect telemetry, "
                "read Factorio saves, modify the game, or write files without "
                "an explicit Save action."
            ),
        ).pack(anchor="w")
        ttk.Button(
            safety,
            text="About and licences",
            command=self.show_about,
        ).pack(anchor="w", pady=(8, 0))

    def _build_output(self, parent: ttk.Frame) -> None:
        preview_box = ttk.LabelFrame(parent, text="Animated preview", padding=8)
        preview_box.pack(fill="x")

        self.preview_canvas = tk.Canvas(
            preview_box,
            height=230,
            background="#0c0d0f",
            highlightthickness=0,
        )
        self.preview_canvas.pack(fill="x")

        ttk.Label(
            preview_box,
            textvariable=self.stats_var,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(7, 0))

        string_box = ttk.LabelFrame(
            parent,
            text="Factorio blueprint string",
            padding=8,
        )
        string_box.pack(fill="both", expand=True, pady=(10, 0))

        self.output_text = tk.Text(
            string_box,
            wrap="char",
            height=18,
            font=("TkFixedFont", 9),
            undo=False,
        )
        scroll = ttk.Scrollbar(
            string_box,
            orient="vertical",
            command=self.output_text.yview,
        )
        self.output_text.configure(yscrollcommand=scroll.set)
        self.output_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _mode_key(self) -> str:
        selected = self.mode_var.get()
        for key, label in MODE_LABELS.items():
            if selected == label:
                return key
        return "lamp-compact"

    def _update_mode_state(self) -> None:
        mode = self._mode_key()
        lamp_mode = mode.startswith("lamp-")
        state = "normal" if lamp_mode else "disabled"
        for child in self.lamp_options.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

        nixie_state = "normal" if mode == "nixie" else "disabled"
        for child in self.nixie_options.winfo_children():
            try:
                child.configure(state=nixie_state)
            except tk.TclError:
                pass

        if mode == "lamp-compatible":
            try:
                if int(self.width_var.get()) > 36:
                    self.width_var.set("24")
            except ValueError:
                pass

    def _config(self) -> TickerConfig:
        return TickerConfig(
            message=self.message_var.get(),
            mode=self._mode_key(),
            seconds_per_step=float(self.seconds_var.get()),
            direction=self.direction_var.get(),
            display_width=int(self.width_var.get()),
            character_spacing=int(self.spacing_var.get()),
            repeat_gap=int(self.gap_var.get()),
            pixel_scale=int(self.scale_var.get()),
            lamp_color=self.color_var.get(),
            rom_columns=int(self.rom_columns_var.get()),
            nixie_edge_spaces=int(self.edge_spaces_var.get()),
        )

    def generate_blueprint(self) -> None:
        self.status_var.set("Generating blueprint…")
        self.update_idletasks()
        try:
            self.result = generate(self._config())
        except (ValueError, RuntimeError) as error:
            self.result = None
            self._set_output("")
            self._set_action_state(False)
            self.status_var.set(f"Generation failed: {error}")
            messagebox.showerror(APP_NAME, str(error), parent=self)
            return
        except Exception as error:
            self.result = None
            self._set_action_state(False)
            self.status_var.set("Unexpected generation error.")
            messagebox.showerror(
                APP_NAME,
                f"Unexpected error:\n\n{type(error).__name__}: {error}",
                parent=self,
            )
            return

        self._set_output(self.result.blueprint_string)
        self._set_action_state(True)
        stats = self.result.stats
        self.stats_var.set(
            f"{stats['mode']}  |  {stats['entities']} entities  |  "
            f"{stats['wires']} wires  |  {stats['frames']} frames  |  "
            f"max wire {stats['max_wire_distance']} tiles"
        )
        self.status_var.set(
            f"Blueprint ready: {stats['blueprint_characters']} characters."
        )
        self.preview_index = 0
        self._schedule_preview()

    def _set_output(self, value: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", value)
        self.output_text.configure(state="disabled")

    def _set_action_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)
        self.json_button.configure(state=state)

    def copy_blueprint(self) -> None:
        if not self.result:
            return
        self.clipboard_clear()
        self.clipboard_append(self.result.blueprint_string)
        self.update()
        self.status_var.set("Blueprint string copied to the clipboard.")

    def save_blueprint(self) -> None:
        if not self.result:
            return
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Save Factorio blueprint string",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialfile="factorio-ticker-blueprint.txt",
        )
        if not filename:
            return
        Path(filename).write_text(
            self.result.blueprint_string + "\n",
            encoding="utf-8",
        )
        self.status_var.set(f"Saved blueprint to {filename}")

    def save_json(self) -> None:
        if not self.result:
            return
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Save decoded blueprint JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            initialfile="factorio-ticker-blueprint.json",
        )
        if not filename:
            return
        Path(filename).write_text(
            json.dumps(
                self.result.blueprint,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        self.status_var.set(f"Saved decoded JSON to {filename}")

    def _schedule_preview(self) -> None:
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
            self.preview_job = None
        if not self.result or not self.result.preview_frames:
            self.preview_canvas.delete("all")
            return

        self._draw_preview()
        delay = max(16, int(self._config().seconds_per_step * 1000))
        self.preview_job = self.after(delay, self._advance_preview)

    def _advance_preview(self) -> None:
        if not self.result:
            return
        self.preview_index = (
            self.preview_index + 1
        ) % len(self.result.preview_frames)
        self._schedule_preview()

    def _draw_preview(self) -> None:
        self.preview_canvas.delete("all")
        frame = self.result.preview_frames[self.preview_index]
        width = max(1, self.preview_canvas.winfo_width())
        height = max(1, self.preview_canvas.winfo_height())

        if isinstance(frame, str):
            self.preview_canvas.create_text(
                width / 2,
                height / 2,
                text=frame.replace(" ", "·"),
                fill="#ffad4a",
                font=(
                    "TkFixedFont",
                    min(30, max(12, width // max(1, len(frame)))),
                ),
                anchor="center",
            )
            return

        logical_width = len(frame)
        if logical_width == 0:
            return
        pixel = min(
            (width - 20) / logical_width,
            (height - 20) / 7,
        )
        pixel = max(2, pixel)
        offset_x = (width - pixel * logical_width) / 2
        offset_y = (height - pixel * 7) / 2
        selected = LAMP_COLORS.get(
            self.color_var.get(),
            LAMP_COLORS["yellow"],
        )
        on_colour = "#{:02x}{:02x}{:02x}".format(
            int(selected["r"] * 255),
            int(selected["g"] * 255),
            int(selected["b"] * 255),
        )

        for column, bits in enumerate(frame):
            for row, value in enumerate(bits):
                x1 = offset_x + column * pixel + 1
                y1 = offset_y + row * pixel + 1
                x2 = x1 + pixel - 2
                y2 = y1 + pixel - 2
                self.preview_canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=(
                        on_colour
                        if value
                        else "#24272c"
                    ),
                    outline="",
                )

    def show_about(self) -> None:
        messagebox.showinfo(
            f"About {APP_NAME}",
            (
                f"{APP_NAME} {APP_VERSION}\n\n"
                "Open-source, offline Factorio blueprint generator.\n"
                "No telemetry, advertisements, update checker, or network code.\n\n"
                "The application source is licensed under the MIT License.\n"
                "Generated blueprints remain yours."
            ),
            parent=self,
        )


def run_self_test() -> int:
    """Exercise the bundled generator without opening a GUI."""
    result = generate(TickerConfig())
    if result.stats["entities"] != 314:
        raise RuntimeError("Unexpected compact blueprint structure.")
    if not result.blueprint_string.startswith("0"):
        raise RuntimeError("Blueprint encoding failed.")
    print(
        f"{APP_NAME} {APP_VERSION} self-test passed: "
        f"{result.stats['entities']} entities"
    )
    return 0


def main() -> None:
    app = BlueprintTickerApp()
    app.mainloop()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(run_self_test())
    main()
