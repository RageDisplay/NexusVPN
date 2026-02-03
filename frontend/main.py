"""
Главная точка входа VPN клиента
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from frontend.ui.main_window import MainWindow

# Настроить логирование
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vpn_client.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Главная функция"""
    logger.info("Запуск NexusVPN клиента...")
    
    app = QApplication(sys.argv)
    
    # Установить шрифт
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Создать главное окно
    window = MainWindow()
    window.show()
    
    logger.info("Главное окно показано")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
