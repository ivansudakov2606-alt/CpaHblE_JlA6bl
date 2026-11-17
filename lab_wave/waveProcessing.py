"""
waveProcessing.py — обработка данных (Программист).

Этапы (п3.5 + п3.6):
  1. Калибровка: по файлам data/calibration/20 mm.txt … 100 mm.txt
     подбирает многочлен, переводящий отсчёты АЦП в уровень воды (мм).
     Сохраняет график height-calibration.png.
  2. Опыты: для wave 20 mm.txt … 100 mm.txt переводит отсчёты в уровень,
     сглаживает (0.3 с), ищет момент прихода волны τ (метод двух прямых),
     считает скорость c = L / τ.
     Рисует график уровня vs время с отмеченным τ и рамкой L, τ, c.
  3. Теория: график c(h) с кривой √(gh) и экспериментальными точками.
  4. Проверка: ln c от ln h, наклон ≈ 0.5.

Перед запуском в аудитории установите правильное расстояние L (м) —
измеряется Экспериментатором линейкой и передаётся Программисту.

Запуск:
    python waveProcessing.py
"""

import os
import glob
import numpy as np
import matplotlib.pyplot as plt

# ---------- Пусти и настройки ----------
DATA_DIR = "data"
CALIBRATION_DIR = os.path.join(DATA_DIR, "calibration")
PLOTS_DIR = "plots"

HEIGHTS = [20, 40, 60, 80, 100]          # мм, уровни калибровки и опытов
POLY_DEGREE = 3                          # степень калибровочного многочлена (2 или 3)

# Расстояние от дверцы до электродов (м). ОДНО для всех опытов, измеряется линейкой.
# ВНИМАНИЕ: замените на реальное измеренное значение! В примере пособия L = 1.00 м.
L = 1.00

# Сглаживание для устранения 4-Гц дроби после открытия дверцы (п3.6)
SMOOTH_WINDOW_SEC = 0.3

# Участок для оценки уровня «до волны» (сек) — волна заведомо ещё не пришла
PRE_WAVE_T0 = 0.2
PRE_WAVE_T1 = 0.5

# Длина участка под аппроксимацию спада для метода двух прямых (сек)
FIT_WINDOW_SEC = 0.3

# Во сколько шумов уровень должен упасть, чтобы считать это началом спада (грубая оценка)
DROP_SIGMA = 5
# Минимальное абсолютное падение уровня (мм), ниже которого срабатывание не считается волной.
# Защищает от ложных срабатываний на шум при очень чистом сигнале.
MIN_ABS_DROP_MM = 1.0

g = 9.81  # ускорение свободного падения, м/с^2


# =====================================================================
#  Чтение и калибровка
# =====================================================================

def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)


def read_height_file(filepath):
    """Прочитать один файл с отсчётами ( формат о3 )."""
    samples, duration, count = b_read(filepath)
    return np.array(samples), duration, count


