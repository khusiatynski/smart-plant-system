from __future__ import annotations

import csv
import random
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk


BG = "#08111f"
BG_ALT = "#0d1a2b"
PANEL = "#12243b"
PANEL_ALT = "#162c47"
TEXT = "#e6f0ff"
MUTED = "#8ea7c3"
ACCENT = "#58d68d"
ACCENT_2 = "#43c6db"
WARNING = "#f5b041"
BORDER = "#21405f"


@dataclass
class PlantData:
    timestamp: datetime
    soil_moisture: float
    temperature: float
    air_humidity: float
    light_level: float
    water_level: float

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{self.soil_moisture:.1f}",
            f"{self.temperature:.1f}",
            f"{self.air_humidity:.1f}",
            f"{self.light_level:.1f}",
            f"{self.water_level:.1f}",
        ]


@dataclass
class SystemStatus:
    pump_on: bool = False
    led_on: bool = False


@dataclass
class ThresholdConfig:
    min_soil_moisture: float = 40.0
    min_light_level: float = 35.0


class DeviceConnection:
    def read_plant_data(self) -> PlantData:
        raise NotImplementedError

    def get_source_name(self) -> str:
        raise NotImplementedError


class MockDeviceConnection(DeviceConnection):
    def __init__(self, system_status: SystemStatus) -> None:
        self.random = random.Random()
        self.system_status = system_status
        self.soil_moisture = 55.0
        self.temperature = 22.0
        self.air_humidity = 58.0
        self.light_level = 50.0
        self.water_level = 80.0

    def read_plant_data(self) -> PlantData:
        self._update_soil_moisture()
        self._update_temperature()
        self._update_air_humidity()
        self._update_light_level()
        self._update_water_level()
        return PlantData(
            timestamp=datetime.now(),
            soil_moisture=self.soil_moisture,
            temperature=self.temperature,
            air_humidity=self.air_humidity,
            light_level=self.light_level,
            water_level=self.water_level,
        )

    def get_source_name(self) -> str:
        return "DEMO"

    def refill_water_tank(self) -> None:
        self.water_level = 100.0

    def _rand(self, min_value: float, max_value: float) -> float:
        return min_value + (max_value - min_value) * self.random.random()

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _update_soil_moisture(self) -> None:
        self.soil_moisture -= self._rand(0.4, 1.2)
        if self.system_status.pump_on and self.water_level > 2.0:
            self.soil_moisture += self._rand(4.0, 7.0)
            self.water_level -= self._rand(1.5, 3.5)
        self.soil_moisture = self._clamp(self.soil_moisture, 5.0, 100.0)

    def _update_temperature(self) -> None:
        self.temperature += self._rand(-0.5, 0.5)
        if self.system_status.led_on:
            self.temperature += 0.2
        self.temperature = self._clamp(self.temperature, 16.0, 32.0)

    def _update_air_humidity(self) -> None:
        self.air_humidity += self._rand(-1.5, 1.5)
        if self.system_status.pump_on:
            self.air_humidity += 0.6
        self.air_humidity = self._clamp(self.air_humidity, 30.0, 90.0)

    def _update_light_level(self) -> None:
        self.light_level += (50.0 - self.light_level) * 0.25
        self.light_level += self._rand(-5.0, 5.0)
        if self.system_status.led_on:
            self.light_level += self._rand(10.0, 18.0)
        self.light_level = self._clamp(self.light_level, 5.0, 100.0)

    def _update_water_level(self) -> None:
        if not self.system_status.pump_on:
            self.water_level -= self._rand(0.0, 0.3)
        self.water_level = self._clamp(self.water_level, 0.0, 100.0)


class UartDeviceConnection(DeviceConnection):
    def __init__(self, port_name: str, baud_rate: int, system_status: SystemStatus) -> None:
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.fallback = MockDeviceConnection(system_status)

    def read_plant_data(self) -> PlantData:
        return self.fallback.read_plant_data()

    def get_source_name(self) -> str:
        return "UART"


class DataLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    def initialize(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with self.log_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "timestamp",
                        "soilMoisture",
                        "temperature",
                        "airHumidity",
                        "lightLevel",
                        "waterLevel",
                        "pumpOn",
                        "ledOn",
                    ]
                )

    def log(self, data: PlantData, status: SystemStatus) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([*data.to_csv_row(), str(status.pump_on).lower(), str(status.led_on).lower()])


