"""
waveMeasure.py — скрипт измерений (Экспериментатор).

Режимы:
  calibrate <уровень_мм> <секунды>   — калибровка на стоявшей воде (20, 40, 60, 80, 100 мм)
  measure   <уровень_мм> [секунды=15] — ждать открытия дверцы, потом записать волну

Примеры:
    python waveMeasure.py calibrate 20 10
    python waveMeasure.py calibrate 100 10
    python waveMeasure.py measure 40 15

Формат файла: - Wave Lab / duration count / отсчёты (см. waveFunctions.save_data)
"""

import sys
import os
import time
import waveFunctions as b

DATA_DIR = "data"
CALIBRATION_DIR = os.path.join(DATA_DIR, "calibration")
HEIGHTS = [20, 40, 60, 80, 100]  # мм


def ensure_dirs():
    os.makedirs(CALIBRATION_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def record(adc, seconds, wait_door=False):
    """
    Собирать отсчёты АЦП в течение seconds.
    Если wait_door — сначала ждать открытия дверцы (moment t=0).
    Возвращает (samples, duration, t0_or_none).
    """
    if wait_door:
        GPIO = b.gpio_setup()
        t0 = b.wait_door_open(GPIO)
    else:
        GPIO = None
        t0 = None

    print(f"[record] Сбор {seconds} сек ... (без пауз, частота определяется АЦП)")
    samples, duration, freq = b.measure_frequency(adc, seconds)

    if GPIO is not None:
        b.gpio_cleanup(GPIO)

    return samples, duration, t0


def calibrate(level_mm, seconds):
    """Калибровка: вода стоит ровно на уровне level_mm, запись seconds."""
    b.adc_setup()  # проверка, что АЦП живой
    adc = b.adc_setup()
    ensure_dirs()
    print(f"[calibrate] Уровень воды {level_mm} мм, запись {seconds} сек ...")
    samples, duration, _ = record(adc, seconds, wait_door=False)
    fname = os.path.join(CALIBRATION_DIR, f"{level_mm} mm.txt")
    b.save_data(fname, samples, duration, len(samples))
    b.adc_deinit(adc)
    print(f"[calibrate] Готово: {fname}")
    return fname


def measure_wave(level_mm, seconds=15):
    """
    Опыт: ждать открытия дверцы, потом записать seconds после открытия.
    Ноль времени — момент открытия дверцы.
    """
    adc = b.adc_setup()
    ensure_dirs()
    print(f"[measure] Уровень воды {level_mm} мм. Ждём открытия дверцы ...")
    samples, duration, t0 = record(adc, seconds, wait_door=True)
    fname = os.path.join(DATA_DIR, f"wave {level_mm} mm.txt")
    b.save_data(fname, samples, duration, len(samples))
    b.adc_deinit(adc)
    print(f"[measure] Готово: {fname}  (τ отсчитывается от момента открытия дверцы)")
    return fname


def print_usage():
    print("Использование:")
    print("  python waveMeasure.py calibrate <уровень_мм> <секунды>")
    print("  python waveMeasure.py measure   <уровень_мм> [секунды=15]")
    print("")
    print("Уровни калибровки: 20, 40, 60, 80, 100 мм")
    print("Примеры:")
    print("  python waveMeasure.py calibrate 20 10")
    print("  python waveMeasure.py calibrate 100 10")
    print("  python waveMeasure.py measure   40 15")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    mode = sys.argv[1]
    try:
        level = int(sys.argv[2])
    except ValueError:
        print("Ошибка: уровень воды должен быть целым числом (мм).")
        print_usage()
        sys.exit(1)

    if mode == "calibrate":
        seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        calibrate(level, seconds)
    elif mode == "measure":
        seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 15
        measure_wave(level, seconds)
    else:
        print(f"Ошибка: неизвестный режим '{mode}'.")
        print_usage()
        sys.exit(1)
