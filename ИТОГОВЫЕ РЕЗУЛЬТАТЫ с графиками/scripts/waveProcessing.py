import csv
import numpy as np
import matplotlib.pyplot as plt
from wave_data import ROOT, DATA, HEIGHTS, read_data

PLOTS = ROOT / "plots"
FIT_INTERVALS = {}


def finish_plot(name, xlabel, ylabel):
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS / name, dpi=150)
    plt.close()


def calibrate():
    means = []
    for height in HEIGHTS:
        samples, duration = read_data(DATA / "calibration" / f"{height} mm.txt")
        means.append(np.mean(samples))
    steps = np.diff(means)
    if not (np.all(steps > 0) or np.all(steps < 0)):
        raise ValueError("Проверьте калибровки: средние коды должны идти по порядку.")
    curve = np.poly1d(np.polyfit(means, HEIGHTS, 2))
    grid = np.linspace(min(means), max(means), 200)
    if np.any(np.diff(curve(grid)) * steps[0] <= 0):
        raise ValueError("Калибровочная кривая меняет направление. Проверьте записи.")
    plt.scatter(means, HEIGHTS, label="Измерения")
    plt.plot(grid, curve(grid), label="Квадратичная калибровка")
    finish_plot("height-calibration.png", "Код АЦП", "Уровень, мм")
    print("Калибровка h(код), мм:", curve)
    return curve, grid[0], grid[-1]


def arrival(t, level, smooth, height):
    before = (t >= 0.2) & (t <= 0.5)
    baseline = np.mean(level[before])
    if height in FIT_INTERVALS:
        start, end = FIT_INTERVALS[height]
    else:
        threshold = max(1.0, 5 * np.std(smooth[before]))
        falling = np.flatnonzero((t > 0.5) & (smooth < baseline - threshold))
        if not len(falling):
            return None
        start = t[falling[0]] + 0.15
        end = start + 0.3
    region = (t >= start) & (t <= end)
    if np.count_nonzero(region) < 3:
        return None
    slope, intercept = np.polyfit(t[region], level[region], 1)
    if slope >= 0:
        return None
    tau = (baseline - intercept) / slope
    if not 0 < tau <= end or start - tau > 0.6:
        return None
    return tau, baseline, slope, intercept, end


def process_wave(height, length, curve, low, high):
    samples, duration = read_data(DATA / f"wave {height} mm.txt")
    code = np.array(samples)
    frequency = len(code) / duration
    if frequency <= 100 or duration < 1:
        raise ValueError(f"Проверьте длительность и частоту записи {height} мм.")
    t = np.arange(len(code)) / frequency
    bounded = np.clip(code, low, high)
    level = curve(bounded) + np.polyder(curve)(bounded) * (code - bounded)
    half = round(0.15 * frequency)
    window = 2 * half + 1
    smooth = np.convolve(np.pad(level, half, mode="edge"), np.ones(window) / window, "valid")
    result = arrival(t, level, smooth, height)
    plt.plot(t, level, color="silver", label="Уровень")
    plt.plot(t, smooth, label="Среднее за 0,3 с")
    outside = (code < low) | (code > high)
    if outside.any():
        plt.plot(t[outside], level[outside], ".", color="gray", ms=1, label="Вне калибровки (оценка)")
    tau = speed = None
    if result is not None:
        tau, baseline, slope, intercept, end = result
        speed = length / tau
        segment = np.array([tau, end])
        plt.plot([0, tau], [baseline, baseline], "k--")
        plt.plot(segment, slope * segment + intercept, "k--", label="Две прямые")
        plt.axvline(tau, color="red", label=f"τ = {tau:.3f} с")
        plt.title(f"{height} мм · L = {length:g} м · c = {speed:.3f} м/с")
    else:
        plt.title(f"{height} мм · укажите участок спада в FIT_INTERVALS")
    finish_plot(f"wave-{height}.png", "Время после открытия, с", "Уровень, мм")
    return height, frequency, tau, speed, np.sqrt(9.81 * height / 1000)


def compare(rows):
    valid = [row for row in rows if row[3] is not None]
    h = np.array([row[0] for row in valid]) / 1000
    speed = np.array([row[3] for row in valid])
    grid = np.linspace(0, 0.11, 200)
    plt.plot(grid, np.sqrt(9.81 * grid), label="Теория √(gh)")
    plt.scatter(h, speed, label="Опыт")
    finish_plot("speed-from-depth.png", "Глубина, м", "Скорость, м/с")
    if len(valid) < 3:
        print("Для оценки погрешности наклона нужны три успешных опыта.")
        return
    x = np.log(h)
    y = np.log(speed)
    (slope, intercept), covariance = np.polyfit(x, y, 1, cov=True)
    slope_error, intercept_error = np.sqrt(np.diag(covariance))
    print(f"Наклон: {slope:.3f} ± {slope_error:.3f}. Теория: 0.500")
    print(f"Свободный член: {intercept:.3f} ± {intercept_error:.3f}. Теория: 1.142")
    plt.scatter(x, y, label="Опыт")
    plt.plot(x, slope * x + intercept, label=f"Наклон {slope:.3f} ± {slope_error:.3f}")
    finish_plot("log-speed.png", "ln(h / 1 м)", "ln(c / 1 м/с)")


def main():
    length = float(input("Расстояние от дверцы до электродов, м: ").replace(",", "."))
    if not np.isfinite(length) or length <= 0:
        raise ValueError("Расстояние должно быть положительным.")
    PLOTS.mkdir(exist_ok=True)
    curve, low, high = calibrate()
    rows = []
    for height in HEIGHTS:
        row = process_wave(height, length, curve, low, high)
        rows.append(row)
        print(f"{height} мм:", "проверьте участок спада" if row[2] is None else f"τ = {row[2]:.3f} с")
    with (PLOTS / "results.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["h, мм", "f, Гц", "τ, с", "c опыта, м/с", "c теории, м/с"])
        writer.writerows(rows)
    compare(rows)


if __name__ == "__main__":
    main()