class PlantControllerService:
    MAX_HISTORY_SIZE = 40

    def __init__(self, device_connection: DeviceConnection, system_status: SystemStatus, log_path: Path) -> None:
        self.device_connection = device_connection
        self.system_status = system_status
        self.threshold_config = ThresholdConfig()
        self.data_logger = DataLogger(log_path)
        self.history: list[PlantData] = []
        self.current_data: PlantData | None = None
        self.last_error_message = ""
        self.automatic_control_enabled = True
        self.active_connection_label = "Tryb demo"
        try:
            self.data_logger.initialize()
        except OSError as exc:
            self.last_error_message = f"Nie udalo sie przygotowac pliku logu: {exc}"

    def refresh_data(self) -> PlantData:
        self.current_data = self.device_connection.read_plant_data()
        self._ensure_pump_safety(self.current_data)
        if self.automatic_control_enabled:
            self._apply_automation(self.current_data)
        self._ensure_pump_safety(self.current_data)
        self.history.append(self.current_data)
        if len(self.history) > self.MAX_HISTORY_SIZE:
            self.history.pop(0)
        try:
            self.data_logger.log(self.current_data, self.system_status)
            if not self.last_error_message.startswith("Pompa"):
                self.last_error_message = ""
        except OSError as exc:
            self.last_error_message = f"Blad zapisu logu: {exc}"
        return self.current_data

    def _apply_automation(self, data: PlantData) -> None:
        self.system_status.pump_on = data.soil_moisture < self.threshold_config.min_soil_moisture and data.water_level > 5.0
        self.system_status.led_on = data.light_level < self.threshold_config.min_light_level

    def _ensure_pump_safety(self, data: PlantData) -> None:
        if data.water_level <= 2.0:
            self.system_status.pump_on = False
            self.last_error_message = "Pompa zostala zablokowana. Brak wody w zbiorniku."

    def set_pump_manual(self, enabled: bool) -> None:
        self.set_automatic_control_enabled(False)
        if enabled and not self.can_start_pump():
            self.system_status.pump_on = False
            self.last_error_message = "Pompa nie moze zostac wlaczona. Zbiornik wody jest pusty."
            return
        self.system_status.pump_on = enabled
        if not enabled:
            self.last_error_message = ""

    def set_led_manual(self, enabled: bool) -> None:
        self.set_automatic_control_enabled(False)
        self.system_status.led_on = enabled

    def update_thresholds(self, min_soil_moisture: float, min_light_level: float) -> None:
        self.threshold_config.min_soil_moisture = min_soil_moisture
        self.threshold_config.min_light_level = min_light_level
        self.automatic_control_enabled = True
        if self.current_data:
            self._apply_automation(self.current_data)
            self._ensure_pump_safety(self.current_data)

    def switch_to_demo_mode(self) -> None:
        self.device_connection = MockDeviceConnection(self.system_status)
        self.active_connection_label = "Tryb demo"
        self.last_error_message = ""

    def connect_to_uart(self, port_name: str, baud_rate: int) -> None:
        self.device_connection = UartDeviceConnection(port_name, baud_rate, self.system_status)
        self.active_connection_label = f"UART: {port_name} @ {baud_rate}"
        self.last_error_message = "Warstwa UART jest przygotowana, odczyt danych pozostaje symulowany."

    def set_automatic_control_enabled(self, enabled: bool) -> None:
        self.automatic_control_enabled = enabled
        if enabled and self.current_data:
            self._apply_automation(self.current_data)
            self._ensure_pump_safety(self.current_data)

    def refill_water_tank(self) -> None:
        if isinstance(self.device_connection, MockDeviceConnection):
            self.device_connection.refill_water_tank()
            self.current_data = self.device_connection.read_plant_data()
            self.history.append(self.current_data)
            if len(self.history) > self.MAX_HISTORY_SIZE:
                self.history.pop(0)
            self.last_error_message = ""

    def can_start_pump(self) -> bool:
        return self.current_data is None or self.current_data.water_level > 2.0

    def is_demo_mode(self) -> bool:
        return self.device_connection.get_source_name() == "DEMO"

    @property
    def log_path(self) -> Path:
        return self.data_logger.log_path

    @property
    def active_source_name(self) -> str:
        return self.device_connection.get_source_name()


