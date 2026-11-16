"""
generate_synthetic.py — создаёт синтетические тестовые данные для отладки process_data.py.
Генерирует файлы калибровки и замеров в папку measurements/.

Физика (упрощённая):
- Показания АЦП linearly зависят от уровня воды у электродов (делитель напряжения).
- При открытии двери волна бежит со скоростью v ~ sqrt(g*h) и через время t = L/v
  доходит до электродов, после чего уровень у них начинает меняться.
- Добавляется шум (имитация реальных измерений).

Запуск:
    python generate_synthetic.py          # создать тестовые данные
    python generate_synthetic.py --clean  # удалить старые файлы measurements/*.txt перед генерацией
"""

import os
import sys
import glob
import numpy as np

MEASUREMENTS_DIR = "measurements"

# "Калибровочная" функция: код АЦП = a * уровень + b (имитация делителя напряжения)
ADC_SCALE = 8.5      # коды АЦП на мм воды
ADC_OFFSET = 120     # нулевое смещение (электроды в воздухе / сухо)


def adc_from_level(level_mm, noise=5.0):
    return ADC_SCALE * level_mm + ADC_OFFSET + np.random.normal(0, noise)


def ensure_dir():
    os.makedirs(MEASUREMENTS_DIR, exist_ok=True)


def clean_measurements():
    for f in glob.glob(os.path.join(MEASUREMENTS_DIR, "*.txt")):
        os.remove(f)
    print("Старые файлы в measurements/ удалены.")


def save_col(filename, values):
    with open(filename, "w", encoding="utf-8") as f:
        for v in values:
            f.write(f"{v:.2f}\n")


def generate_calibration(duration_sec=10, fs=20):
    """Калибровка: вода стоит ровно на уровне level, шум вокруг среднего."""
    ensure_dir()
    n = int(duration_sec * fs)
    for level in [20, 40, 60, 80, 100, 120]:
        data = np.full(n, adc_from_level(level, noise=4.0))
        save_col(os.path.join(MEASUREMENTS_DIR, f"calibrate_{level}mm.txt"), data)
        print(f"[gen] calibrate_{level}mm.txt: {n} точек")


def generate_measurement(level_mm, door_to_electrodes_mm=300,
                         duration_sec=15, fs=20):
    """
    Замер: до прихода волны уровень = level_mm.
    Волна приходит в t_arrival = L / v, v = sqrt(g*h) (упрощённо).
    После прихода уровень у электродов меняется на delta_level.
    """
    ensure_dir()
    n = int(duration_sec * fs)
    times = np.arange(n) / fs

    # Скорость волны зависит от глубины (упрощённо v ~ sqrt(g*h), h в метрах)
    g = 9.8
    h_m = level_mm / 1000.0
    v = np.sqrt(g * h_m) * 1000  # мм/с
    v = v * 0.9 + 100  # slight tweak to make interesting numbers

    t_arrival = door_to_electrodes_mm / v  # сек

    delta = 8.0   # мм — насколько меняется уровень у электродов после прихода волны
    rise_time = 0.2  # сек — как быстро поднимается фронт волны

    levels = np.full(n, level_mm)
    adc = np.zeros(n)
    for i, t in enumerate(times):
        if t >= t_arrival:
            progress = min(1.0, (t - t_arrival) / rise_time)
            levels[i] = level_mm + delta * progress
        adc[i] = adc_from_level(levels[i], noise=3.0)

    base = os.path.join(MEASUREMENTS_DIR, f"measure_{level_mm}mm")
    save_col(base + ".txt", adc)
    save_col(base + "_t.txt", times)
    print(f"[gen] measure_{level_mm}mm.txt: t_arrival={t_arrival:.3f} с, v≈{v:.0f} мм/с")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean_measurements()
    generate_calibration()
    for level in [120, 80, 40]:
        generate_measurement(level)
    print("\nГотово. Теперь запустите: python process_data.py")
