from __future__ import annotations

import csv
import random
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

try:
    import serial  # type: ignore
except ImportError:
    serial = None


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
    pressure: float
    light_level: float
    water_level: float

    def to_csv_row(self) -> list[str]:
        return [
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{self.soil_moisture:.1f}",
            f"{self.temperature:.1f}",
            f"{self.air_humidity:.1f}",
            f"{self.pressure:.1f}",
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
    max_soil_moisture: float = 60.0
    min_light_level: float = 35.0
    max_light_level: float = 65.0


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
        self.pressure = 1008.0
        self.light_level = 50.0
        self.water_level = 80.0

    def read_plant_data(self) -> PlantData:
        self._update_soil_moisture()
        self._update_temperature()
        self._update_air_humidity()
        self._update_pressure()
        self._update_light_level()
        self._update_water_level()
        return PlantData(
            timestamp=datetime.now(),
            soil_moisture=self.soil_moisture,
            temperature=self.temperature,
            air_humidity=self.air_humidity,
            pressure=self.pressure,
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

    def _update_pressure(self) -> None:
        target = 1008.0 + (2.0 if self.system_status.led_on else 0.0)
        self.pressure += (target - self.pressure) * 0.18
        self.pressure += self._rand(-0.9, 0.9)
        self.pressure = self._clamp(self.pressure, 970.0, 1045.0)

    def _update_water_level(self) -> None:
        if not self.system_status.pump_on:
            self.water_level -= self._rand(0.0, 0.3)
        self.water_level = self._clamp(self.water_level, 0.0, 100.0)


class UartDeviceConnection(DeviceConnection):
    def __init__(self, port_name: str, baud_rate: int, system_status: SystemStatus) -> None:
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.system_status = system_status
        self.fallback = MockDeviceConnection(system_status)
        self.serial_port = None
        self.last_error = ""
        self.last_data: PlantData | None = None

        if serial is None:
            self.last_error = "Brak biblioteki pyserial. UART jest niedostepny."
            return

        try:
            self.serial_port = serial.Serial(port_name, baud_rate, timeout=2)
            self.send_time()
        except Exception as exc:
            self.last_error = f"Nie mozna otworzyc portu {port_name}: {exc}"
            self.serial_port = None

    def read_plant_data(self) -> PlantData:
        if not self.serial_port or not self.serial_port.is_open:
            if self.last_data is not None:
                return self.last_data
            self.last_data = self.fallback.read_plant_data()
            return self.last_data

        deadline = datetime.now().timestamp() + 2.2
        while datetime.now().timestamp() < deadline:
            try:
                raw = self.serial_port.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if self._handle_status_line(line):
                    continue
                data = self._parse_data_line(line)
                if data is None:
                    continue
                self.last_data = data
                return data
            except Exception as exc:
                self.last_error = f"Blad odczytu UART: {exc}"
                break

        if self.last_data is not None:
            return self.last_data
        self.last_data = self.fallback.read_plant_data()
        return self.last_data

    def get_source_name(self) -> str:
        return "UART" if self.serial_port and self.serial_port.is_open else "UART-OFFLINE"

    def send_command(self, command: str) -> bool:
        if not self.serial_port or not self.serial_port.is_open:
            self.last_error = "Port UART nie jest otwarty."
            return False

        try:
            self.serial_port.write(f"{command}\n".encode("utf-8"))
            self.serial_port.flush()
            response = self.serial_port.readline().decode("utf-8", errors="ignore").strip()
            if response:
                if response.startswith("ERROR:"):
                    self.last_error = self._translate_device_error(response)
                    return False
                if response.startswith("OK:"):
                    self.last_error = ""
                    return True
                self._handle_status_line(response)
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = f"Blad wysylania UART: {exc}"
            return False

    def send_time(self) -> None:
        now = datetime.now()
        self.send_command(now.strftime("SET_TIME:%Y-%m-%d %H:%M:%S"))

    def send_thresholds(self, soil_min: float, soil_max: float, light_min: float, light_max: float) -> bool:
        return self.send_command(f"SET_THRESHOLDS:{soil_min:.1f},{soil_max:.1f},{light_min:.1f},{light_max:.1f}")

    def set_auto_mode(self) -> bool:
        return self.send_command("AUTO")

    def set_manual_mode(self) -> bool:
        return self.send_command("MANUAL")

    def set_pump(self, enabled: bool) -> bool:
        return self.send_command("PUMP:ON" if enabled else "PUMP:OFF")

    def set_led(self, enabled: bool) -> bool:
        return self.send_command("LED:ON" if enabled else "LED:OFF")

    def consume_last_error(self) -> str:
        message = self.last_error
        self.last_error = ""
        return message

    def _handle_status_line(self, line: str) -> bool:
        if line == "Smart Plant System Ready":
            return True
        if line.startswith("OK:"):
            self.last_error = ""
            return True
        if line.startswith("ERROR:"):
            self.last_error = self._translate_device_error(line)
            return True
        return False

    def _parse_data_line(self, line: str) -> PlantData | None:
        parts = line.split(",")
        if len(parts) != 9:
            return None
        try:
            data = PlantData(
                timestamp=datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S"),
                soil_moisture=float(parts[1]),
                temperature=float(parts[2]),
                air_humidity=float(parts[3]),
                pressure=float(parts[4]),
                light_level=float(parts[5]),
                water_level=float(parts[6]),
            )
            self.system_status.pump_on = parts[7].strip().lower() == "true"
            self.system_status.led_on = parts[8].strip().lower() == "true"
            self.last_error = ""
            return data
        except ValueError:
            return None

    def _translate_device_error(self, response: str) -> str:
        if response == "ERROR:LOW_WATER":
            return "Arduino odrzucilo komende. Zbyt niski poziom wody."
        return response.replace("ERROR:", "Blad Arduino: ")


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
                        "pressure",
                        "lightLevel",
                        "waterLevel",
                        "pumpOn",
                        "ledOn",
                    ]
                )
        else:
            header = self.log_path.read_text(encoding="utf-8").splitlines()[0:1]
            if header and "pressure" not in header[0]:
                with self.log_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(
                        [
                            "timestamp",
                            "soilMoisture",
                            "temperature",
                            "airHumidity",
                            "pressure",
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
        self._pull_uart_error()
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
        if data.soil_moisture < self.threshold_config.min_soil_moisture and data.water_level > 5.0:
            self.system_status.pump_on = True
        elif data.soil_moisture >= self.threshold_config.max_soil_moisture:
            self.system_status.pump_on = False

        if data.light_level < self.threshold_config.min_light_level:
            self.system_status.led_on = True
        elif data.light_level >= self.threshold_config.max_light_level:
            self.system_status.led_on = False

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
        if isinstance(self.device_connection, UartDeviceConnection):
            if not self.device_connection.set_pump(enabled):
                self._pull_uart_error()
        if not enabled:
            self.last_error_message = ""

    def set_led_manual(self, enabled: bool) -> None:
        self.set_automatic_control_enabled(False)
        self.system_status.led_on = enabled
        if isinstance(self.device_connection, UartDeviceConnection):
            if not self.device_connection.set_led(enabled):
                self._pull_uart_error()

    def update_thresholds(
        self,
        min_soil_moisture: float,
        max_soil_moisture: float,
        min_light_level: float,
        max_light_level: float,
    ) -> None:
        self.threshold_config.min_soil_moisture = min_soil_moisture
        self.threshold_config.max_soil_moisture = max_soil_moisture
        self.threshold_config.min_light_level = min_light_level
        self.threshold_config.max_light_level = max_light_level
        if isinstance(self.device_connection, UartDeviceConnection):
            if not self.device_connection.send_thresholds(min_soil_moisture, max_soil_moisture, min_light_level, max_light_level):
                self._pull_uart_error()
        self.automatic_control_enabled = True
        if self.current_data:
            self._apply_automation(self.current_data)
            self._ensure_pump_safety(self.current_data)

    def switch_to_demo_mode(self) -> None:
        self.device_connection = MockDeviceConnection(self.system_status)
        self.active_connection_label = "Tryb demo"
        self.last_error_message = ""

    def connect_to_uart(self, port_name: str, baud_rate: int) -> None:
        connection = UartDeviceConnection(port_name, baud_rate, self.system_status)
        self.device_connection = connection
        self.active_connection_label = f"UART: {port_name} @ {baud_rate}"
        if connection.serial_port and connection.serial_port.is_open:
            self.last_error_message = ""
        else:
            self.last_error_message = connection.consume_last_error() or "Nie udalo sie nawiazac polaczenia UART."

    def set_automatic_control_enabled(self, enabled: bool) -> None:
        self.automatic_control_enabled = enabled
        if isinstance(self.device_connection, UartDeviceConnection):
            ok = self.device_connection.set_auto_mode() if enabled else self.device_connection.set_manual_mode()
            if not ok:
                self._pull_uart_error()
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

    def _pull_uart_error(self) -> None:
        if isinstance(self.device_connection, UartDeviceConnection):
            message = self.device_connection.consume_last_error()
            if message:
                self.last_error_message = message


class Card(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, subtitle: str = "") -> None:
        super().__init__(parent, style="Card.TFrame", padding=18)
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(header, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))


class MetricCard(Card):
    def __init__(self, parent: tk.Misc, icon: str, title: str, accent: str, scale_min: float = 0.0, scale_max: float = 100.0) -> None:
        super().__init__(parent, title)
        self.scale_min = scale_min
        self.scale_max = scale_max
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
        normalized = 100 * (value - self.scale_min) / max(1.0, self.scale_max - self.scale_min)
        self.bar["value"] = max(0, min(100, normalized))


class GaugeCard(Card):
    def __init__(self, parent: tk.Misc, icon: str, title: str, accent: str, unit: str, scale_min: float, scale_max: float) -> None:
        super().__init__(parent, title)
        self.accent = accent
        self.unit = unit
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.canvas = tk.Canvas(self, width=210, height=210, bg=PANEL, highlightthickness=0)
        self.canvas.pack(pady=(8, 6))
        self.status_label = ttk.Label(self, text="Brak danych", style="Muted.TLabel")
        self.status_label.pack(anchor="center")
        self.icon = icon
        self.value = 0.0
        self.canvas.bind("<Configure>", lambda _: self._draw())

    def update_gauge(self, value: float, description: str) -> None:
        self.value = value
        self.status_label.configure(text=description)
        self._draw()

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 210)
        height = max(canvas.winfo_height(), 210)
        cx = width / 2
        cy = height / 2
        radius = min(width, height) / 2 - 16
        normalized = max(0.0, min(1.0, (self.value - self.scale_min) / max(1.0, self.scale_max - self.scale_min)))
        start = 135
        extent = 270

        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline="#1f3956", width=16)
        canvas.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=start,
            extent=-extent * normalized,
            style="arc",
            outline=self.accent,
            width=16,
        )
        canvas.create_oval(cx - radius + 24, cy - radius + 24, cx + radius - 24, cy + radius - 24, fill=PANEL_ALT, outline="")
        canvas.create_text(cx, cy - 34, text=self.icon, fill=self.accent, font=("Segoe UI Emoji", 22))
        canvas.create_text(cx, cy + 4, text=f"{self.value:.1f}", fill=TEXT, font=("Segoe UI Semibold", 24))
        canvas.create_text(cx, cy + 30, text=self.unit, fill=MUTED, font=("Segoe UI", 10))
        canvas.create_text(cx - radius + 8, cy + radius - 8, text=f"{self.scale_min:.0f}", fill=MUTED, anchor="sw", font=("Segoe UI", 9))
        canvas.create_text(cx + radius - 8, cy + radius - 8, text=f"{self.scale_max:.0f}", fill=MUTED, anchor="se", font=("Segoe UI", 9))


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