class Card(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, subtitle: str = "") -> None:
        super().__init__(parent, style="Card.TFrame", padding=18)
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(header, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))


class MetricCard(Card):
    def __init__(self, parent: tk.Misc, icon: str, title: str, accent: str) -> None:
        super().__init__(parent, title)
        top = ttk.Frame(self, style="Card.TFrame")
        top.pack(fill="x")
        tk.Label(top, text=icon, bg=PANEL_ALT, fg=accent, font=("Segoe UI Emoji", 20), width=2, pady=4).pack(side="left")
        self.value_label = ttk.Label(top, text="--", style="MetricValue.TLabel")
        self.value_label.pack(side="left", padx=(12, 0))
        self.status_label = ttk.Label(self, text="Brak danych", style="Muted.TLabel")
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.bar = ttk.Progressbar(self, maximum=100, mode="determinate", style="Plant.Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=(14, 0))

    def update_metric(self, value: float, suffix: str, description: str) -> None:
        self.value_label.configure(text=f"{value:.1f}{suffix}")
        self.status_label.configure(text=description)
        self.bar["value"] = max(0, min(100, value))


class ToggleCard(Card):
    def __init__(self, parent: tk.Misc, icon: str, title: str, accent: str) -> None:
        super().__init__(parent, title)
        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x")
        tk.Label(row, text=icon, bg=PANEL_ALT, fg=accent, font=("Segoe UI Emoji", 20), width=2, pady=4).pack(side="left")
        self.state_label = ttk.Label(row, text="--", style="MetricValue.TLabel")
        self.state_label.pack(side="left", padx=(12, 0))
        self.detail_label = ttk.Label(self, text="Oczekiwanie na pierwszy odczyt", style="Muted.TLabel")
        self.detail_label.pack(anchor="w", pady=(12, 0))

    def update_state(self, enabled: bool, auto_mode: bool, detail: str) -> None:
        self.state_label.configure(text="AKTYWNA" if enabled else "WYLOCZONA")
        self.detail_label.configure(text=f"{detail} | {'AUTO' if auto_mode else 'REKA'}")


class ModeControlCard(Card):
    def __init__(self, parent: tk.Misc, app: "PlantApp") -> None:
        super().__init__(parent, "Tryb pracy i sterowanie", "Najwazniejsze akcje sa stale widoczne")
        self.app = app
        self.mode_label = ttk.Label(self, text="AUTO", style="MetricValue.TLabel")
        self.mode_label.pack(anchor="w", pady=(8, 2))
        self.mode_detail = ttk.Label(self, text="Sterowanie automatyczne aktywne", style="Muted.TLabel")
        self.mode_detail.pack(anchor="w")

        mode_row = ttk.Frame(self, style="Card.TFrame")
        mode_row.pack(fill="x", pady=(14, 0))
        ttk.Button(mode_row, text="AUTO", style="Action.TButton", command=self.app.set_auto).pack(side="left", expand=True, fill="x")
        ttk.Button(mode_row, text="REKA", style="Ghost.TButton", command=self.app.set_manual).pack(side="left", expand=True, fill="x", padx=(10, 0))

        grid = ttk.Frame(self, style="Card.TFrame")
        grid.pack(fill="x", pady=(14, 0))
        for idx in range(2):
            grid.columnconfigure(idx, weight=1)
        ttk.Button(grid, text="Pompa ON", style="Action.TButton", command=lambda: self.app.toggle_pump(True)).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(grid, text="Pompa OFF", style="Ghost.TButton", command=lambda: self.app.toggle_pump(False)).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(grid, text="LED ON", style="Action.TButton", command=lambda: self.app.toggle_led(True)).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(10, 0))
        ttk.Button(grid, text="LED OFF", style="Ghost.TButton", command=lambda: self.app.toggle_led(False)).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(10, 0))

    def update_mode(self, auto_mode: bool) -> None:
        self.mode_label.configure(text="AUTO" if auto_mode else "REKA")
        self.mode_detail.configure(text="Sterowanie automatyczne aktywne" if auto_mode else "Sterowanie reczne aktywne")


