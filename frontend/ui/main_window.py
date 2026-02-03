"""
Главное окно VPN клиента
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox,
                             QCheckBox, QSpinBox, QGroupBox, QStatusBar,
                             QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
                             QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor
from frontend.ui.styles import STYLE_SHEET, COLORS, WINDOW_WIDTH, WINDOW_HEIGHT
from frontend.ui.settings_dialog import SettingsDialog
from frontend.vpn_client import VPNClient
import logging

logger = logging.getLogger(__name__)


class ConnectionThread(QThread):
    """Поток подключения к VPN"""
    
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, vpn_client: VPNClient):
        super().__init__()
        self.vpn_client = vpn_client
        self.action = None  # 'connect' или 'disconnect'
    
    def run(self):
        try:
            if self.action == 'connect':
                if self.vpn_client.connect():
                    self.connected.emit()
                else:
                    self.error.emit("Не удалось подключиться к VPN серверу")
            elif self.action == 'disconnect':
                self.vpn_client.disconnect()
                self.disconnected.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.vpn_client = None
        self.connection_thread = None
        self.stats_timer = QTimer()
        
        self.setWindowTitle('NexusVPN - Безопасная VPN')
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(STYLE_SHEET)
        
        # Создать основной виджет
        self.init_ui()
        
        # Таймер для обновления статистики
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(1000)  # Обновлять каждую секунду
    
    def init_ui(self):
        """Инициализировать UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === Заголовок ===
        title_label = QLabel('NexusVPN')
        title_font = QFont('Segoe UI', 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        status_label = QLabel('Отключено')
        status_font = QFont('Segoe UI', 12)
        status_label.setFont(status_font)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.status_label = status_label
        main_layout.addWidget(status_label)
        
        # === Вкладки ===
        tabs = QTabWidget()
        
        # Вкладка подключения
        connection_tab = self._create_connection_tab()
        tabs.addTab(connection_tab, "Подключение")
        
        # Вкладка статистики
        stats_tab = self._create_stats_tab()
        tabs.addTab(stats_tab, "Статистика")
        
        # Вкладка настроек
        settings_tab = self._create_settings_tab()
        tabs.addTab(settings_tab, "Настройки")
        
        main_layout.addWidget(tabs)
        
        # === Кнопки управления ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.connect_button = QPushButton('Подключиться')
        self.connect_button.setMinimumHeight(45)
        self.connect_button.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        self.connect_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        buttons_layout.addWidget(self.connect_button)
        
        self.disconnect_button = QPushButton('Отключиться')
        self.disconnect_button.setMinimumHeight(45)
        self.disconnect_button.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        self.disconnect_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: #e53935;
            }}
            QPushButton:disabled {{
                background-color: #888;
            }}
        """)
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_button.setEnabled(False)
        buttons_layout.addWidget(self.disconnect_button)
        
        main_layout.addLayout(buttons_layout)
        
        # === Статус бар ===
        self.statusBar().setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text']};")
        self.statusBar().showMessage('Готово к подключению')
        
        central_widget.setLayout(main_layout)
    
    def _create_connection_tab(self) -> QWidget:
        """Создать вкладку подключения"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Группа "Параметры сервера"
        server_group = QGroupBox("Параметры сервера")
        server_layout = QVBoxLayout()
        
        # Хост
        host_layout = QHBoxLayout()
        host_label = QLabel("Адрес сервера:")
        host_label.setMinimumWidth(100)
        self.host_input = QLineEdit()
        self.host_input.setText("127.0.0.1")
        self.host_input.setPlaceholderText("IP или домен сервера")
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_input)
        server_layout.addLayout(host_layout)
        
        # Порт
        port_layout = QHBoxLayout()
        port_label = QLabel("Порт:")
        port_label.setMinimumWidth(100)
        self.port_input = QSpinBox()
        self.port_input.setMinimum(1)
        self.port_input.setMaximum(65535)
        self.port_input.setValue(443)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        server_layout.addLayout(port_layout)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Группа "Аутентификация"
        auth_group = QGroupBox("Аутентификация")
        auth_layout = QVBoxLayout()
        
        # Пароль
        password_layout = QHBoxLayout()
        password_label = QLabel("Пароль:")
        password_label.setMinimumWidth(100)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setText("pass")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        auth_layout.addLayout(password_layout)
        
        # Показать пароль
        self.show_password_check = QCheckBox("Показать пароль")
        self.show_password_check.stateChanged.connect(self._toggle_password_visibility)
        auth_layout.addWidget(self.show_password_check)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # Группа "Протокол"
        protocol_group = QGroupBox("Обфусцировка трафика")
        protocol_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Режим:")
        mode_label.setMinimumWidth(100)
        self.obfuscation_combo = QComboBox()
        self.obfuscation_combo.addItems(['HTTPS', 'HTTP/2', 'WebSocket', 'Random', 'None'])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.obfuscation_combo)
        mode_layout.addStretch()
        protocol_layout.addLayout(mode_layout)
        
        # DPI Bypass
        self.dpi_bypass_check = QCheckBox("Включить DPI bypass (избегание блокировок)")
        self.dpi_bypass_check.setChecked(True)
        protocol_layout.addWidget(self.dpi_bypass_check)
        
        protocol_group.setLayout(protocol_layout)
        layout.addWidget(protocol_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_stats_tab(self) -> QWidget:
        """Создать вкладку статистики"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Статистика подключения
        stats_group = QGroupBox("Статистика подключения")
        stats_layout = QVBoxLayout()
        
        # Время подключения
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Время подключения:"))
        self.time_label = QLabel("--:--")
        self.time_label.setStyleSheet(f"color: {COLORS['primary']};")
        time_layout.addWidget(self.time_label)
        time_layout.addStretch()
        stats_layout.addLayout(time_layout)
        
        # Отправлено
        sent_layout = QHBoxLayout()
        sent_layout.addWidget(QLabel("Отправлено:"))
        self.sent_label = QLabel("0 B")
        self.sent_label.setStyleSheet(f"color: {COLORS['primary']};")
        sent_layout.addWidget(self.sent_label)
        sent_layout.addStretch()
        stats_layout.addLayout(sent_layout)
        
        # Получено
        recv_layout = QHBoxLayout()
        recv_layout.addWidget(QLabel("Получено:"))
        self.recv_label = QLabel("0 B")
        self.recv_label.setStyleSheet(f"color: {COLORS['primary']};")
        recv_layout.addWidget(self.recv_label)
        recv_layout.addStretch()
        stats_layout.addLayout(recv_layout)
        
        # Пакеты
        packets_layout = QHBoxLayout()
        packets_layout.addWidget(QLabel("Пакеты отправлены/получены:"))
        self.packets_label = QLabel("0 / 0")
        self.packets_label.setStyleSheet(f"color: {COLORS['primary']};")
        packets_layout.addWidget(self.packets_label)
        packets_layout.addStretch()
        stats_layout.addLayout(packets_layout)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Создать вкладку настроек"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Кнопка открытия расширенных настроек
        advanced_button = QPushButton("Расширенные настройки")
        advanced_button.clicked.connect(self._open_settings_dialog)
        layout.addWidget(advanced_button)
        
        # О приложении
        about_group = QGroupBox("О приложении")
        about_layout = QVBoxLayout()
        about_layout.addWidget(QLabel("NexusVPN v1.0.0"))
        about_layout.addWidget(QLabel("Безопасный VPN клиент"))
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _on_connect_clicked(self):
        """Обработчик кнопки подключения"""
        try:
            host = self.host_input.text().strip()
            port = self.port_input.value()
            password = self.password_input.text()
            
            if not host:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите адрес сервера")
                return
            
            if not password:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите пароль")
                return
            
            self.statusBar().showMessage('Подключение...')
            self.connect_button.setEnabled(False)
            
            # Создать VPN клиент
            obfuscation_mode = self.obfuscation_combo.currentText().lower()
            self.vpn_client = VPNClient(
                server_host=host,
                server_port=port,
                password=password,
                obfuscation_mode=obfuscation_mode if obfuscation_mode != 'none' else 'https',
                on_connect_callback=self._on_vpn_connected,
                on_disconnect_callback=self._on_vpn_disconnected
            )
            
            # Запустить подключение в отдельном потоке
            self.connection_thread = ConnectionThread(self.vpn_client)
            self.connection_thread.action = 'connect'
            self.connection_thread.connected.connect(self._on_vpn_connected)
            self.connection_thread.error.connect(self._on_vpn_error)
            self.connection_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при подключении: {str(e)}")
            self.connect_button.setEnabled(True)
    
    def _on_disconnect_clicked(self):
        """Обработчик кнопки отключения"""
        try:
            self.statusBar().showMessage('Отключение...')
            self.disconnect_button.setEnabled(False)
            
            if self.vpn_client:
                self.connection_thread = ConnectionThread(self.vpn_client)
                self.connection_thread.action = 'disconnect'
                self.connection_thread.disconnected.connect(self._on_vpn_disconnected)
                self.connection_thread.error.connect(self._on_vpn_error)
                self.connection_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при отключении: {str(e)}")
            self.disconnect_button.setEnabled(True)
    
    def _on_vpn_connected(self):
        """Callback при успешном подключении"""
        self.statusBar().showMessage('Подключено к VPN')
        self.status_label.setText('Подключено ✓')
        self.status_label.setStyleSheet(f"color: {COLORS['success']};")
        
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        
        self.host_input.setReadOnly(True)
        self.port_input.setReadOnly(True)
        self.password_input.setReadOnly(True)
        
        logger.info("Успешно подключено к VPN")
    
    def _on_vpn_disconnected(self):
        """Callback при отключении"""
        self.statusBar().showMessage('Отключено от VPN')
        self.status_label.setText('Отключено')
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        
        self.host_input.setReadOnly(False)
        self.port_input.setReadOnly(False)
        self.password_input.setReadOnly(False)
        
        logger.info("Отключено от VPN")
    
    def _on_vpn_error(self, error_msg: str):
        """Callback при ошибке VPN"""
        QMessageBox.critical(self, "Ошибка VPN", error_msg)
        self.statusBar().showMessage('Ошибка подключения')
        
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        
        logger.error(f"VPN ошибка: {error_msg}")
    
    def _toggle_password_visibility(self):
        """Показать/скрыть пароль"""
        if self.show_password_check.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def _open_settings_dialog(self):
        """Открыть диалог настроек"""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def _update_stats(self):
        """Обновить статистику"""
        if self.vpn_client and self.vpn_client.is_connected():
            stats = self.vpn_client.get_stats()
            
            # Время подключения
            if stats['connection_time']:
                elapsed = time.time() - stats['connection_time']
                minutes = int(elapsed) // 60
                seconds = int(elapsed) % 60
                self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
            
            # Объем данных
            sent_mb = stats['bytes_sent'] / (1024 * 1024)
            recv_mb = stats['bytes_received'] / (1024 * 1024)
            
            if sent_mb > 0:
                self.sent_label.setText(f"{sent_mb:.2f} MB")
            else:
                self.sent_label.setText(f"{stats['bytes_sent']} B")
            
            if recv_mb > 0:
                self.recv_label.setText(f"{recv_mb:.2f} MB")
            else:
                self.recv_label.setText(f"{stats['bytes_received']} B")
            
            # Пакеты
            self.packets_label.setText(
                f"{stats['packets_sent']} / {stats['packets_received']}"
            )
    
    def closeEvent(self, event):
        """Событие закрытия окна"""
        if self.vpn_client and self.vpn_client.is_connected():
            reply = QMessageBox.question(
                self,
                'Выход',
                'VPN все еще подключен. Отключиться перед выходом?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.vpn_client.disconnect()
        
        event.accept()


import time
