import time
from mcp3021_driver import MCP3021

adc = MCP3021(5.0)
try:
    start = adc.get_number()
    previous = start
    print("Начальный код:", start)
    print("Код | старшие 7 бит | младшие 3 бита | изменение кода от старта")
    while True:
        code = adc.get_number()
        if code != previous:
            print(f"{code:4}  {code >> 3:07b}          {code & 7:03b}             {code - start:+d}")
            previous = code
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    adc.deinit()
