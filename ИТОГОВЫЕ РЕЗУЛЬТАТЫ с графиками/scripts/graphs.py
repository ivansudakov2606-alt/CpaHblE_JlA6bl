from pathlib import Path
import csv
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent


def save_graph(name, times, values, ylabel):
    folder = ROOT / "plots" / "measurements"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"

    plt.figure(figsize=(8, 4))
    plt.plot(times, values, ".-", markersize=2, linewidth=1)
    plt.xlabel("Время, с")
    plt.ylabel(ylabel)
    plt.grid()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print("График сохранён:", path)


def save_table(name, times, values, ylabel):
    folder = ROOT / "data" / "checks"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Время, с", ylabel])
        writer.writerows(zip(times, values))

    print("Таблица сохранена:", path)


def plot_adc(name, samples, duration):
    times = [i * duration / len(samples) for i in range(len(samples))]
    save_graph(name, times, samples, "Код АЦП")
