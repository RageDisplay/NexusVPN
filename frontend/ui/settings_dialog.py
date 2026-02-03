"""
Диалог расширенных настроек
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QCheckBox, QSpinBox,
                             QGroupBox, QMessageBox, QTabWidget, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from frontend.ui.styles import COLORS


class SettingsDialog(QDialog):
    """Диалог расширенных настроек"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Настройки NexusVPN')
        self.setGeometry(200, 200, 600, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
        """)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализировать UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка сети
        network_tab = self._create_network_tab()
        tabs.addTab(network_tab, "Сеть")
        
        # Вкладка безопасности
        security_tab = self._create_security_tab()
        tabs.addTab(security_tab, "Безопасность")
        
        # Вкладка логирования
        logging_tab = self._create_logging_tab()
        tabs.addTab(logging_tab, "Логирование")
        
        layout.addWidget(tabs)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)
        
        apply_button = QPushButton('Применить')
        apply_button.clicked.connect(self._on_apply)
        buttons_layout.addWidget(apply_button)
        
        cancel_button = QPushButton('Отмена')
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def _create_network_tab(self) -> QWidget:
        """Создать вкладку сети"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Timeout
        timeout_group = QGroupBox("Таймауты")
        timeout_layout = QVBoxLayout()
        
        timeout_input_layout = QHBoxLayout()
        timeout_input_layout.addWidget(QLabel("Таймаут сокета (сек):"))
        self.socket_timeout = QSpinBox()
        self.socket_timeout.setValue(30)
        self.socket_timeout.setMinimum(5)
        self.socket_timeout.setMaximum(300)
        timeout_input_layout.addWidget(self.socket_timeout)
        timeout_input_layout.addStretch()
        timeout_layout.addLayout(timeout_input_layout)
        
        keepalive_layout = QHBoxLayout()
        keepalive_layout.addWidget(QLabel("Интервал keepalive (сек):"))
        self.keepalive_interval = QSpinBox()
        self.keepalive_interval.setValue(20)
        self.keepalive_interval.setMinimum(5)
        self.keepalive_interval.setMaximum(300)
        keepalive_layout.addWidget(self.keepalive_interval)
        keepalive_layout.addStretch()
        timeout_layout.addLayout(keepalive_layout)
        
        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)
        
        # Буфер
        buffer_group = QGroupBox("Буфер")
        buffer_layout = QVBoxLayout()
        
        buffer_size_layout = QHBoxLayout()
        buffer_size_layout.addWidget(QLabel("Размер буфера (байт):"))
        self.buffer_size = QSpinBox()
        self.buffer_size.setValue(4096)
        self.buffer_size.setMinimum(512)
        self.buffer_size.setMaximum(65536)
        self.buffer_size.setSingleStep(512)
        buffer_size_layout.addWidget(self.buffer_size)
        buffer_size_layout.addStretch()
        buffer_layout.addLayout(buffer_size_layout)
        
        buffer_group.setLayout(buffer_layout)
        layout.addWidget(buffer_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_security_tab(self) -> QWidget:
        """Создать вкладку безопасности"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Обфусцировка
        obfuscation_group = QGroupBox("Обфусцировка")
        obfuscation_layout = QVBoxLayout()
        
        self.enable_obfuscation = QCheckBox("Включить обфусцировку трафика")
        self.enable_obfuscation.setChecked(True)
        obfuscation_layout.addWidget(self.enable_obfuscation)
        
        self.enable_dpi_bypass = QCheckBox("Включить DPI bypass")
        self.enable_dpi_bypass.setChecked(True)
        obfuscation_layout.addWidget(self.enable_dpi_bypass)
        
        obfuscation_group.setLayout(obfuscation_layout)
        layout.addWidget(obfuscation_group)
        
        # Криптография
        crypto_group = QGroupBox("Криптография")
        crypto_layout = QVBoxLayout()
        
        crypto_layout.addWidget(QLabel("Алгоритм: ChaCha20-Poly1305 AEAD"))
        crypto_layout.addWidget(QLabel("Key Exchange: Curve25519 ECDH"))
        crypto_layout.addWidget(QLabel("KDF: PBKDF2-HMAC-SHA256 (100k iterations)"))
        
        crypto_group.setLayout(crypto_layout)
        layout.addWidget(crypto_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_logging_tab(self) -> QWidget:
        """Создать вкладку логирования"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Уровень логирования
        logging_group = QGroupBox("Логирование")
        logging_layout = QVBoxLayout()
        
        self.enable_logging = QCheckBox("Включить логирование")
        self.enable_logging.setChecked(True)
        logging_layout.addWidget(self.enable_logging)
        
        self.verbose_logging = QCheckBox("Подробное логирование (DEBUG)")
        self.verbose_logging.setChecked(False)
        logging_layout.addWidget(self.verbose_logging)
        
        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)
        
        # Файл логов
        log_file_group = QGroupBox("Файл логов")
        log_file_layout = QVBoxLayout()
        
        log_file_input_layout = QHBoxLayout()
        log_file_input_layout.addWidget(QLabel("Путь:"))
        self.log_file_input = QLineEdit()
        self.log_file_input.setText("vpn_client.log")
        log_file_input_layout.addWidget(self.log_file_input)
        log_file_layout.addLayout(log_file_input_layout)
        
        open_logs_button = QPushButton("Открыть папку с логами")
        open_logs_button.clicked.connect(self._open_logs_folder)
        log_file_layout.addWidget(open_logs_button)
        
        log_file_group.setLayout(log_file_layout)
        layout.addWidget(log_file_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _on_apply(self):
        """Применить настройки"""
        QMessageBox.information(self, "Настройки", "Настройки применены")
    
    def _open_logs_folder(self):
        """Открыть папку с логами"""
        import subprocess
        import os
        
        log_path = os.path.expanduser("~")
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(log_path)
            else:
                subprocess.Popen(['xdg-open', log_path])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку: {str(e)}")