class StateSwitch(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str, left_label: str, right_label: str, left_command, right_command) -> None:
        super().__init__(parent, style="Card.TFrame")
        ttk.Label(self, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x")
        self.left_button = tk.Button(row, text=left_label, relief="flat", command=left_command, font=("Segoe UI Semibold", 10), pady=10, bd=0)
        self.left_button.pack(side="left", expand=True, fill="x")
        self.right_button = tk.Button(row, text=right_label, relief="flat", command=right_command, font=("Segoe UI Semibold", 10), pady=10, bd=0)
        self.right_button.pack(side="left", expand=True, fill="x", padx=(10, 0))
        self.detail_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.detail_label.pack(anchor="w", pady=(8, 0))

    def update_switch(self, left_active: bool, active_text: str, inactive_text: str) -> None:
        self._paint(self.left_button, left_active, active_positive=True)
        self._paint(self.right_button, not left_active, active_positive=False)
        self.detail_label.configure(text=active_text if left_active else inactive_text)

    def _paint(self, button: tk.Button, active: bool, active_positive: bool) -> None:
        if active:
            bg = "#58d68d" if active_positive else "#ff6b6b"
            fg = "#062515" if active_positive else "#2a0910"
        else:
            bg = "#203a58"
            fg = TEXT
        button.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)


