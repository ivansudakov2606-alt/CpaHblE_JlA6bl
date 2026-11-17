import time
import RPi.GPIO as GPIO
from mcp3021_driver import MCP3021
from wave_data import DATA, ask_height, record, save_data, show_frequency

height = ask_height()
GPIO.setmode(GPIO.BCM)
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
try:
    adc = MCP3021(5.0)
    try:
        if GPIO.input(15) == 0:
            print("Закройте дверцу.")
            while GPIO.input(15) == 0:
                time.sleep(0.01)
        print("Готово. Резко откройте дверцу.", flush=True)
        while GPIO.input(15) == 1:
            pass
        start = time.perf_counter()
        samples, duration = record(adc, 15, start)
    finally:
        adc.deinit()
finally:
    GPIO.cleanup()

save_data(DATA / f"wave {height} mm.txt", samples, duration)
show_frequency(samples, duration)