class TrendChart(Card):
    def __init__(self, parent: tk.Misc, title: str, line_color: str, value_getter) -> None:
        super().__init__(parent, title, "Ostatnie 40 probek")
        self.line_color = line_color
        self.value_getter = value_getter
        self.history: list[PlantData] = []
        self.canvas = tk.Canvas(self, height=250, bg=PANEL_ALT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(14, 0))
        self.canvas.bind("<Configure>", lambda _: self.redraw(self.history))

    def redraw(self, history: list[PlantData]) -> None:
        self.history = history
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 220)
        left, top, right, bottom = 46, 20, width - 20, height - 34
        canvas.create_rectangle(0, 0, width, height, fill=PANEL_ALT, outline=PANEL_ALT)
        for idx in range(5):
            y = top + (bottom - top) * idx / 4
            canvas.create_line(left, y, right, y, fill="#284763", dash=(2, 4))
            canvas.create_text(14, y, text=f"{100 - idx * 25}%", fill=MUTED, anchor="w", font=("Segoe UI", 9))
        canvas.create_line(left, top, left, bottom, fill=BORDER, width=2)
        canvas.create_line(left, bottom, right, bottom, fill=BORDER, width=2)
        if len(history) < 2:
            canvas.create_text(width / 2, height / 2, text="Za malo danych do wykresu", fill=MUTED, font=("Segoe UI", 13))
            return
        points: list[tuple[float, float]] = []
        for idx, item in enumerate(history):
            x = left + (right - left) * idx / (len(history) - 1)
            y = bottom - (bottom - top) * self.value_getter(item) / 100
            points.append((x, y))
        for idx in range(1, len(points)):
            canvas.create_line(*points[idx - 1], *points[idx], fill=self.line_color, width=3, smooth=True)
        for x, y in points[-6:]:
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=self.line_color, outline="")


