"""
waveFunctions.py — стартовый набор функций для лабораторной «Скорость волны на поверхности».

Предназначен для импорта в скрипт измерений:
    import waveFunctions as b

Демо-режим (DEMO_MODE = True) позволяет отлаживать код без реального АЦП.
Для работы на настоящем оборудовании замените функции adc_setup(), read_adc(),
wait_door_open() на код под вашу плату (например, Raspberry Pi + MCP3008 через spidev).
"""

import time
import random
import os

# ---------- Настройки ----------
ADC_CHANNEL = 0          # канал АЦП, к которому подключён делитель напряжения с электродов
SAMPLE_INTERVAL = 0.05   # интервал между измерениями, сек (20 Гц)
DEMO_MODE = True         # True — без реального АЦП (для отладки), False — настоящее оборудование


def adc_setup():
    """
    Настроить SPI и АЦП (GPIO 9, 10, 11).
    В демо-режиме просто сообщает, что всё готово.
    """
    if DEMO_MODE:
        print("[demo] adc_setup(): АЦП сконфигурирован (виртуальный)")
        return True
    # TODO: реализуйте под ваше оборудование (например, spidev для Raspberry Pi + MCP3008)
    raise NotImplementedError("Реализуйте настройку реального АЦП")


def read_adc(channel=ADC_CHANNEL):
    """
    Прочитать одно показание АЦП (целое число, обычно 0..1023 для 10-битного АЦП).
    Возвращает число — напряжение на выходе делителя, переведённое в коды АЦП.
    """
    if DEMO_MODE:
        # Имитация «шума около нуля» когда электроды не в воде
        return random.randint(0, 30)
    # TODO: реализуйте чтение реального АЦП
    raise NotImplementedError("Реализуйте чтение реального АЦП")


def wait_door_open():
    """
    Ждать открытия торцевой двери кюветы (срабатывание геркона).
    Возвращает момент времени (Unix timestamp), когда дверь открылась.
    В демо-режиме ждёт нажатия Enter.
    """
    if DEMO_MODE:
        input("[demo] Нажмите Enter, когда дверь кюветы открыта (геркон сработал) ...")
        return time.time()
    # TODO: реализуйте чтение GPIO с геркона
    raise NotImplementedError("Реализуйте чтение геркона через GPIO")


def save_data(filename, data):
    """
    Сохранить список показаний в файл. По одному числу на строку.
    data — список чисел (показания АЦП).
    """
    with open(filename, "w", encoding="utf-8") as f:
        for value in data:
            f.write(f"{value}\n")
    print(f"[save] Сохранено {len(data)} значений в '{filename}'")


def load_data(filename):
    """
    Загрузить список показаний из файла (одно число на строку).
    """
    values = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                values.append(float(line))
    return values
