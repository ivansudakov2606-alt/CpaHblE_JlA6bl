import time
from mcp3021_driver import MCP3021
from graphs import save_graph, save_table

adc = MCP3021(5.0)
times = []
codes = []
start = time.perf_counter()

try:
    while True:
        code = adc.get_number()
        times.append(time.perf_counter() - start)
        codes.append(code)
        print(code)
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    adc.deinit()

if codes:
    save_table("electrodes", times, codes, "Код АЦП")
    save_graph("electrodes", times, codes, "Код АЦП")