"""
waveFunctions.py — общие функции для лабораторной «Скорость волны на поверхности».

Работает в двух режимах:
  DEMO_MODE = True   — без железа, генерирует тестовые отсчёты (для отладки обработки)
  DEMO_MODE = False  — настоящее оборудование: Raspberry Pi + get-adc (MCP3021, I2C) + геркон на GPIO15

Формат данных файла (из о3):
  строка 1:  - Wave Lab
  строка 2:  duration <секунд> count <количество отсчётов>
  дальше:    по одному отсчёту АЦП на строку
"""

import time
import os
import random

# ---------- Настройки ----------
ADC_CHANNEL = 0
DOOR_PIN = 15                  # геркон подключён к GPIO15
CLOSED_LEVEL = 1               # дверца закрыта — на входе 1
SAMPLES_PER_SEC_TARGET = 1840  # целевая частота дискретизации (пример с установки)
DEMO_MODE = True               # True — без железа, False — настоящее оборудование


# =====================================================================
#  Работа с файлами (формат о3: save / read)
# =====================================================================

def save_data(filename, samples, duration, count):
    """
    Сохранить отсчёты АЦП в файл формата о3.
    Первая строка — '- Wave Lab', вторая — metadata (длительность и количество).
    """
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("- Wave Lab\n")
        f.write(f"duration {duration:.6f} count {count}\n")
        for value in samples:
            f.write(f"{value}\n")
    print(f"[save] Сохранено {count} отсчётов, {duration:.3f} с в '{filename}'")


def read_data(filename):
    """
    Прочитать файл формата о3.
    Возвращает (samples, duration, count).
    """
    samples = []
    duration = None
    count = None
    with open(filename, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        if header != "- Wave Lab":
            raise ValueError(f"Неверный заголовок файла '{filename}': {header!r}")
        meta = f.readline().strip()
        parts = meta.split()
        duration = float(parts[1])
        count = int(parts[2])
        for line in f:
            line = line.strip()
            if line:
                samples.append(float(line))
    return samples, duration, count


# =====================================================================
#  АЦП (MCP3021 через I2C)
# =====================================================================

def adc_setup(vref=5.0):
    """
    Создать и вернуть объект АЦП MCP3021.
    В демо-режиме возвращает заглушку с методом get_number().
    """
    if DEMO_MODE:
        class _DemoAdc:
            def get_number(self):
                return random.randint(0, 65535)
            def deinit(self):
                pass
        print("[demo] adc_setup(): виртуальный MCP3021 готов")
        return _DemoAdc()
    # Настоящее оборудование — импортируем драйвер из своего репозитория get
    try:
        from mcp3021_driver import MCP3021
        adc = MCP3021(vref)
        print("[adc] MCP3021 инициализирован")
        return adc
    except ImportError:
        raise ImportError(
            "mcp3021_driver.py не найден. Положите его в папку со скриптом "
            "или установите DEMO_MODE = True для отладки без железа."
        )


def read_adc(adc):
    """Прочитать один отсчёт АЦП."""
    if DEMO_MODE:
        return adc.get_number()
    return adc.get_number()


def adc_deinit(adc):
    """Освободить АЦП."""
    if not DEMO_MODE:
        adc.deinit()


# =====================================================================
#  Геркон (датчик открытия дверцы)
# =====================================================================

def gpio_setup():
    """Настроить GPIO15 как вход с подтяжкой к земле."""
    if DEMO_MODE:
        print("[demo] gpio_setup(): виртуальный GPIO15 готов")
        return None
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    return GPIO


def wait_door_open(GPIO=None):
    """
    Ждать открытия дверцы.
    Дверца закрыта — на GPIO15 уровень 1 (замыкание геркона через резистор на +3.3 В).
    Дверца открыта — уровень 0.
    Возвращает момент времени (time.time()) открытия.
    """
    if DEMO_MODE:
        input("[demo] Нажмите Enter, когда дверца кюветы открыта (геркон сработал) ...")
        return time.time()

    GPIO.setup(DOOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    print("[gpio] Ждём открытия дверцы...")
    while GPIO.input(DOOR_PIN) == CLOSED_LEVEL:
        pass
    t0 = time.time()
    print(f"[gpio] Дверца открыта в t=0 ({t0:.3f})")
    return t0


def gpio_cleanup(GPIO=None):
    if not DEMO_MODE and GPIO is not None:
        GPIO.cleanup()


# =====================================================================
#  Измерение частоты дискретизации
# =====================================================================

def measure_frequency(adc, seconds=10):
    """
    Замерить реальную частоту дискретизации: читать АЦП без пауз в течение seconds.
    Возвращает (samples, duration, measured_freq_hz).
    """
    start = time.time()
    samples = []
    while time.time() - start < seconds:
        samples.append(read_adc(adc))
    finish = time.time()
    duration = finish - start
    freq = len(samples) / duration
    print(f"[freq] Отсчётов: {len(samples)}, время: {duration:.3f} с, частота: {freq:.0f} Гц")
    return samples, duration, freq
