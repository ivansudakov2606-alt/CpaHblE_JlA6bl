"""
process_data.py — обработка данных (роль: Программист).

Что делает:
  1. Калибровка: по файлам calibrate_<20..120>mm.txt ищет полиномиальную
     зависимость уровня воды h от показаний АЦП.
  2. Обработка замеров: для уровней 120, 80, 40 мм переводит показания АЦП
     в уровень воды, строит график уровня от времени после открытия двери.
  3. Определяет момент прихода волны (время пробега от двери до электродов)
     и наносит скорость на график.
  4. Сохраняет графики в папку results/ и текстовый отчёт results/summary.txt.

Запуск:
    python process_data.py

Перед запуском в аудитории установите правильное расстояние дверь → электроды
в переменной DOOR_TO_ELECTRODES_MM (измеряется Экспериментатором линейкой, мм).
"""

import os
import glob
import numpy as np
import matplotlib.pyplot as plt

# ---------- Пути ----------
MEASUREMENTS_DIR = "measurements"
RESULTS_DIR = "results"

# Расстояние от торцевой двери до электродов (измеряется Experimenter'ом, мм)
# ВНИМАНИЕ: замените на реальное измеренное значение!
DOOR_TO_ELECTRODES_MM = 300

# Уровни для калибровки и замеров
CALIBRATION_LEVELS = [20, 40, 60, 80, 100, 120]  # мм
MEASURE_LEVELS = [120, 80, 40]                    # мм

# Порог для автоматического определения прихода волны:
# доля от разницы между «до волны» и «после волны».
# 0.25 — срабатывает на четверти фронта. Чем меньше, тем раньше фиксируется приход.
THRESHOLD_FRAC = 0.25

# Интервал сэмплирования (должен совпадать с SAMPLE_INTERVAL в waveMeasure.py)
SAMPLE_INTERVAL = 0.05  # сек


def ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def load_adc(filename):
    """Загрузить список показаний АЦП из файла (одно число на строку)."""
    values = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                values.append(float(line))
    return np.array(values)


def load_timestamps(filename):
    """Загрузить временные метки (сек) из файла, если есть."""
    if not os.path.exists(filename):
        return None
    vals = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                vals.append(float(line))
    return np.array(vals)


def smooth(x, window=3):
    """Простое скользящее среднее для подавления шума перед поиска фронта."""
    if window < 2 or len(x) < window:
        return x
    return np.convolve(x, np.ones(window) / window, mode="same")


def calibrate_polynomial(degree=3):
    """
    Построить полиномиальную зависимость уровня воды h от кода АЦП.
    Для каждого уровня калибровки берём среднее показание АЦП (вода стояла ровно).
    Возвращает коэффициенты полинома, объект poly1d и словарь level -> mean_adc.
    """
    levels = []
    adc_means = []

    for level in CALIBRATION_LEVELS:
        fname = os.path.join(MEASUREMENTS_DIR, f"calibrate_{level}mm.txt")
        if not os.path.exists(fname):
            print(f"[warn] Не найден файл калибровки: {fname}")
            continue
        data = load_adc(fname)
        levels.append(level)
        adc_means.append(np.mean(data))
        print(f"[calibrate] {level} мм: средний ADC = {np.mean(data):.2f} (n={len(data)})")

    if len(levels) < 2:
        print("[error] Недостаточно файлов калибровки для построения полинома.")
        return None, None, {}

    levels = np.array(levels)
    adc_means = np.array(adc_means)

    # h = f(adc) — уровень через показания АЦП
    degree = min(degree, len(levels) - 1)
    coeffs = np.polyfit(adc_means, levels, degree)
    poly = np.poly1d(coeffs)

    terms = " + ".join(f"{c:.4f}·ADC^{len(coeffs)-i-1}" for i, c in enumerate(coeffs))
    print(f"[calibrate] Полином степени {degree}: h = {terms}")

    return coeffs, poly, dict(zip(CALIBRATION_LEVELS, adc_means))


def adc_to_level(adc_values, poly):
    """Перевести массив показаний АЦП в уровень воды (мм) по калибровочному полиному."""
    return poly(adc_values)


def detect_arrival_time(times, levels, threshold_frac=THRESHOLD_FRAC):
    """
    Автоматическое определение момента прихода волны.
    Метод:
      1. Сглаживаем сигнал (скользящее среднее, окно=3).
      2. Базовый уровень — среднее первых 15% данных (до прихода волны).
      3. Фронт волны — максимальный градиент сглаженного сигнала (без краёв).
      4. Уровень после волны — среднее после фронта.
      5. Порог — доля threshold_frac от перепада между «до» и «после».
      6. Ищем первое пересечение порога после фронта.
    Возвращает время прихода (сек) и индекс в массиве.
    """
    n = len(levels)
    if n < 10:
        return None, None

    sm = smooth(levels, window=3)
    edge = 5  # исключаем края (артефакты сглаживания)

    # Базовый уровень — среднее первых 15% (до прихода волны)
    base_end = max(edge + 1, int(0.15 * n))
    baseline = np.mean(sm[:base_end])

    # Фронт волны — максимальный градиент сглаженного сигнала (без краёв)
    diff = np.diff(sm)
    valid_diff = np.abs(diff[edge:n - edge])
    max_grad_idx = int(np.argmax(valid_diff)) + edge

    # Уровень после волны — среднее после фронта
    after_start = max_grad_idx + 1
    if after_start >= n:
        return None, None
    after_level = np.mean(sm[after_start:])

    # Порог — доля от перепада между до и после
    threshold = baseline + threshold_frac * (after_level - baseline)

    # Ищем первое пересечение порога, начиная с фронта
    search_from = max_grad_idx
    arrival_idx = None
    rising = after_level > baseline
    for i in range(search_from, n):
        if rising and sm[i] >= threshold:
            arrival_idx = i
            break
        if not rising and sm[i] <= threshold:
            arrival_idx = i
            break

    if arrival_idx is None:
        arrival_idx = max_grad_idx  # fallback

    arrival_time = times[arrival_idx] if times is not None else arrival_idx * SAMPLE_INTERVAL
    return arrival_time, arrival_idx


