import time
from mcp3021_driver import MCP3021
from wave_data import record, show_frequency

adc = MCP3021(5.0)
try:
    samples, duration = record(adc, 10, time.perf_counter())
finally:
    adc.deinit()

show_frequency(samples, duration)