def b_read(filepath):
    """Локальный парсер файлов формата о3 (без импорта waveFunctions, чтобы не зависеть от железа)."""
    samples = []
    duration = None
    count = None
    with open(filepath, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        if header != "- Wave Lab":
            raise ValueError(f"Неверный заголовок '{filepath}': {header!r}")
        meta = f.readline().strip().split()
        # формат: duration <секунды> count <количество>
        duration = float(meta[1])
        count = int(meta[3])
        for line in f:
            line = line.strip()
            if line:
                samples.append(float(line))
    return samples, duration, count


def calibrate_polynomial():
    """
    Подобрать многочлен уровня от отсчёта АЦП по файлам калибровки.
    Возвращает coeffs (для np.polyval, где x = отсчёт ADC), poly1d объект,
    и списки heights_m, adc_means для отчёта.
    """
    heights_m = np.array(HEIGHTS) / 1000.0  # м
    adc_means = []
    adc_stds = []

    for h in HEIGHTS:
        fpath = os.path.join(CALIBRATION_DIR, f"{h} mm.txt")
        if not os.path.exists(fpath):
            print(f"[warn] Нет файла калибровки: {fpath}")
            continue
        samples, duration, count = read_height_file(fpath)
        adc_means.append(np.mean(samples))
        adc_stds.append(np.std(samples))
        print(f"[calibrate] {h} мм: средний ADC = {np.mean(samples):.1f} ± {np.std(samples):.1f} (n={count})")

    if len(adc_means) < 3:
        raise RuntimeError("Недостаточно файлов калибровки для подбора многочлена.")

    adc_means = np.array(adc_means)
    heights_m = heights_m[:len(adc_means)]

    # Многочлен: уровень = f(отсчёт ADC)
    coeffs = np.polyfit(adc_means, heights_m, POLY_DEGREE)
    poly = np.poly1d(coeffs)

    # Проверка отклонений точек от кривой
    preds = poly(adc_means)
    deviations_mm = np.abs(preds - heights_m) * 1000.0
    print(f"[calibrate] Многочлен степени {POLY_DEGREE}:")
    print(f"[calibrate]   коэффициенты: {coeffs}")
    print(f"[calibrate]   макс. отклонение точки от кривой: {deviations_mm.max():.2f} мм")

    # ---------- График калибровки ----------
    plt.figure(figsize=(7, 5))
    adc_fine = np.linspace(adc_means.min(), adc_means.max(), 300)
    level_fine = poly(adc_fine) * 1000.0  # мм
    plt.plot(adc_fine, level_fine, "b-", label=f"многочлен степени {POLY_DEGREE}")
    plt.scatter(adc_means, heights_m * 1000.0, color="orange", zorder=5, label="калибровка")
    plt.xlabel("отсчёт АЦП")
    plt.ylabel("уровень воды, мм")
    plt.title("Калибровка датчика уровня")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    cal_plot = os.path.join(PLOTS_DIR, "height-calibration.png")
    plt.savefig(cal_plot, dpi=150)
    plt.close()
    print(f"[save] График калибровки: {cal_plot}")

    return coeffs, poly, heights_m, adc_means


def adc_to_level_m(adc_values, poly, min_adc, max_adc):
    """Перевести отсчёты АЦП в уровень (м), обрезав к диапазону калибровки."""
    clipped = np.clip(adc_values, min_adc, max_adc)
    return poly(clipped)


# =====================================================================
#  Метод двух прямых для поиска момента прихода волны τ
# =====================================================================

def smooth_signal(signal, window_sec, duration, count):
    """Скользящее среднее за window_sec секунд. Края補щаются краевыми значениями,
    чтобы не было искусственного падения к концу записи (артефакт mode='same')."""
    k = max(3, int(window_sec * count / duration))
    if k < 3:
        return signal.copy()
    pad = k // 2
    padded = np.pad(signal, pad, mode="edge")
    return np.convolve(padded, np.ones(k) / k, mode="valid")


def find_tau_two_lines(t, level_smooth, duration):
    """
    Метод двух прямых (т3.5):
      1. Средний уровень на участке PRE_WAVE_T0..PRE_WAVE_T1 (до волны).
      2. Первая точка, где уровень упал ниже среднего на DROP_SIGMA шумов — грубый старт спада.
      3. Прямая по следующим FIT_WINDOW_SEC сек спада.
      4. τ — пересечение горизонтали (уровень до волны) и этой прямой.
    Возвращает τ (сек) или None.
    """
    n = len(level_smooth)
    if n < 10:
        return None

    # Индексы для участка «до волны»
    i0 = int(PRE_WAVE_T0 * n / duration)
    i1 = int(PRE_WAVE_T1 * n / duration)
    if i1 <= i0:
        i1 = i0 + 1

    baseline = np.mean(level_smooth[i0:i1])
    noise = np.std(level_smooth[i0:i1])
    if noise == 0:
        noise = 1.0

    # Грубая оценка начала спада: первое существенное падение уровня.
    # Порог — максимум из «нескольких шумов» и минимального абсолютного падения,
    # чтобы не срабатывать на случайные колебания при чистом сигнале.
    threshold_drop = max(DROP_SIGMA * noise, MIN_ABS_DROP_MM)
    drop_start = None
    for i in range(i1, n):
        if level_smooth[i] < baseline - threshold_drop:
            drop_start = i
            break
    if drop_start is None:
        return None

    # Аппроксимируем начало спада прямой на следующем окне
    fit_end = min(drop_start + int(FIT_WINDOW_SEC * n / duration), n - 1)
    if fit_end <= drop_start + 2:
        return None

    t_fit = t[drop_start:fit_end]
    y_fit = level_smooth[drop_start:fit_end]
    # Прямая y = a*t + b
    a, b = np.polyfit(t_fit, y_fit, 1)

    # Пересечение с горизонталью y = baseline: baseline = a*tau + b  =>  tau = (baseline - b) / a
    if abs(a) < 1e-9:
        return None
    tau = (baseline - b) / a

    # Ограничим τ разумными пределами (внутри записи)
    if tau < t[0] or tau > t[-1]:
        tau = None
    return tau, baseline


# =====================================================================
#  Обработка одного опыта
# =====================================================================

def process_one_experiment(height_mm, poly, min_adc, max_adc):
    """
    Обработать один файл опыта wave H mm.txt.
    Возвращает словарь с результатами или None.

    Волна ищется в «сырых» отсчётах АЦП (без обрезки по диапазону калибровки),
    потому что уровень может упасть ниже минимального калибровочного уровня.
    Перевод в миллиметры — только для отображения на графике.
    """
    fpath = os.path.join(DATA_DIR, f"wave {height_mm} mm.txt")
    if not os.path.exists(fpath):
        print(f"[warn] Нет файла опыта: {fpath}")
        return None

    samples, duration, count = read_height_file(fpath)
    adc = np.array(samples, dtype=float)
    t = np.linspace(0, duration, count)

    # ---------- Поиск τ в пространстве отсчётов АЦП ----------
    adc_smooth = smooth_signal(adc, SMOOTH_WINDOW_SEC, duration, count)
    result_tau = find_tau_two_lines(t, adc_smooth, duration)

    speed_m_s = None
    tau_val = None
    if result_tau is not None:
        tau_val, baseline_adc = result_tau
        speed_m_s = L / tau_val
        print(f"[process] {height_mm} мм: τ = {tau_val:.3f} с, c = {speed_m_s:.3f} м/с (L={L} м)")
    else:
        print(f"[process] {height_mm} мм: τ не найден автоматически (нужен ручной ввод)")

    # ---------- Уровень (мм) для графика (с обрезкой по диапазону калибровки) ----------
    level_m = adc_to_level_m(adc, poly, min_adc, max_adc)
    level_mm = level_m * 1000.0
    level_smooth_mm = smooth_signal(level_mm, SMOOTH_WINDOW_SEC, duration, count)

    # ---------- График уровня vs время ----------
    plt.figure(figsize=(8, 4.5))
    plt.plot(t, level_mm, "b-", linewidth=0.8, label="уровень воды")
    if result_tau is not None:
        plt.axvline(tau_val, color="r", linestyle="--", label=f"τ = {tau_val:.2f} с")
        # Рамка с параметрами
        textstr = f"L = {L:.2f} [м]\nτ = {tau_val:.3f} [с]\nc = {speed_m_s:.3f} [м/с]"
        plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes,
                 fontsize=10, verticalalignment="top",
                 bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8})
    plt.xlabel("время после открытия дверцы, с")
    plt.ylabel("уровень воды, мм")
    plt.title(f"Опыт, уровень воды {height_mm} мм")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_path = os.path.join(PLOTS_DIR, f"wave {height_mm} mm.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()

    return {
        "height": height_mm,
        "t": t,
        "level_mm": level_mm,
        "level_smooth": level_smooth_mm,
        "tau": tau_val,
        "speed_m_s": speed_m_s,
        "plot": plot_path,
    }


# =====================================================================
#  Теоретические графики
# =====================================================================

def plot_theory_and_results(results):
    """
    График c(h): teoría √(gh) + экспериментальные точки.
    График ln c от ln h с прямой и наклоном.
    """
    heights = [r["height"] for r in results if r["speed_m_s"] is not None]
    speeds = [r["speed_m_s"] for r in results if r["speed_m_s"] is not None]
    if len(heights) < 2:
        print("[warn] Недостаточно опытов с найденным τ для графиков теории.")
        return

    h_m = np.array(heights) / 1000.0
    c_exp = np.array(speeds)

    # --- График 1: c(h) ---
    plt.figure(figsize=(7, 5))
    h_fine = np.linspace(0, 0.12, 200)
    c_theory = np.sqrt(g * h_fine)
    plt.plot(h_fine * 1000, c_theory, "b-", label="теория c = √(gh)")
    plt.scatter(heights, c_exp, color="orange", zorder=5, label="опыт")
    plt.xlabel("глубина, мм")
    plt.ylabel("скорость волны, м/с")
    plt.title("Скорость волны от глубины")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    p1 = os.path.join(PLOTS_DIR, "speed-from-depth.png")
    plt.savefig(p1, dpi=150)
    plt.close()
    print(f"[save] График c(h): {p1}")

    # --- График 2: ln c от ln h ---
    ln_h = np.log(h_m)
    ln_c = np.log(c_exp)
    slope, intercept = np.polyfit(ln_h, ln_c, 1)
    # Погрешность наклона через ковариацию
    (slope2, intercept2), cov = np.polyfit(ln_h, ln_c, 1, cov=True)
    slope_err = np.sqrt(cov[0, 0])
    intercept_err = np.sqrt(cov[1, 1])

    plt.figure(figsize=(7, 5))
    plt.scatter(ln_h, ln_c, color="orange", zorder=5, label="опыт")
    ln_h_fit = np.linspace(ln_h.min(), ln_h.max(), 100)
    ln_c_fit = slope * ln_h_fit + intercept
    plt.plot(ln_h_fit, ln_c_fit, "b-",
             label=f"прямая: наклон {slope:.3f} ± {slope_err:.3f}")
    plt.xlabel("ln h")
    plt.ylabel("ln c")
    plt.title("Проверка теории: ln c от ln h (наклон должен быть ≈ 0.5)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    p2 = os.path.join(PLOTS_DIR, "ln-speed-from-depth.png")
    plt.savefig(p2, dpi=150)
    plt.close()
    print(f"[save] График ln c от ln h: {p2}")

    print(f"\n[теория] Наклон ln c от ln h: {slope:.3f} ± {slope_err:.3f} (теория 0.5)")
    print(f"[теория] Свободный член: {intercept:.3f} ± {intercept_err:.3f} (теория ½·ln g ≈ {0.5*np.log(g):.3f})")

    return slope, slope_err, intercept, intercept_err


# =====================================================================
#  Основной запуск
# =====================================================================

def save_results_csv(results, coeffs, fname=os.path.join("plots", "results.csv")):
    import csv
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Параметр", "Значение"])
        w.writerow(["L (м)", L])
        w.writerow(["Степень калибровочного многочлена", POLY_DEGREE])
        w.writerow(["Коэффициенты уровня = f(ADC)", coeffs.tolist()])
        w.writerow([])
        w.writerow(["Уровень (мм)", "τ (с)", "c expériment (м/с)", "c теория √(gh) (м/с)", "Расхождение (%)"])
        for r in results:
            h = r["height"]
            tau = r["tau"]
            c = r["speed_m_s"]
            c_th = np.sqrt(g * h / 1000.0)
            diff = (c - c_th) / c_th * 100 if c else None
            w.writerow([h, f"{tau:.4f}" if tau else "—",
                        f"{c:.4f}" if c else "—",
                        f"{c_th:.4f}", f"{diff:+.1f}" if diff is not None else "—"])
    print(f"[save] Таблица результатов: {fname}")


def main():
    ensure_dirs()

    print("=== П3.5 КАЛИБРОВКА: уровень vs отсчёт АЦП ===")
    coeffs, poly, heights_m, adc_means = calibrate_polynomial()
    min_adc = float(adc_means.min())
    max_adc = float(adc_means.max())

    print("\n=== П3.6 ОПЫТЫ: уровень vs время, τ, скорость ===")
    results = []
    for h in HEIGHTS:
        r = process_one_experiment(h, poly, min_adc, max_adc)
        if r:
            results.append(r)

    # Сохранить таблицу
    save_results_csv(results, coeffs)

    # Теоретические графики
    print("\n=== П3.6 СРАВНЕНИЕ С ТЕОРИЕЙ ===")
    plot_theory_and_results(results)

    print(f"\n[Готово] Графики в папке '{PLOTS_DIR}/', таблица в plots/results.csv")


if __name__ == "__main__":
    main()
