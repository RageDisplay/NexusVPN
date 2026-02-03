#!/usr/bin/env python3
"""
Скрипт для запуска VPN сервера
Использование: python run_server.py --host 0.0.0.0 --port 443 --password "your_password"
"""
import sys
import os

# Добавить путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.vpn_server import main


if __name__ == '__main__':
    main()
