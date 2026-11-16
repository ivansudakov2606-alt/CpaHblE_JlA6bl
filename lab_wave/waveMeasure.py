"""
waveMeasure.py — скрипт сбора данных (используется Экспериментатором).

Импортирует waveFunctions как b:
    import waveFunctions as b

Режимы работы (аргументы командной строки):
  calibrate <уровень_мм> <секунды>   — калибровка на стоявшей воде (20, 40, ..., 120 мм)
  measure   <уровень_мм> [сек=15]   — замер пробега волны после открытия двери

Примеры:
    python waveMeasure.py calibrate 20 10
    python waveMeasure.py measure 120
    python waveMeasure.py measure 80 15
"""

import sys
import os
import time
import waveFunctions as b

RESULTS_DIR = "measurements"


def ensure_dir():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)


def calibrate(level_mm, seconds):
    """
    Собирать показания АЦП в течение `seconds` секунд на стоявшей воде уровня `level_mm`.
    Сохраняет в measurements/calibrate_<level>mm.txt
    """
    b.adc_setup()
    ensure_dir()
    print(f"[calibrate] Уровень воды {level_mm} мм, сбор {seconds} сек ...")
    print("   (держите уровень воды неизменным, не трогайте кювету)")
    end = time.time() + seconds
    data = []
    while time.time() < end:
        data.append(b.read_adc())
        # прогресс-индикатор
        remaining = int(end - time.time())
        print(f"\r   осталось {remaining} сек...", end="", flush=True)
        time.sleep(b.SAMPLE_INTERVAL)
    print()
    fname = os.path.join(RESULTS_DIR, f"calibrate_{level_mm}mm.txt")
    b.save_data(fname, data)
    print(f"[calibrate] Готово: {fname}")
    return fname


def measure_wave(level_mm, seconds=15):
    """
    Ждать открытия двери, затем собирать показания в течение `seconds` секунд.
    Сохраняет в measurements/measure_<level>mm.txt и _t.txt (временные метки).
    """
    b.adc_setup()
    ensure_dir()
    print(f"[measure] Уровень воды {level_mm} мм.")
    print("   Ожидание открытия двери кюветы (геркон)...")
    t0 = b.wait_door_open()
    print(f"   Дверь открыта в t=0. Сбор {seconds} сек ...")
    end = time.time() + seconds
    data = []
    timestamps = []
    while time.time() < end:
        data.append(b.read_adc())
        timestamps.append(time.time() - t0)
        remaining = int(end - time.time())
        print(f"\r   осталось {remaining} сек...", end="", flush=True)
        time.sleep(b.SAMPLE_INTERVAL)
    print()
    base = os.path.join(RESULTS_DIR, f"measure_{level_mm}mm")
    b.save_data(base + ".txt", data)
    # Сохраняем временные метки отдельно (удобно для обработки)
    with open(base + "_t.txt", "w", encoding="utf-8") as f:
        for t in timestamps:
            f.write(f"{t:.6f}\n")
    print(f"[measure] Готово: {base}.txt  и  {base}_t.txt")
    return base


def print_usage():
    print("Использование:")
    print("  python waveMeasure.py calibrate <уровень_мм> <секунды>")
    print("  python waveMeasure.py measure   <уровень_мм> [секунды=15]")
    print("")
    print("Примеры:")
    print("  python waveMeasure.py calibrate 20 10")
    print("  python waveMeasure.py calibrate 120 10")
    print("  python waveMeasure.py measure   120")
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
