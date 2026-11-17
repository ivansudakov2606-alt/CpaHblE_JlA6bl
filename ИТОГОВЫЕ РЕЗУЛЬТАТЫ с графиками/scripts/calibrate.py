import time
from mcp3021_driver import MCP3021
from wave_data import DATA, ask_height, record, save_data, show_frequency

height = ask_height()
input("Закройте дверцу, дождитесь спокойной воды и нажмите Enter.")
adc = MCP3021(5.0)

try:
    samples, duration = record(adc, 10, time.perf_counter())
finally:
    adc.deinit()

save_data(DATA / "calibration" / f"{height} mm.txt", samples, duration)
show_frequency(samples, duration)
print(f"Средний код АЦП: {sum(samples) / len(samples):.2f}")
