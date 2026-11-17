"""
generate_synthetic.py — синтетические тестовые данные в формате о3 (- Wave Lab).
Генерирует калибровку и пять опытов в папку data/.

Физика (упрощённая, как в пособии):
- Отсчёт АЦП линейно растёт с уровнем (с небольшой нелинейностью у предела).
- При открытии дверцы уровень у электродов сначала стоит, потом падает, когда приходит волна падения.
- τ = L / sqrt(g*h), L = 1 м.
- Шум ~1-2 отсчёта, частота ~1840 Гц.
- После открытия дверцы на 0.3-0.5 с добавляется дрожь 4 Гц (рывок дверцы) — не волна.

Запуск:
    python generate_synthetic.py          # создать тестовые данные
    python generate_synthetic.py --clean  # удалить старые data/*.txt перед генерацией
"""

import os
import sys
import glob
import numpy as np

DATA_DIR = "data"
CALIBRATION_DIR = os.path.join(DATA_DIR, "calibration")
L = 1.00  # м, дверца -> электроды
FS_TARGET = 1840  # Гц


def ensure_dirs():
    os.makedirs(CALIBRATION_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def clean():
    for d in [CALIBRATION_DIR, DATA_DIR]:
        for f in glob.glob(os.path.join(d, "*.txt")):
            os.remove(f)
    print("Старые файлы в data/ удалены.")


def save_col(filepath, samples, duration):
    count = len(samples)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("- Wave Lab\n")
        f.write(f"duration {duration:.6f} count {count}\n")
        for v in samples:
            f.write(f"{v:.2f}\n")
    print(f"[gen] {os.path.basename(filepath)}: {count} отсчётов, {duration:.2f} с")


def adc_from_level(level_mm, noise=0.0):
    """Базовый отсчёт АЦП от уровня (мм) без шума. Шум добавляется отдельно по выборке."""
    # Базовая линейная зависимость (пример из пособия: 20->113, 100->621)
    base = 105 + 5.2 * level_mm
    # Нелинейность у верхнего предела (датчик насыщается около 3 В)
    saturation = 0.0012 * level_mm ** 2
    return base + saturation


def generate_calibration(duration_sec=10):
    ensure_dirs()
    n = int(duration_sec * FS_TARGET)
    t = np.arange(n) / FS_TARGET
    for level in [20, 40, 60, 80, 100]:
        data = np.full(n, adc_from_level(level)) + np.random.normal(0, 1.5, n)
        save_col(os.path.join(CALIBRATION_DIR, f"{level} mm.txt"), data, duration_sec)


def generate_wave_experiment(level_mm, duration_sec=15):
    """Запись после открытия дверцы: уровень стоит, потом падает при приходе волны."""
    ensure_dirs()
    n = int(duration_sec * FS_TARGET)
    t = np.arange(n) / FS_TARGET

    # Скорость волны по теории мелкой воды
    v = np.sqrt(9.81 * level_mm / 1000.0)  # м/с
    tau = L / v  # момент прихода волны

    # Дрожь после открытия дверцы (4 Гц, до ~0.5 с) — не волна
    jitter = np.zeros(n)
    mask_jit = (t > 0) & (t < 0.5)
    jitter[mask_jit] = 1.5 * np.sin(2 * np.pi * 4 * t[mask_jit])

    # Уровень: стоит на level_mm, после tau начинает падать (линейно за 2 сек)
    level = np.full(n, float(level_mm))
    drop_start = tau
    drop_end = tau + 2.0
    drop_mask = (t >= drop_start) & (t <= drop_end)
    level[drop_mask] = level_mm - (level_mm - 5.0) * (t[drop_mask] - drop_start) / (drop_end - drop_start)
    level[t > drop_end] = 5.0

    level += jitter

    adc = np.array([adc_from_level(ll) + np.random.normal(0, 1.2) for ll in level])
    save_col(os.path.join(DATA_DIR, f"wave {level_mm} mm.txt"), adc, duration_sec)
    print(f"[gen] wave {level_mm} mm.txt:理论 tau={tau:.3f} с, v={v:.3f} м/с")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
    generate_calibration()
    for level in [20, 40, 60, 80, 100]:
        generate_wave_experiment(level)
    print("\nГотово. Теперь запустите: python waveProcessing.py")
