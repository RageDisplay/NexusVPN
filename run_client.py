#!/usr/bin/env python3
"""
Скрипт для быстрого запуска VPN клиента
Использование: python run_client.py [--host 127.0.0.1] [--port 443] [--password password]
"""
import sys
import os
import argparse

# Добавить путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontend.main import main


if __name__ == '__main__':
    # Для простоты запускаем основное приложение
    # Параметры командной строки можно передать через аргументы
    main()
