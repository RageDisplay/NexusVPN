"""
Стили для GUI приложения
"""

STYLE_SHEET = """
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}

QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}

QLabel {
    color: #ffffff;
    font-size: 12px;
}

QLineEdit {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
}

QLineEdit:focus {
    border: 2px solid #0d7377;
    background-color: #333333;
}

QPushButton {
    background-color: #0d7377;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #14919b;
}

QPushButton:pressed {
    background-color: #0a5d62;
}

QPushButton:disabled {
    background-color: #404040;
    color: #808080;
}

QComboBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 8px;
    font-size: 12px;
}

QComboBox:focus {
    border: 2px solid #0d7377;
}

QComboBox::drop-down {
    border: none;
}

QComboBox::down-arrow {
    image: url("noimg");
    width: 10px;
}

QListView {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #404040;
}

QListView::item:selected {
    background-color: #0d7377;
}

QScrollBar:vertical {
    background-color: #2d2d2d;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #404040;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background-color: #505050;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QCheckBox {
    color: #ffffff;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QCheckBox::indicator:unchecked {
    background-color: #2d2d2d;
    border: 1px solid #404040;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #0d7377;
    border: 1px solid #0d7377;
    border-radius: 3px;
}

QSpinBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 8px;
}

QGroupBox {
    color: #ffffff;
    border: 1px solid #404040;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QTabWidget::pane {
    border: 1px solid #404040;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #ffffff;
    padding: 8px 20px;
    border: none;
}

QTabBar::tab:selected {
    background-color: #0d7377;
}

QDialog {
    background-color: #1e1e1e;
    color: #ffffff;
}

QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #ffffff;
}

QProgressBar {
    background-color: #2d2d2d;
    border: 1px solid #404040;
    border-radius: 4px;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #0d7377;
    border-radius: 3px;
}

QStatusBar {
    background-color: #2d2d2d;
    color: #ffffff;
    border-top: 1px solid #404040;
}
"""

# Цветовая схема
COLORS = {
    'background': '#1e1e1e',
    'surface': '#2d2d2d',
    'primary': '#0d7377',
    'primary_hover': '#14919b',
    'primary_active': '#0a5d62',
    'text': '#ffffff',
    'text_secondary': '#b0b0b0',
    'border': '#404040',
    'danger': '#d32f2f',
    'success': '#388e3c',
    'warning': '#f57c00',
}

# Размеры окна
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 600

# Размеры компонентов
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 140
INPUT_HEIGHT = 40

# Шрифты
FONT_FAMILY = "Segoe UI"
FONT_SIZE_SMALL = 10
FONT_SIZE_NORMAL = 12
FONT_SIZE_LARGE = 14
FONT_SIZE_TITLE = 16