class ModeControlCard(Card):
    def __init__(self, parent: tk.Misc, app: "PlantApp") -> None:
        super().__init__(parent, "Tryb pracy i sterowanie", "Sterowanie widoczne stale, z kolorowym stanem")
        self.app = app
        self.mode_label = ttk.Label(self, text="AUTO", style="MetricValue.TLabel")
        self.mode_label.pack(anchor="w", pady=(8, 2))
        self.mode_detail = ttk.Label(self, text="Sterowanie automatyczne aktywne", style="Muted.TLabel")
        self.mode_detail.pack(anchor="w")

        self.mode_switch = StateSwitch(self, "Tryb pracy", "AUTO", "REKA", self.app.set_auto, self.app.set_manual)
        self.mode_switch.pack(fill="x", pady=(16, 0))
        self.pump_switch = StateSwitch(self, "Pompa", "ON", "OFF", lambda: self.app.toggle_pump(True), lambda: self.app.toggle_pump(False))
        self.pump_switch.pack(fill="x", pady=(16, 0))
        self.led_switch = StateSwitch(self, "LED Grow", "ON", "OFF", lambda: self.app.toggle_led(True), lambda: self.app.toggle_led(False))
        self.led_switch.pack(fill="x", pady=(16, 0))

    def update_mode(self, auto_mode: bool, pump_on: bool, led_on: bool) -> None:
        self.mode_label.configure(text="AUTO" if auto_mode else "REKA")
        self.mode_detail.configure(text="Sterowanie automatyczne aktywne" if auto_mode else "Sterowanie reczne aktywne")
        self.mode_switch.update_switch(auto_mode, "Tryb automatyczny wlaczony", "Tryb reczny wlaczony")
        self.pump_switch.update_switch(pump_on, "Pompa jest wlaczona", "Pompa jest wylaczona")
        self.led_switch.update_switch(led_on, "LED jest wlaczony", "LED jest wylaczony")


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
        self.geometry("1480x940")
        self.minsize(1260, 840)
        self.configure(bg=BG)

        self.port_var = tk.StringVar(value="COM3")
        self.baud_var = tk.StringVar(value="9600")
        self.mode_var = tk.StringVar(value="AUTO")
        self.soil_min_var = tk.StringVar(value=f"{self.service.threshold_config.min_soil_moisture:.1f}")
        self.soil_max_var = tk.StringVar(value=f"{self.service.threshold_config.max_soil_moisture:.1f}")
        self.light_min_var = tk.StringVar(value=f"{self.service.threshold_config.min_light_level:.1f}")
        self.light_max_var = tk.StringVar(value=f"{self.service.threshold_config.max_light_level:.1f}")
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
        shell = ttk.Frame(self, style="Header.TFrame")
        shell.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(shell, bg=BG_ALT, highlightthickness=0)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self.scroll_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)

        outer = ttk.Frame(self.scroll_canvas, style="Header.TFrame", padding=24)
        self.scroll_window = self.scroll_canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind("<Configure>", self._resize_scroll_frame)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
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
        for idx in range(6):
            metrics.columnconfigure(idx, weight=1)
        self.temp_gauge = GaugeCard(metrics, "🌡", "Temperatura BME", WARNING, "C", 0, 40)
        self.humidity_gauge = GaugeCard(metrics, "💨", "Wilgotnosc BME", "#5dade2", "%", 0, 100)
        self.pressure_gauge = GaugeCard(metrics, "🧭", "Cisnienie BME", "#f39c12", "hPa", 970, 1045)
        self.soil_card = MetricCard(metrics, "💧", "Wilgotnosc gleby", ACCENT)
        self.light_card = MetricCard(metrics, "☀", "Natezenie swiatla", ACCENT_2)
        self.water_card = MetricCard(metrics, "🚰", "Poziom wody", "#9b59b6")
        top_row = (self.temp_gauge, self.humidity_gauge, self.pressure_gauge)
        for idx, widget in enumerate(top_row):
            widget.grid(row=0, column=idx * 2, columnspan=2, sticky="nsew", padx=(0 if idx == 0 else 12, 0), pady=(0, 12))
        bottom_row = (self.soil_card, self.light_card, self.water_card)
        for idx, widget in enumerate(bottom_row):
            widget.grid(row=1, column=idx * 2, columnspan=2, sticky="nsew", padx=(0 if idx == 0 else 12, 0))

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
        self.mode_card.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=(0, 18))

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

        config = Card(parent, "Zakresy automatyki", "Podaj przedzial utrzymania dla gleby i swiatla")
        config.pack(fill="x", pady=(0, 18))
        ttk.Label(config, text="Wilgotnosc gleby MIN [%]", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Entry(config, textvariable=self.soil_min_var, style="Field.TEntry").pack(fill="x")
        ttk.Label(config, text="Wilgotnosc gleby MAX [%]", style="Section.TLabel").pack(anchor="w", pady=(12, 6))
        ttk.Entry(config, textvariable=self.soil_max_var, style="Field.TEntry").pack(fill="x")
        ttk.Label(config, text="Naswietlenie MIN [%]", style="Section.TLabel").pack(anchor="w", pady=(12, 6))
        ttk.Entry(config, textvariable=self.light_min_var, style="Field.TEntry").pack(fill="x")
        ttk.Label(config, text="Naswietlenie MAX [%]", style="Section.TLabel").pack(anchor="w", pady=(12, 6))
        ttk.Entry(config, textvariable=self.light_max_var, style="Field.TEntry").pack(fill="x")
        ttk.Button(config, text="Zapisz zakresy", style="Action.TButton", command=self.save_thresholds).pack(fill="x", pady=(16, 0))

        info = Card(parent, "Stan systemu", "Szybki podglad diagnostyczny")
        info.pack(fill="x")
        self.info_text = tk.Text(info, height=8, bg=PANEL_ALT, fg=TEXT, bd=0, highlightthickness=0, wrap="word", font=("Consolas", 10))
        self.info_text.pack(fill="both", expand=True)
        self.info_text.configure(state="disabled")

    def _resize_scroll_frame(self, event) -> None:
        self.scroll_canvas.itemconfigure(self.scroll_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if self.scroll_canvas.winfo_exists():
            self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

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
            soil_min = self._parse_percent(self.soil_min_var.get())
            soil_max = self._parse_percent(self.soil_max_var.get())
            light_min = self._parse_percent(self.light_min_var.get())
            light_max = self._parse_percent(self.light_max_var.get())
            self._validate_range("Wilgotnosc gleby", soil_min, soil_max)
            self._validate_range("Naswietlenie", light_min, light_max)
        except ValueError as exc:
            messagebox.showerror("Niepoprawne dane", str(exc))
            return
        self.service.update_thresholds(soil_min, soil_max, light_min, light_max)
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

    def _validate_range(self, label: str, min_value: float, max_value: float) -> None:
        if min_value >= max_value:
            raise ValueError(f"{label}: wartosc MIN musi byc mniejsza od MAX.")

    def refresh_view(self) -> None:
        data = self.service.current_data
        if data:
            self.soil_card.update_metric(data.soil_moisture, "%", self._soil_description(data.soil_moisture))
            self.light_card.update_metric(data.light_level, "%", self._light_description(data.light_level))
            self.water_card.update_metric(data.water_level, "%", self._water_description(data.water_level))
            self.temp_gauge.update_gauge(data.temperature, self._temp_description(data.temperature))
            self.humidity_gauge.update_gauge(data.air_humidity, self._air_humidity_description(data.air_humidity))
            self.pressure_gauge.update_gauge(data.pressure, self._pressure_description(data.pressure))
            self.last_update_var.set(f"Ostatni odczyt: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        self.connection_var.set(self.service.active_connection_label)
        self.mode_var.set("AUTO" if self.service.automatic_control_enabled else "REKA")
        self.mode_card.update_mode(
            self.service.automatic_control_enabled,
            self.service.system_status.pump_on,
            self.service.system_status.led_on,
        )
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
            f"Zakres gleby: {self.service.threshold_config.min_soil_moisture:.1f}% - {self.service.threshold_config.max_soil_moisture:.1f}%",
            f"Zakres swiatla: {self.service.threshold_config.min_light_level:.1f}% - {self.service.threshold_config.max_light_level:.1f}%",
        ]
        if data:
            lines.extend(
                [
                    f"Temperatura BME: {data.temperature:.1f} C",
                    f"Wilgotnosc powietrza BME: {data.air_humidity:.1f}%",
                    f"Cisnienie BME: {data.pressure:.1f} hPa",
                ]
            )
        if self.service.last_error_message:
            lines.append(f"Status: {self.service.last_error_message}")
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state="disabled")

    def _soil_description(self, value: float) -> str:
        if value < self.service.threshold_config.min_soil_moisture:
            return "Ponizej zakresu, wlaczy sie podlewanie"
        if value > self.service.threshold_config.max_soil_moisture:
            return "Powyzej zalecanego zakresu"
        return "Wilgotnosc w zadanym przedziale"

    def _temp_description(self, value: float) -> str:
        if value < 19:
            return "Temperatura niska"
        if value <= 26:
            return "Zakres stabilny"
        return "Temperatura podwyzszona"

    def _light_description(self, value: float) -> str:
        if value < self.service.threshold_config.min_light_level:
            return "Ponizej zakresu, LED moze sie wlaczyc"
        if value > self.service.threshold_config.max_light_level:
            return "Powyzej docelowego naswietlenia"
        return "Swiatlo w zadanym przedziale"

    def _water_description(self, value: float) -> str:
        if value < 15:
            return "Uzupelnij zbiornik"
        if value < 50:
            return "Rezerwa srednia"
        return "Zbiornik wypelniony"

    def _air_humidity_description(self, value: float) -> str:
        if value < 40:
            return "Powietrze suche"
        if value <= 70:
            return "Wilgotnosc powietrza stabilna"
        return "Powietrze bardzo wilgotne"

    def _pressure_description(self, value: float) -> str:
        if value < 995:
            return "Niskie cisnienie"
        if value <= 1018:
            return "Cisnienie stabilne"
        return "Podwyzszone cisnienie"


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    system_status = SystemStatus()
    service = PlantControllerService(MockDeviceConnection(system_status), system_status, repo_root / "logs" / "plant-log.csv")
    app = PlantApp(service)
    app.mainloop()


if __name__ == "__main__":
    main()