class PlantApp(tk.Tk):
    def __init__(self, service: PlantControllerService) -> None:
        super().__init__()
        self.service = service
        self.title("Smart Plant System")
        self.geometry("1380x860")
        self.minsize(1180, 760)
        self.configure(bg=BG)

        self.port_var = tk.StringVar(value="COM3")
        self.baud_var = tk.StringVar(value="9600")
        self.mode_var = tk.StringVar(value="AUTO")
        self.soil_threshold_var = tk.StringVar(value=f"{self.service.threshold_config.min_soil_moisture:.1f}")
        self.light_threshold_var = tk.StringVar(value=f"{self.service.threshold_config.min_light_level:.1f}")
        self.connection_var = tk.StringVar(value="Tryb demo")
        self.footer_var = tk.StringVar(value="")
        self.last_update_var = tk.StringVar(value="Brak danych")

        self._configure_styles()
        self._build_layout()
        self.refresh_view()
        self.after(200, self._tick)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL_ALT)
        style.configure("Card.TFrame", background=PANEL, borderwidth=0)
        style.configure("Header.TFrame", background=BG_ALT)
        style.configure("CardTitle.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 14))
        style.configure("HeroTitle.TLabel", background=BG_ALT, foreground=TEXT, font=("Segoe UI Semibold", 28))
        style.configure("HeroText.TLabel", background=BG_ALT, foreground=MUTED, font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("MetricValue.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 23))
        style.configure("Section.TLabel", background=BG, foreground=MUTED, font=("Segoe UI Semibold", 10))
        style.configure("Action.TButton", background=ACCENT, foreground="#062515", borderwidth=0, font=("Segoe UI Semibold", 10), padding=10)
        style.map("Action.TButton", background=[("active", "#73e1a2")])
        style.configure("Ghost.TButton", background=PANEL_ALT, foreground=TEXT, borderwidth=0, font=("Segoe UI Semibold", 10), padding=10)
        style.map("Ghost.TButton", background=[("active", "#1e3b5b")])
        style.configure("Plant.Horizontal.TProgressbar", troughcolor="#1a324f", background=ACCENT, bordercolor="#1a324f", lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("Field.TEntry", fieldbackground=PANEL_ALT, foreground=TEXT, bordercolor=BORDER, insertcolor=TEXT, padding=8)
        style.configure("Data.TCombobox", fieldbackground=PANEL_ALT, foreground=TEXT, background=PANEL_ALT, arrowcolor=TEXT)
        style.map("Data.TCombobox", fieldbackground=[("readonly", PANEL_ALT)])
        style.configure("Select.TRadiobutton", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 10))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self, style="Header.TFrame", padding=24)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        hero = ttk.Frame(outer, style="Header.TFrame", padding=24)
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=1)
        ttk.Label(hero, text="🌿 Smart Plant Control", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            hero,
            text="Nowy dashboard w Pythonie: ciemny interfejs, kolorowe statusy, wykresy na zywo i sterowanie podlewaniem z jednego okna.",
            style="HeroText.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        hero_side = ttk.Frame(hero, style="Header.TFrame")
        hero_side.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(hero_side, textvariable=self.connection_var, style="Section.TLabel").pack(anchor="e")
        ttk.Label(hero_side, textvariable=self.last_update_var, style="HeroText.TLabel").pack(anchor="e", pady=(6, 0))

        metrics = ttk.Frame(outer, style="Header.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(18, 18))
        for idx in range(4):
            metrics.columnconfigure(idx, weight=1)
        self.soil_card = MetricCard(metrics, "💧", "Wilgotnosc gleby", ACCENT)
        self.temp_card = MetricCard(metrics, "🌡", "Temperatura", WARNING)
        self.light_card = MetricCard(metrics, "☀", "Natezenie swiatla", ACCENT_2)
        self.water_card = MetricCard(metrics, "🚰", "Poziom wody", "#9b59b6")
        for idx, widget in enumerate((self.soil_card, self.temp_card, self.light_card, self.water_card)):
            widget.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 12, 0))

        content = ttk.Frame(outer, style="Header.TFrame")
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=0)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content, style="Header.TFrame")
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 18))
        right = ttk.Frame(content, style="Header.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.columnconfigure(1, weight=1)
        right.columnconfigure(2, weight=1)
        right.rowconfigure(1, weight=1)

        self._build_controls(left)

        self.mode_card = ModeControlCard(right, self)
        self.pump_state = ToggleCard(right, "🪴", "Pompa", ACCENT)
        self.led_state = ToggleCard(right, "💡", "LED Grow", WARNING)
        self.mode_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 18))
        self.pump_state.grid(row=0, column=1, sticky="ew", padx=6, pady=(0, 18))
        self.led_state.grid(row=0, column=2, sticky="ew", padx=(6, 0), pady=(0, 18))

        self.soil_chart = TrendChart(right, "Trend wilgotnosci gleby", ACCENT, lambda item: item.soil_moisture)
        self.light_chart = TrendChart(right, "Trend naswietlenia", ACCENT_2, lambda item: item.light_level)
        self.soil_chart.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        self.light_chart.grid(row=1, column=2, sticky="nsew", padx=(6, 0))

        footer = ttk.Frame(outer, style="Card.TFrame", padding=14)
        footer.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(footer, textvariable=self.footer_var, style="Muted.TLabel", wraplength=1280, justify="left").pack(anchor="w")

    def _build_controls(self, parent: ttk.Frame) -> None:
        connection = Card(parent, "Polaczenie i tryb", "Demo lub przygotowany UART")
        connection.pack(fill="x", pady=(0, 18))
        ttk.Label(connection, text="Port COM", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Combobox(connection, textvariable=self.port_var, values=[f"COM{i}" for i in range(1, 13)], style="Data.TCombobox").pack(fill="x")
        ttk.Label(connection, text="Baud rate", style="Section.TLabel").pack(anchor="w", pady=(14, 6))
        ttk.Combobox(connection, textvariable=self.baud_var, values=["9600", "19200", "38400", "57600", "115200"], style="Data.TCombobox", state="readonly").pack(fill="x")
        row = ttk.Frame(connection, style="Card.TFrame")
        row.pack(fill="x", pady=(16, 0))
        ttk.Button(row, text="Polacz UART", style="Action.TButton", command=self.connect_uart).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Tryb demo", style="Ghost.TButton", command=self.switch_demo).pack(side="left", expand=True, fill="x", padx=(10, 0))
        ttk.Button(connection, text="Dolej wode", style="Ghost.TButton", command=self.refill_water).pack(fill="x", pady=(10, 0))

        mode = Card(parent, "Sterowanie", "Wybierz sposob pracy systemu")
        mode.pack(fill="x", pady=(0, 18))
        ttk.Radiobutton(mode, text="AUTO", variable=self.mode_var, value="AUTO", style="Select.TRadiobutton", command=self.set_auto).pack(anchor="w")
        ttk.Radiobutton(mode, text="REKA", variable=self.mode_var, value="REKA", style="Select.TRadiobutton", command=self.set_manual).pack(anchor="w", pady=(6, 0))
        buttons = ttk.Frame(mode, style="Card.TFrame")
        buttons.pack(fill="x", pady=(16, 0))
        for index in range(2):
            buttons.columnconfigure(index, weight=1)
        ttk.Button(buttons, text="Pompa ON", style="Action.TButton", command=lambda: self.toggle_pump(True)).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(buttons, text="Pompa OFF", style="Ghost.TButton", command=lambda: self.toggle_pump(False)).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(buttons, text="LED ON", style="Action.TButton", command=lambda: self.toggle_led(True)).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(10, 0))
        ttk.Button(buttons, text="LED OFF", style="Ghost.TButton", command=lambda: self.toggle_led(False)).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(10, 0))

        config = Card(parent, "Progi automatyki", "Zmiana zapisuje i wlacza AUTO")
        config.pack(fill="x", pady=(0, 18))
        ttk.Label(config, text="Min. wilgotnosc gleby [%]", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Entry(config, textvariable=self.soil_threshold_var, style="Field.TEntry").pack(fill="x")
        ttk.Label(config, text="Min. natezenie swiatla [%]", style="Section.TLabel").pack(anchor="w", pady=(14, 6))
        ttk.Entry(config, textvariable=self.light_threshold_var, style="Field.TEntry").pack(fill="x")
        ttk.Button(config, text="Zapisz progi", style="Action.TButton", command=self.save_thresholds).pack(fill="x", pady=(16, 0))

        info = Card(parent, "Stan systemu", "Szybki podglad diagnostyczny")
        info.pack(fill="x")
        self.info_text = tk.Text(info, height=8, bg=PANEL_ALT, fg=TEXT, bd=0, highlightthickness=0, wrap="word", font=("Consolas", 10))
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def _tick(self) -> None:
        self.service.refresh_data()
        self.refresh_view()
        self.after(2000, self._tick)

    def connect_uart(self) -> None:
        port_name = self.port_var.get().strip().upper()
        if not port_name or not port_name.startswith("COM"):
            messagebox.showerror("Blad UART", "Nazwa portu powinna wygladac np. COM3.")
            return
        try:
            baud_rate = int(self.baud_var.get().strip())
        except ValueError:
            messagebox.showerror("Blad UART", "Baud rate musi byc liczba.")
            return
        self.service.connect_to_uart(port_name, baud_rate)
        self.refresh_view()

    def switch_demo(self) -> None:
        self.service.switch_to_demo_mode()
        self.refresh_view()

    def refill_water(self) -> None:
        self.service.refill_water_tank()
        self.refresh_view()

    def set_auto(self) -> None:
        self.service.set_automatic_control_enabled(True)
        self.mode_var.set("AUTO")
        self.refresh_view()

    def set_manual(self) -> None:
        self.service.set_automatic_control_enabled(False)
        self.mode_var.set("REKA")
        self.refresh_view()

    def toggle_pump(self, enabled: bool) -> None:
        self.service.set_pump_manual(enabled)
        if enabled and not self.service.can_start_pump():
            messagebox.showwarning("Brak wody", "Pompy nie mozna wlaczyc bez wody w zbiorniku.")
        self.mode_var.set("REKA")
        self.refresh_view()

    def toggle_led(self, enabled: bool) -> None:
        self.service.set_led_manual(enabled)
        self.mode_var.set("REKA")
        self.refresh_view()

    def save_thresholds(self) -> None:
        try:
            soil = self._parse_percent(self.soil_threshold_var.get())
            light = self._parse_percent(self.light_threshold_var.get())
        except ValueError as exc:
            messagebox.showerror("Niepoprawne dane", str(exc))
            return
        self.service.update_thresholds(soil, light)
        self.mode_var.set("AUTO")
        self.refresh_view()

    def _parse_percent(self, value: str) -> float:
        try:
            parsed = float(value.replace(",", "."))
        except ValueError as exc:
            raise ValueError("Wprowadz liczbe w polach progow.") from exc
        if not 0 <= parsed <= 100:
            raise ValueError("Wprowadz wartosc z zakresu 0-100.")
        return parsed

    def refresh_view(self) -> None:
        data = self.service.current_data
        if data:
            self.soil_card.update_metric(data.soil_moisture, "%", self._soil_description(data.soil_moisture))
            self.temp_card.update_metric(data.temperature, "C", self._temp_description(data.temperature))
            self.light_card.update_metric(data.light_level, "%", self._light_description(data.light_level))
            self.water_card.update_metric(data.water_level, "%", self._water_description(data.water_level))
            self.last_update_var.set(f"Ostatni odczyt: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self.connection_var.set(self.service.active_connection_label)
        self.mode_var.set("AUTO" if self.service.automatic_control_enabled else "REKA")
        self.mode_card.update_mode(self.service.automatic_control_enabled)
        self.pump_state.update_state(self.service.system_status.pump_on, self.service.automatic_control_enabled, "Nawadnianie aktywne" if self.service.system_status.pump_on else "Pompa oczekuje")
        self.led_state.update_state(self.service.system_status.led_on, self.service.automatic_control_enabled, "Doswietlanie aktywne" if self.service.system_status.led_on else "Swiatlo w stanie spoczynku")
        self.soil_chart.redraw(self.service.history)
        self.light_chart.redraw(self.service.history)
        self.footer_var.set(self._build_footer())
        self._update_info_panel(data)

    def _build_footer(self) -> str:
        mode = "Tryb automatyczny" if self.service.automatic_control_enabled else "Tryb reczny"
        base = f"Log: {self.service.log_path} | Zrodlo: {self.service.active_source_name} | {mode}"
        return f"{base} | {self.service.last_error_message}" if self.service.last_error_message else base

    def _update_info_panel(self, data: PlantData | None) -> None:
        lines = [
            f"Tryb: {'AUTO' if self.service.automatic_control_enabled else 'REKA'}",
            f"Polaczenie: {self.service.active_connection_label}",
            f"Zrodlo danych: {self.service.active_source_name}",
            f"Pompa: {'ON' if self.service.system_status.pump_on else 'OFF'}",
            f"LED: {'ON' if self.service.system_status.led_on else 'OFF'}",
            f"Prog gleby: {self.service.threshold_config.min_soil_moisture:.1f}%",
            f"Prog swiatla: {self.service.threshold_config.min_light_level:.1f}%",
        ]
        if data:
            lines.extend([f"Temperatura: {data.temperature:.1f} C", f"Wilgotnosc powietrza: {data.air_humidity:.1f}%"])
        if self.service.last_error_message:
            lines.append(f"Status: {self.service.last_error_message}")
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state="disabled")

    def _soil_description(self, value: float) -> str:
        if value < 30:
            return "Gleba wymaga podlewania"
        if value < 55:
            return "Poziom bezpieczny"
        return "Roslina ma komfortowa wilgoc"

    def _temp_description(self, value: float) -> str:
        if value < 19:
            return "Temperatura niska"
        if value <= 26:
            return "Zakres stabilny"
        return "Temperatura podwyzszona"

    def _light_description(self, value: float) -> str:
        if value < 30:
            return "Za ciemno dla wzrostu"
        if value < 60:
            return "Oswietlenie umiarkowane"
        return "Dobre naswietlenie"

    def _water_description(self, value: float) -> str:
        if value < 15:
            return "Uzupelnij zbiornik"
        if value < 50:
            return "Rezerwa srednia"
        return "Zbiornik wypelniony"


def main() -> None:
    system_status = SystemStatus()
    service = PlantControllerService(MockDeviceConnection(system_status), system_status, Path("logs") / "plant-log.csv")
    app = PlantApp(service)
    app.mainloop()


if __name__ == "__main__":
    main()