def process_measurement(level_mm, poly, door_to_electrodes_mm=DOOR_TO_ELECTRODES_MM):
    """
    Обработать один замер: построить график уровня vs время, найти время прихода,
    вычислить скорость волны.
    """
    data_fname = os.path.join(MEASUREMENTS_DIR, f"measure_{level_mm}mm.txt")
    time_fname = os.path.join(MEASUREMENTS_DIR, f"measure_{level_mm}mm_t.txt")

    if not os.path.exists(data_fname):
        print(f"[warn] Нет файла замеров: {data_fname}")
        return None

    adc = load_adc(data_fname)
    times = load_timestamps(time_fname)
    if times is None:
        times = np.arange(len(adc)) * SAMPLE_INTERVAL

    # Перевод ADC -> уровень воды
    water_level = adc_to_level(adc, poly)

    # Время прихода волны
    arrival_time, arrival_idx = detect_arrival_time(times, water_level)

    # Скорость
    speed_mm_s = None
    if arrival_time is not None and arrival_time > 0:
        speed_mm_s = door_to_electrodes_mm / arrival_time  # мм/с

    status = f"v = {speed_mm_s:.1f} мм/с = {speed_mm_s/1000:.3f} м/с" if speed_mm_s else "v не определён"
    print(f"[process] Уровень {level_mm} мм: приход волны в t={arrival_time:.3f} сек, {status}")

    # ---------- График ----------
    plt.figure(figsize=(9, 5))
    plt.plot(times, water_level, "b-", label="Уровень воды (мм)")
    if arrival_idx is not None:
        plt.axvline(x=arrival_time, color="r", linestyle="--",
                    label=f"Приход волны: t={arrival_time:.2f} с")
    plt.axhline(y=level_mm, color="g", linestyle=":", alpha=0.5,
                label=f"Исходный уровень {level_mm} мм")
    plt.xlabel("Время после открытия двери, с")
    plt.ylabel("Уровень воды у электродов, мм")
    plt.title(f"Прогон волны, уровень воды {level_mm} мм")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plot_fname = os.path.join(RESULTS_DIR, f"level_{level_mm}mm.png")
    plt.savefig(plot_fname, dpi=150)
    plt.close()

    return {
        "level": level_mm,
        "arrival_time": arrival_time,
        "speed_mm_s": speed_mm_s,
        "plot": plot_fname,
        "times": times,
        "levels": water_level,
    }


def save_csv(results, coeffs, fname=os.path.join("results", "results.csv")):
    """Сохранить результаты в CSV (для отчёта и дополнительного анализа)."""
    import csv
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    with open(fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Параметр", "Значение"])
        writer.writerow(["Дистанция дверь -> электроды (мм)", DOOR_TO_ELECTRODES_MM])
        writer.writerow(["Степень полинома калибровки", len(coeffs)])
        writer.writerow(["Коэффициенты полинома (h = f(ADC))", coeffs.tolist()])
        writer.writerow([])
        writer.writerow(["Уровень (мм)", "Время прихода (с)", "Скорость (мм/с)", "Скорость (м/с)"])
        for r in results:
            v = r["speed_mm_s"]
            writer.writerow([r["level"], f"{r['arrival_time']:.4f}",
                             f"{v:.2f}" if v else "—",
                             f"{v/1000:.4f}" if v else "—"])
    print(f"[save] Результаты сохранены в {fname}")


def main():
    ensure_dirs()

    print("=== КАЛИБРОВКА: уровень vs показания АЦП ===")
    coeffs, poly, cal_map = calibrate_polynomial(degree=3)
    if poly is None:
        print("[error] Калибровка не удалась. Проверьте файлы в measurements/")
        return

    print("\n=== ОБРАБОТКА ЗАМЕРОВ ===")
    results = []
    for level in MEASURE_LEVELS:
        r = process_measurement(level, poly)
        if r:
            results.append(r)

    # Сохраняем текстовый отчёт
    summary_fname = os.path.join(RESULTS_DIR, "summary.txt")
    with open(summary_fname, "w", encoding="utf-8") as f:
        f.write("Итоги обработки данных\n")
        f.write("=" * 40 + "\n")
        f.write(f"Дистанция дверь -> электроды: {DOOR_TO_ELECTRODES_MM} мм\n")
        f.write(f"Полином калибровки степени {len(coeffs)-1}: {coeffs}\n\n")
        for r in results:
            f.write(f"Уровень {r['level']} мм:\n")
            f.write(f"  Время прихода волны: {r['arrival_time']:.3f} с\n")
            if r["speed_mm_s"]:
                f.write(f"  Скорость: {r['speed_mm_s']:.1f} мм/с = {r['speed_mm_s']/1000:.3f} м/с\n")
            else:
                f.write("  Скорость: не определена\n")
            f.write("\n")

    # Сохраняем CSV
    save_csv(results, coeffs)

    print(f"\n[Готово] Графики, summary.txt и results.csv сохранены в папку '{RESULTS_DIR}/'")


if __name__ == "__main__":
    main()
