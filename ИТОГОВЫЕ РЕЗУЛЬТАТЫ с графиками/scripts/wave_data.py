import math
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEIGHTS = [20, 40, 60, 80, 100]


def ask_height():
    height = int(input("Глубина по линейке (20, 40, 60, 80 или 100 мм): "))
    if height not in HEIGHTS:
        raise SystemExit("Для этого опыта выберите одну из пяти глубин.")
    return height


def record(adc, seconds, start):
    samples = []
    while time.perf_counter() - start < seconds:
        samples.append(adc.get_number())
    duration = time.perf_counter() - start
    return samples, duration


def show_frequency(samples, duration):
    frequency = len(samples) / duration
    print(f"{len(samples)} отсчётов за {duration:.3f} с. Частота {frequency:.1f} Гц.")
    if frequency <= 100:
        print("Для опыта требуется частота выше 100 Гц.")


def save_data(path, samples, duration):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        file.write("- Wave Lab\n")
        file.write(f"- Date: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        file.write(f"- Duration: {duration:.6f} s\n\n")
        for sample in samples:
            file.write(f"{sample}\n")
    temporary.replace(path)
    print(f"Запись сохранена: {path}")


def read_data(path):
    with path.open(encoding="utf-8-sig") as file:
        if file.readline().strip() != "- Wave Lab":
            raise ValueError(f"Неверный заголовок в {path.name}")
        line = file.readline().strip()
        expected = None
        if line.startswith("- Date:"):
            fields = file.readline().split()
            if len(fields) != 4 or fields[:2] != ["-", "Duration:"] or fields[3] != "s":
                raise ValueError(f"Проверьте строку длительности в {path.name}")
            duration = float(fields[2])
        else:
            fields = line.split()
            if len(fields) != 4 or fields[0] != "duration" or fields[2] != "count":
                raise ValueError(f"Неверный формат в {path.name}")
            duration = float(fields[1])
            expected = int(fields[3])
        samples = [float(line) for line in file if line.strip()]
    if not samples or not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"Проверьте длительность и данные в {path.name}")
    if expected is not None and expected != len(samples):
        raise ValueError(f"Неполная запись в {path.name}")
    if any(not 0 <= value <= 1023 for value in samples):
        raise ValueError(f"В {path.name} есть значения вне диапазона MCP3021 (0–1023)")
    return samples, duration
