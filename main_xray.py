# Bobcat Proxy 2.6 pre2 - Клиент для Xray-core
# С автоматическим fallback эмодзи для Linux

from datetime import datetime, timedelta
import re
import os
import json
import subprocess
import base64
import urllib.request
import urllib.parse
import socket
import ssl
import time
import uuid
import sys
import platform
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLineEdit,
                             QComboBox, QLabel, QDialog, QMessageBox, QSplitter,
                             QGroupBox, QCheckBox, QListWidget, QListWidgetItem,
                             QTabWidget, QFormLayout, QSpinBox, QDateTimeEdit,
                             QMenu, QRadioButton, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QAction, QFont, QPalette, QIcon

# ==================================================================================================
# ПОДДЕРЖКА ЭМОДЗИ И FALLBACK (ДЛЯ LINUX)
# ==================================================================================================
def check_emoji_support() -> bool:
    """Проверяет, поддерживает ли система цветные эмодзи."""
    system = platform.system()
    if system in ('Windows', 'Darwin'):
        return True  # В Windows и macOS эмодзи поддерживаются нативно
    
    if system == 'Linux':
        try:
            # Проверяем наличие цветных шрифтов через fontconfig
            result = subprocess.run(
                ['fc-list', ':color'],
                capture_output=True, text=True, timeout=2
            )
            # Если в выводе есть 'emoji' или 'noto', значит цветные эмодзи есть
            if 'emoji' in result.stdout.lower() or 'noto' in result.stdout.lower():
                return True
        except Exception:
            pass
    return False

EMOJI_SUPPORT = check_emoji_support()

# Словарь замены цветных эмодзи на универсальные монохромные Unicode-символы
UNICODE_FALLBACKS = {
    "⚙️": "⚙", "⚙": "⚙", "📡": "≋", "🔄": "↻", "✅": "✔", "❌": "✖",
    "🔴": "●", "🟢": "●", "📥": "↓", "📦": "▣", "🔍": "⌕", "🚀": "➤",
    "🔌": "⚡", "🔗": "⛓", "📋": "▤", "📄": "▤", "🔑": "⚷", "📝": "✎",
    "🌐": "⊕", "🧪": "⚗", "💾": "▣", "🗑️": "✕", "🗑": "✕", "➕": "＋",
    "📊": "≡", "🕐": "⏱", "⏸️": "⏸", "⏸": "⏸", "⏳": "⏳", "⏬": "⤵",
    "⏹️": "⏹", "⏹": "⏹", "🔚": "⏏", "ℹ️": "ⓘ", "ℹ": "ⓘ", "✋": "✋",
    "🏷️": "⚲", "🏷": "⚲", "📍": "➤", "⚠️": "⚠", "⚠": "⚠", "📁": "▤", "🔧": "⚒",
    "🔐": "🔒", "🔒": "🔒", "🌍": "⊕"
}

def fix_emojis(text: str) -> str:
    """Заменяет эмодзи на Unicode-символы, если система их не поддерживает."""
    if not EMOJI_SUPPORT:
        for emoji, fallback in UNICODE_FALLBACKS.items():
            text = text.replace(emoji, fallback)
    return text

def apply_emoji_fallbacks():
    """Патчит классы Qt для автоматической замены эмодзи во всем интерфейсе."""
    if EMOJI_SUPPORT:
        return

    print("ℹ️ Цветные эмодзи не поддерживаются системой. Используются Unicode-символы.")

    # Патчим QLabel
    _orig_label_setText = QLabel.setText
    def _label_setText(self, text):
        _orig_label_setText(self, fix_emojis(str(text)))
    QLabel.setText = _label_setText

    # Патчим QPushButton
    _orig_btn_setText = QPushButton.setText
    def _btn_setText(self, text):
        _orig_btn_setText(self, fix_emojis(str(text)))
    QPushButton.setText = _btn_setText

    # Патчим QCheckBox
    _orig_chk_setText = QCheckBox.setText
    def _chk_setText(self, text):
        _orig_chk_setText(self, fix_emojis(str(text)))
    QCheckBox.setText = _chk_setText

    # Патчим QGroupBox
    _orig_grp_setTitle = QGroupBox.setTitle
    def _grp_setTitle(self, title):
        _orig_grp_setTitle(self, fix_emojis(str(title)))
    QGroupBox.setTitle = _grp_setTitle

    # Патчим QMainWindow
    _orig_win_setTitle = QMainWindow.setWindowTitle
    def _win_setTitle(self, title):
        _orig_win_setTitle(self, fix_emojis(str(title)))
    QMainWindow.setWindowTitle = _win_setTitle

    # Патчим QListWidgetItem
    _orig_item_setText = QListWidgetItem.setText
    def _item_setText(self, text):
        _orig_item_setText(self, fix_emojis(str(text)))
    QListWidgetItem.setText = _item_setText

    # Патчим QComboBox (addItem)
    _orig_combo_addItem = QComboBox.addItem
    def _combo_addItem(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (fix_emojis(args[0]),) + args[1:]
        _orig_combo_addItem(self, *args, **kwargs)
    QComboBox.addItem = _combo_addItem

    # Патчим QMessageBox (диалоговые окна)
    for msg_type in ['information', 'warning', 'question', 'critical']:
        orig_method = getattr(QMessageBox, msg_type)
        def make_patched(method):
            def patched(*args, **kwargs):
                args = list(args)
                if len(args) >= 2:
                    args[1] = fix_emojis(str(args[1]))  # Заголовок
                if len(args) >= 3:
                    args[2] = fix_emojis(str(args[2]))  # Текст
                return method(*args, **kwargs)
            return patched
        setattr(QMessageBox, msg_type, make_patched(orig_method))

# ==================================================================================================
# КОНСТАНТЫ И ПУТИ
# ==================================================================================================
def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_app_data_dir() -> str:
    system = platform.system()
    if system == 'Windows':
        appdata = os.getenv('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
        data_dir = os.path.join(appdata, 'BobcatProxy')
    else:
        xdg_config = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        data_dir = os.path.join(xdg_config, 'BobcatProxy')
        os.makedirs(data_dir, exist_ok=True)
    return data_dir

DATA_DIR = get_app_data_dir()
BASE_DIR = get_base_dir()

# Пути к файлам
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
KEYS_DB_PATH = os.path.join(DATA_DIR, "keys.json")
SUBS_DB_PATH = os.path.join(DATA_DIR, "sub.json")
LOGS_DIR = os.path.join(DATA_DIR, "xraylogs")
GEOIP_PATH = os.path.join(DATA_DIR, "geoip.dat")
GEOSITE_PATH = os.path.join(DATA_DIR, "geosite.dat")
GEOSITE_RU_ONLY_PATH = os.path.join(DATA_DIR, "geosite-ru-only.dat")
RU_BLOCKED_PATH = os.path.join(DATA_DIR, "ru-blocked-all.txt")
VERSION_FILE = os.path.join(DATA_DIR, "xray_version.txt")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
USERAGENT_FILE = os.path.join(DATA_DIR, "useragent.json")

# Настройки прокси
LOCAL_PROXY_HOST = "127.0.0.1"
LOCAL_PROXY_PORT = 25443
DEFAULT_UPDATE_INTERVAL = 3600
MIN_UPDATE_INTERVAL = 300

# Пресеты User-Agent
USERAGENT_PRESETS = {
    "chrome_windows": {
        "name": "Chrome 148 (Windows)",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    },
    "firefox_windows": {
        "name": "Firefox 148 (Windows)",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
    },
    "edge_windows": {
        "name": "Edge 148 (Windows)",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
    },
    "chrome_linux": {
        "name": "Chrome (Linux)",
        "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    },
    "firefox_linux": {
        "name": "Firefox (Linux)",
        "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0"
    },
    "safari_mac": {
        "name": "Safari (macOS)",
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
    },
    "chrome_android": {
        "name": "Chrome (Android)",
        "ua": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Mobile Safari/537.36"
    },
    "safari_ios": {
        "name": "Safari (iOS)",
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    },
    "custom": {
        "name": "Свой User-Agent",
        "ua": ""
    }
}

DEFAULT_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

# URL для загрузки файлов
GEOIP_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat"
GEOSITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/download/202604112225/geosite.dat"
GEOSITE_RU_ONLY_URL = "https://github.com/runetfreedom/russia-blocked-geosite/releases/download/202604112126/geosite-ru-only.dat"
RU_BLOCKED_URL = "https://github.com/runetfreedom/russia-blocked-geosite/releases/download/202604112126/ru-blocked-all.txt"

# Базовый URL для Xray-core
XRAY_RELEASES_URL = "https://github.com/XTLS/Xray-core/releases"
XRAY_API_URL = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"

# Настройки обновлений Xray-core
UPDATE_CHANNELS = {
    "stable": {
        "name": "Стабильная версия",
        "desc": "Рекомендуется для повседневного использования",
        "api_url": "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
    },
    "prerelease": {
        "name": "Пре-релиз (нестабильная)",
        "desc": "Последняя версия, включая бета и RC. Может содержать ошибки!",
        "api_url": "https://api.github.com/repos/XTLS/Xray-core/releases"
    }
}
DEFAULT_UPDATE_CHANNEL = "stable"

# Режимы туннелирования
TUNNEL_MODES = {
    "ru_direct": {
        "name": "Российские напрямую",
        "desc": "Домены из geosite-ru-only.dat идут напрямую",
        "file": GEOSITE_RU_ONLY_PATH,
        "url": GEOSITE_RU_ONLY_URL
    },
    "blocked_tunnel": {
        "name": "Всё напрямую кроме заблокированных",
        "desc": "Домены из ru-blocked-all.txt идут в туннель",
        "file": RU_BLOCKED_PATH,
        "url": RU_BLOCKED_URL
    },
    "all_vpn": {
        "name": "Всё в VPN",
        "desc": "Весь трафик идёт через VPN (все домены и IP через прокси)",
        "file": None,
        "url": None
    }
}

# Форматы отображения ключей
KEY_DISPLAY_MODES = {
    "legacy": "Старый формат (как сейчас)",
    "detailed": "Протокол | домен/IP | транспорт",
    "hashtag": "Хештег / название сервера"
}
DEFAULT_KEY_DISPLAY_MODE = "legacy"

# Режимы логирования
LOG_MODES = {
    "normal": "Обычный режим (warning)",
    "debug": "Режим отладки (debug)"
}
DEFAULT_LOG_MODE = "normal"

# ==================================================================================================
# УПРАВЛЕНИЕ USER-AGENT
# ==================================================================================================
def load_useragent_settings() -> dict:
    """Загружает настройки User-Agent из файла"""
    default_settings = {
        "preset": "chrome_windows",
        "custom_ua": "",
        "enabled": True
    }
    if os.path.exists(USERAGENT_FILE):
        try:
            with open(USERAGENT_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                default_settings.update(saved)
        except Exception:
            pass
    return default_settings

def save_useragent_settings(settings: dict):
    """Сохраняет настройки User-Agent в файл"""
    with open(USERAGENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_current_useragent() -> str:
    """Возвращает текущий User-Agent на основе сохранённых настроек"""
    settings = load_useragent_settings()
    if not settings.get("enabled", True):
        return DEFAULT_USERAGENT
    preset_key = settings.get("preset", "chrome_windows")
    if preset_key == "custom":
        return settings.get("custom_ua", DEFAULT_USERAGENT)
    preset = USERAGENT_PRESETS.get(preset_key, USERAGENT_PRESETS["chrome_windows"])
    return preset["ua"]

# ==================================================================================================
# ОПРЕДЕЛЕНИЕ ТЕМЫ СИСТЕМЫ
# ==================================================================================================
def get_linux_theme() -> str:
    try:
        result = subprocess.run(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
            capture_output=True, text=True, timeout=2, check=False
        )
        if result.returncode == 0:
            output = result.stdout.strip().strip("'")
            if 'prefer-dark' in output or 'dark' in output:
                return 'dark'
            elif 'prefer-light' in output or 'light' in output:
                return 'light'
    except Exception:
        pass
    try:
        app = QApplication.instance()
        if app and app.palette().color(QPalette.ColorRole.Window).lightness() < 128:
            return 'dark'
    except Exception:
        pass
    return 'light'

def get_windows_theme() -> str:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
    except Exception:
        return "dark"

def get_system_theme() -> str:
    system = platform.system()
    if system == 'Windows':
        return get_windows_theme()
    else:
        return get_linux_theme()

# ==================================================================================================
# УТИЛИТЫ ОБНОВЛЕНИЯ XRAY-CORE
# ==================================================================================================
def get_current_xray_version() -> Optional[str]:
    """Получает текущую установленную версию Xray-core."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_current_xray_version(version: str):
    """Сохраняет текущую версию Xray-core."""
    with open(VERSION_FILE, 'w') as f:
        f.write(version)

def get_latest_xray_release(channel: str = "stable") -> Optional[Dict]:
    """Получает информацию о последнем релизе Xray-core через GitHub API."""
    try:
        if channel == "stable":
            api_url = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
            req = urllib.request.Request(api_url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', get_current_useragent())
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        else:
            api_url = "https://api.github.com/repos/XTLS/Xray-core/releases?per_page=5"
            req = urllib.request.Request(api_url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', get_current_useragent())
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                releases = json.loads(response.read().decode('utf-8'))
                if releases and isinstance(releases, list):
                    return releases[0]
                return None
    except Exception as e:
        print(f"⚠️ Ошибка получения релиза через API: {e}")
        return None

def find_asset_for_platform(assets: List[Dict]) -> Optional[Dict]:
    """Находит подходящий ассет для текущей платформы."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == 'windows':
        platform_keywords = ['windows', 'win']
        arch_keywords = ['64', 'x64', 'amd64', 'x86_64']
    elif system == 'linux':
        platform_keywords = ['linux']
        arch_keywords = ['64', 'x64', 'amd64', 'x86_64']
    elif system == 'darwin':
        platform_keywords = ['macos', 'darwin', 'mac']
        arch_keywords = ['64', 'x64', 'amd64', 'x86_64']
    else:
        return None
    for asset in assets:
        name = asset.get('name', '').lower()
        download_url = asset.get('browser_download_url', '')
        if not download_url or not name.endswith('.zip'):
            continue
        platform_match = any(kw in name for kw in platform_keywords)
        arch_match = any(kw in name for kw in arch_keywords)
        is_excluded = any(x in name for x in ['debug', 'symbol', 'pdb', 'sha256', 'asc', 'dgst'])
        if platform_match and arch_match and not is_excluded:
            return asset
    return None

def download_file_with_progress(url: str, destination: str, progress_callback=None, timeout: int = 120) -> bool:
    """Скачивает файл с отслеживанием прогресса."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header('User-Agent', get_current_useragent())
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        percent = int((downloaded / total_size) * 100)
                        progress_callback(percent)
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return False

def install_xray_from_zip(zip_path: str, target_dir: str) -> bool:
    """Распаковывает архив Xray-core и устанавливает бинарник."""
    try:
        extract_dir = os.path.join(target_dir, "xray_extract")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        binary_name = "xray.exe" if platform.system() == 'Windows' else "xray"
        found = False
        for root, dirs, files in os.walk(extract_dir):
            if binary_name in files:
                source_path = os.path.join(root, binary_name)
                target_path = os.path.join(target_dir, binary_name)
                if os.path.exists(target_path):
                    backup = target_path + '.backup'
                    shutil.move(target_path, backup)
                shutil.copy2(source_path, target_path)
                if platform.system() != 'Windows':
                    os.chmod(target_path, 0o755)
                if os.path.exists(target_path + '.backup'):
                    os.remove(target_path + '.backup')
                found = True
                break
        shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return found
    except Exception as e:
        print(f"❌ Ошибка распаковки: {e}")
        return False

# ==================================================================================================
# КЛАССЫ ДЛЯ ОБНОВЛЕНИЯ
# ==================================================================================================
class UpdateChecker(QThread):
    """Поток для проверки обновлений Xray-core."""
    update_available = pyqtSignal(str, str, str, str, str)
    no_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, channel: str = "stable"):
        super().__init__()
        self.channel = channel

    def run(self):
        try:
            release_data = get_latest_xray_release(self.channel)
            if not release_data:
                self.error.emit("Не удалось получить информацию о релизе")
                return
            tag_name = release_data.get('tag_name', '')
            latest_version = tag_name.lstrip('v')
            if not latest_version:
                self.error.emit("Не удалось определить версию релиза")
                return
            is_prerelease = release_data.get('prerelease', False)
            channel_name = "пре-релиз" if is_prerelease else "стабильная"
            assets = release_data.get('assets', [])
            asset = find_asset_for_platform(assets)
            if not asset:
                self.error.emit(f"Не найден подходящий билд для {platform.system()} {platform.machine()}")
                return
            download_url = asset.get('browser_download_url', '')
            file_size = asset.get('size', 0)
            size_mb = file_size / (1024 * 1024) if file_size else 0
            current_version = get_current_xray_version()
            if current_version == latest_version:
                self.no_update.emit(latest_version)
            else:
                self.update_available.emit(
                    latest_version,
                    tag_name,
                    download_url,
                    f"{size_mb:.1f} МБ",
                    channel_name
                )
        except Exception as e:
            self.error.emit(f"Ошибка проверки обновлений: {str(e)}")

class DownloadWorker(QThread):
    """Поток для скачивания и установки Xray-core."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, download_url: str, version: str):
        super().__init__()
        self.download_url = download_url
        self.version = version

    def run(self):
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            filename = self.download_url.split('/')[-1]
            if not filename.endswith('.zip'):
                filename = f"Xray-{platform.system().lower()}-64.zip"
            download_path = os.path.join(DOWNLOAD_DIR, filename)
            self.status.emit(fix_emojis(f"Скачивание Xray-core v{self.version}..."))
            success = download_file_with_progress(
                self.download_url,
                download_path,
                progress_callback=self.progress.emit
            )
            if not success:
                self.finished.emit(False, fix_emojis("❌ Ошибка при скачивании файла"))
                return
            self.status.emit(fix_emojis("Установка Xray-core..."))
            if install_xray_from_zip(download_path, DATA_DIR):
                save_current_xray_version(self.version)
                self.finished.emit(True, fix_emojis(f"✅ Xray-core v{self.version} успешно установлен"))
            else:
                self.finished.emit(False, fix_emojis("❌ Не удалось установить Xray-core из архива"))
        except Exception as e:
            self.finished.emit(False, fix_emojis(f"❌ Ошибка при установке: {str(e)}"))

# ==================================================================================================
# ДИАЛОГ НАСТРОЕК ОБНОВЛЕНИЙ
# ==================================================================================================
class UpdateSettingsDialog(QDialog):
    """Диалог настроек обновлений Xray-core."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(fix_emojis("⚙️ Настройки обновлений Xray-core"))
        self.setMinimumSize(500, 350)
        self.setFont(QFont("Arial"))
        self.update_checker = None
        self._init_ui()
        self._load_current_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(fix_emojis("Настройки канала обновлений Xray-core"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 10px;")
        layout.addWidget(title)
        channel_group = QGroupBox(fix_emojis("Канал обновлений"))
        channel_layout = QVBoxLayout(channel_group)
        self.channel_radio = {}
        for channel_key, channel_info in UPDATE_CHANNELS.items():
            radio = QRadioButton(fix_emojis(f"{channel_info['name']}"))
            radio.setToolTip(fix_emojis(channel_info['desc']))
            radio.clicked.connect(lambda checked, k=channel_key: self._on_channel_changed(k))
            self.channel_radio[channel_key] = radio
            radio_layout = QVBoxLayout()
            radio_layout.addWidget(radio)
            desc_label = QLabel(fix_emojis(f"   {channel_info['desc']}"))
            desc_label.setStyleSheet("color: #888; font-size: 9pt;")
            radio_layout.addWidget(desc_label)
            channel_layout.addLayout(radio_layout)
        layout.addWidget(channel_group)
        info_group = QGroupBox(fix_emojis("Информация"))
        info_layout = QVBoxLayout(info_group)
        current_ver = get_current_xray_version()
        if current_ver:
            ver_text = fix_emojis(f"Установленная версия: v{current_ver}")
        else:
            ver_text = fix_emojis("Xray-core не установлен")
        self.version_info = QLabel(ver_text)
        self.version_info.setStyleSheet("font-size: 10pt;")
        info_layout.addWidget(self.version_info)
        self.channel_info = QLabel("")
        self.channel_info.setStyleSheet("color: #666; font-size: 9pt;")
        info_layout.addWidget(self.channel_info)
        layout.addWidget(info_group)
        self.warning_label = QLabel(fix_emojis(
            "⚠️ Внимание! Пре-релизные версии могут содержать ошибки\n"
            "и нестабильности. Используйте только для тестирования!"
        ))
        self.warning_label.setStyleSheet(
            "color: #ff6b6b; font-size: 9pt; padding: 10px; "
            "background-color: #fff3f3; border-radius: 5px;"
        )
        self.warning_label.setVisible(False)
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)
        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_check = QPushButton(fix_emojis("🔄 Проверить сейчас"))
        self.btn_check.clicked.connect(self._check_now)
        self.btn_save = QPushButton(fix_emojis("💾 Сохранить"))
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_check)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        settings = load_json_file(os.path.join(DATA_DIR, "update_settings.json"), {})
        current_channel = settings.get("channel", DEFAULT_UPDATE_CHANNEL)
        if current_channel in self.channel_radio:
            self.channel_radio[current_channel].setChecked(True)
            self._on_channel_changed(current_channel)

    def _on_channel_changed(self, channel_key: str):
        channel_info = UPDATE_CHANNELS.get(channel_key, {})
        self.channel_info.setText(fix_emojis(f"Канал: {channel_info.get('name', 'Неизвестно')}"))
        self.warning_label.setVisible(channel_key == "prerelease")
        if channel_key == "prerelease":
            self.channel_info.setStyleSheet("color: #ff6b6b; font-size: 9pt; font-weight: bold;")
        else:
            self.channel_info.setStyleSheet("color: #51cf66; font-size: 9pt;")

    def _check_now(self):
        selected_channel = next(
            (k for k, r in self.channel_radio.items() if r.isChecked()),
            DEFAULT_UPDATE_CHANNEL
        )
        self.btn_check.setEnabled(False)
        self.btn_check.setText(fix_emojis("⏳ Проверка..."))
        QApplication.processEvents()
        self.update_checker = UpdateChecker(selected_channel)
        self.update_checker.update_available.connect(self._on_update_found)
        self.update_checker.no_update.connect(self._on_no_update)
        self.update_checker.error.connect(self._on_check_error)
        self.update_checker.finished.connect(self._on_check_finished)
        self.update_checker.start()

    def _on_update_found(self, version: str, tag: str, url: str, size: str, channel: str):
        current = get_current_xray_version() or "не установлена"
        msg = fix_emojis(
            f"Найдена новая версия ({channel}):\n"
            f"Текущая: v{current}\n"
            f"Новая: v{version}\n"
            f"Размер: {size}\n\n"
            f"Скачать и установить?"
        )
        reply = QMessageBox.question(
            self, fix_emojis("Доступно обновление"),
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.parent_window and hasattr(self.parent_window, 'download_update'):
                self.parent_window.download_update(url, version)
                self.accept()

    def _on_no_update(self, version: str):
        QMessageBox.information(
            self,
            fix_emojis("Обновления Xray-core"),
            fix_emojis(f"Установлена последняя версия: v{version}")
        )

    def _on_check_error(self, error: str):
        QMessageBox.warning(self, fix_emojis("Ошибка проверки"), fix_emojis(error))

    def _on_check_finished(self):
        self.btn_check.setEnabled(True)
        self.btn_check.setText(fix_emojis("🔄 Проверить сейчас"))

    def _save_settings(self):
        selected_channel = next(
            (k for k, r in self.channel_radio.items() if r.isChecked()),
            DEFAULT_UPDATE_CHANNEL
        )
        settings = {
            "channel": selected_channel,
            "channel_name": UPDATE_CHANNELS[selected_channel]["name"],
            "updated": datetime.now().isoformat()
        }
        save_json_file(os.path.join(DATA_DIR, "update_settings.json"), settings)
        channel_name = UPDATE_CHANNELS[selected_channel]["name"]
        QMessageBox.information(
            self,
            fix_emojis("Настройки сохранены"),
            fix_emojis(f"Выбран канал обновлений: {channel_name}")
        )
        self.accept()

# ==================================================================================================
# ДИАЛОГ НАСТРОЕК USER-AGENT
# ==================================================================================================
class UserAgentDialog(QDialog):
    """Диалог настройки User-Agent"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(fix_emojis("🌐 Настройка User-Agent"))
        self.setMinimumSize(600, 450)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(fix_emojis("Настройка User-Agent для HTTP-запросов"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 10px;")
        layout.addWidget(title)
        desc = QLabel(fix_emojis("User-Agent используется при загрузке подписок и проверке обновлений.\n"
                                 "Выберите пресет или введите свой."))
        desc.setStyleSheet("color: #888; font-size: 9pt; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        self.enabled_check = QCheckBox(fix_emojis("Использовать кастомный User-Agent"))
        self.enabled_check.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_check)
        preset_group = QGroupBox(fix_emojis("Выбор пресета User-Agent"))
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        for key, preset in USERAGENT_PRESETS.items():
            self.preset_combo.addItem(fix_emojis(preset["name"]), key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet(
            "color: #666; font-size: 8pt; padding: 8px; "
            "background-color: #f5f5f5; border-radius: 5px;"
        )
        self.preview_label.setWordWrap(True)
        self.preview_label.setMinimumHeight(60)
        preset_layout.addWidget(self.preview_label)
        layout.addWidget(preset_group)
        custom_group = QGroupBox(fix_emojis("Свой User-Agent"))
        custom_layout = QVBoxLayout(custom_group)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Введите свой User-Agent...")
        self.custom_input.textChanged.connect(self._on_custom_changed)
        custom_layout.addWidget(self.custom_input)
        self.custom_info = QLabel(fix_emojis("Редактируйте поле выше для ввода своего User-Agent"))
        self.custom_info.setStyleSheet("color: #888; font-size: 8pt;")
        custom_layout.addWidget(self.custom_info)
        layout.addWidget(custom_group)
        info_group = QGroupBox(fix_emojis("Текущий User-Agent"))
        info_layout = QVBoxLayout(info_group)
        self.current_ua_label = QLabel("")
        self.current_ua_label.setStyleSheet(
            "font-size: 9pt; padding: 8px; background-color: #f0f0f0; "
            "border-radius: 5px; border: 1px solid #ddd;"
        )
        self.current_ua_label.setWordWrap(True)
        info_layout.addWidget(self.current_ua_label)
        layout.addWidget(info_group)
        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton(fix_emojis("🧪 Тест User-Agent"))
        self.btn_test.clicked.connect(self._test_useragent)
        self.btn_test.setToolTip(fix_emojis("Проверить текущий User-Agent на тестовом сервере"))
        self.btn_save = QPushButton(fix_emojis("💾 Сохранить"))
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_test)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        settings = load_useragent_settings()
        self.enabled_check.setChecked(settings.get("enabled", True))
        preset_key = settings.get("preset", "chrome_windows")
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == preset_key:
                self.preset_combo.setCurrentIndex(i)
                break
        self.custom_input.setText(settings.get("custom_ua", ""))
        self._update_preview()
        self._update_current_ua()

    def _on_enabled_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.preset_combo.setEnabled(enabled)
        self.custom_input.setEnabled(enabled and self.preset_combo.currentData() == "custom")
        self._update_current_ua()

    def _on_preset_changed(self):
        preset_key = self.preset_combo.currentData()
        self.custom_input.setEnabled(preset_key == "custom" and self.enabled_check.isChecked())
        self._update_preview()
        self._update_current_ua()

    def _on_custom_changed(self):
        self._update_preview()
        self._update_current_ua()

    def _update_preview(self):
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom":
            ua = self.custom_input.text() or "(пусто)"
        else:
            preset = USERAGENT_PRESETS.get(preset_key, {})
            ua = preset.get("ua", "(не задан)")
        self.preview_label.setText(fix_emojis(f"📋 Предпросмотр:\n{ua}"))

    def _update_current_ua(self):
        if not self.enabled_check.isChecked():
            self.current_ua_label.setText(fix_emojis(f"🔌 Кастомный User-Agent отключен\n{DEFAULT_USERAGENT}"))
            return
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom":
            ua = self.custom_input.text().strip()
            if not ua:
                self.current_ua_label.setText(fix_emojis("⚠️ Свой User-Agent не задан!\nБудет использован стандартный."))
                return
            self.current_ua_label.setText(fix_emojis(f"✏️ Свой User-Agent:\n{ua}"))
        else:
            preset = USERAGENT_PRESETS.get(preset_key, {})
            ua = preset.get("ua", "")
            name = preset.get("name", "")
            self.current_ua_label.setText(fix_emojis(f"✅ {name}:\n{ua}"))

    def _test_useragent(self):
        ua = get_current_useragent() if self.enabled_check.isChecked() else DEFAULT_USERAGENT
        if self.enabled_check.isChecked():
            preset_key = self.preset_combo.currentData()
            if preset_key == "custom":
                ua = self.custom_input.text().strip() or DEFAULT_USERAGENT
        self.btn_test.setEnabled(False)
        self.btn_test.setText(fix_emojis("⏳ Тестирование..."))
        QApplication.processEvents()
        try:
            req = urllib.request.Request("https://httpbin.org/user-agent")
            req.add_header('User-Agent', ua)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                returned_ua = data.get('user-agent', 'Не удалось определить')
                QMessageBox.information(
                    self,
                    fix_emojis("Результат теста"),
                    fix_emojis(f"Отправленный User-Agent:\n{ua}\n\n"
                               f"Полученный сервером User-Agent:\n{returned_ua}\n\n"
                               f"{'✅ User-Agent совпадает!' if ua == returned_ua else '⚠️ User-Agent отличается!'}")
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                fix_emojis("Ошибка теста"),
                fix_emojis(f"Не удалось проверить User-Agent:\n{str(e)}")
            )
        finally:
            self.btn_test.setEnabled(True)
            self.btn_test.setText(fix_emojis("🧪 Тест User-Agent"))

    def _save_settings(self):
        preset_key = self.preset_combo.currentData()
        settings = {
            "preset": preset_key,
            "custom_ua": self.custom_input.text().strip(),
            "enabled": self.enabled_check.isChecked(),
            "updated": datetime.now().isoformat()
        }
        save_useragent_settings(settings)
        if settings["enabled"]:
            if preset_key == "custom":
                ua = settings["custom_ua"] or DEFAULT_USERAGENT
                msg = fix_emojis(f"Свой User-Agent сохранён:\n{ua}")
            else:
                preset = USERAGENT_PRESETS.get(preset_key, {})
                msg = fix_emojis(f"User-Agent сохранён: {preset.get('name', 'Неизвестно')}")
        else:
            msg = fix_emojis("Кастомный User-Agent отключен.\nБудет использован стандартный.")
        QMessageBox.information(self, fix_emojis("Настройки сохранены"), msg)
        self.accept()

# ==================================================================================================
# НАСТРОЙКА SSL ДЛЯ WINDOWS
# ==================================================================================================
def create_ssl_context():
    """Создаёт SSL контекст с отключенной проверкой сертификатов для решения проблем на Windows"""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    except Exception:
        return None

def create_opener_with_ssl_fix():
    """Создаёт URL opener с исправлением SSL проблем на Windows"""
    context = create_ssl_context()
    if context:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    else:
        opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', get_current_useragent())]
    return opener

URL_OPENER = create_opener_with_ssl_fix()

# ==================================================================================================
# ЗАГРУЗКА ФАЙЛОВ
# ==================================================================================================
def download_file(url: str, destination: str, timeout: int = 120) -> bool:
    """Загрузка файлов geoip/geosite"""
    return download_file_with_progress(url, destination, timeout=timeout)

def ensure_geoip_file(data_dir: str) -> bool:
    geoip_path = os.path.join(data_dir, "geoip.dat")
    if not os.path.exists(geoip_path):
        print(fix_emojis(f"⏬ geoip.dat не найден. Загрузка..."))
        return download_file(GEOIP_URL, geoip_path)
    print(fix_emojis(f"✅ geoip.dat найден: {geoip_path}"))
    return True

def ensure_geosite_file(mode_key: str, data_dir: str) -> bool:
    mode = TUNNEL_MODES.get(mode_key)
    if not mode or mode.get("file") is None:
        return True
    file_path = mode["file"]
    url = mode["url"]
    if not os.path.exists(file_path):
        print(fix_emojis(f"⏬ Файл не найден: {file_path}. Загрузка..."))
        return download_file(url, file_path)
    print(fix_emojis(f"✅ Файл найден: {file_path}"))
    return True

def find_xray_binary() -> Optional[str]:
    """Находит бинарный файл Xray-core."""
    binary_name = "xray.exe" if platform.system() == 'Windows' else "xray"
    candidate = os.path.join(DATA_DIR, binary_name)
    if os.path.exists(candidate):
        return candidate
    candidate = os.path.join(BASE_DIR, binary_name)
    if os.path.exists(candidate):
        return candidate
    sys_path = shutil.which(binary_name)
    if sys_path:
        return sys_path
    return None

XRAY_PATH = find_xray_binary()
XRAY_BINARY = "xray.exe" if platform.system() == 'Windows' else "xray"
XRAY_VERSION = get_current_xray_version() or "не установлен"

if XRAY_PATH:
    print(fix_emojis(f"✅ Xray-core {XRAY_VERSION}: {XRAY_PATH}"))
else:
    print(fix_emojis(f"⚠️ Xray-core не найден. Нажмите 'Проверить обновления' для установки."))

try:
    ensure_geoip_file(DATA_DIR)
except Exception as e:
    print(fix_emojis(f"⚠️ Ошибка при загрузке geoip.dat: {e}"))

# ==================================================================================================
# УТИЛИТЫ
# ==================================================================================================
def load_json_file(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json_file(path: str, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_key(key_string: str) -> str:
    if '#' in key_string and key_string.startswith(('vless://', 'vmess://', 'trojan://', 'ss://')):
        return key_string.split('#')[0].strip()
    return key_string.strip()

def load_geosite_domains(file_path: str, mode_key: str) -> List[str]:
    domains = []
    if not os.path.exists(file_path):
        return domains
    if file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith(('domain:', 'regexp:', 'full:', 'keyword:')):
                        domains.append(line)
                    elif line.startswith('.'):
                        domains.append(f"domain:{line[1:]}")
                    else:
                        domains.append(f"domain:{line}")
    elif file_path.endswith('.dat'):
        if "ru-only" in file_path or "russia-blocked" in file_path:
            return []
        elif "geosite.dat" in file_path and "Loyalsoldier" in file_path:
            return ["geosite:category-ru", "geosite:ru"]
        else:
            return ["geosite:ru"]
    return domains

def parse_key_for_display(key_string: str) -> Dict[str, str]:
    """Парсит ключ и возвращает компоненты для детального отображения"""
    result = {"protocol": "???", "address": "???", "transport": "???", "hashtag": ""}
    try:
        if key_string.startswith('{') and key_string.endswith('}'):
            config = json.loads(key_string)
            outbounds = config.get("outbounds", [])
            for ob in outbounds:
                if ob.get("tag") == "proxy":
                    result["protocol"] = ob.get("protocol", "unknown").upper()
                    settings = ob.get("settings", {})
                    if "vnext" in settings and settings["vnext"]:
                        result["address"] = settings["vnext"][0].get("address", "???")
                    elif "servers" in settings and settings["servers"]:
                        result["address"] = settings["servers"][0].get("address", "???")
                    stream = ob.get("streamSettings", {})
                    result["transport"] = stream.get("network", "tcp").upper()
                    tag = ob.get("tag", "")
                    if tag and tag != "proxy":
                        result["hashtag"] = tag
                    break
            return result
        if key_string.startswith("vless://"):
            result["protocol"] = "VLESS"
            url_part = key_string[8:]
            if '#' in url_part:
                url_part, hashtag = url_part.split('#', 1)
                result["hashtag"] = urllib.parse.unquote(hashtag)
            if '?' in url_part:
                addr_part, query = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query)
            else:
                addr_part, params = url_part, {}
            if '@' in addr_part:
                _, host_port = addr_part.rsplit('@', 1)
                if host_port.startswith('['):
                    end = host_port.index(']')
                    result["address"] = host_port[1:end]
                elif ':' in host_port:
                    result["address"] = host_port.rsplit(':', 1)[0]
            result["transport"] = params.get('type', ['tcp'])[0].upper()
            return result
        if key_string.startswith("vmess://"):
            result["protocol"] = "VMESS"
            b64 = key_string[8:].strip()
            if '#' in b64:
                b64, hashtag = b64.split('#', 1)
                result["hashtag"] = urllib.parse.unquote(hashtag)
            b64 += '=' * (-len(b64) % 4)
            try:
                vmess = json.loads(base64.b64decode(b64).decode('utf-8'))
                result["address"] = vmess.get('add', '???')
                result["transport"] = vmess.get('net', 'tcp').upper()
                if not result["hashtag"]:
                    ps = vmess.get('ps', '')
                    if ps:
                        result["hashtag"] = ps
            except Exception:
                pass
            return result
        if key_string.startswith("trojan://"):
            result["protocol"] = "TROJAN"
            url_part = key_string[9:]
            if '#' in url_part:
                url_part, hashtag = url_part.split('#', 1)
                result["hashtag"] = urllib.parse.unquote(hashtag)
            if '?' in url_part:
                addr_part, query = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query)
            else:
                addr_part, params = url_part, {}
            if '@' in addr_part:
                _, host_port = addr_part.rsplit('@', 1)
                if host_port.startswith('['):
                    end = host_port.index(']')
                    result["address"] = host_port[1:end]
                elif ':' in host_port:
                    result["address"] = host_port.rsplit(':', 1)[0]
            result["transport"] = params.get('type', ['tcp'])[0].upper()
            return result
        if key_string.startswith("ss://"):
            result["protocol"] = "SS"
            url_part = key_string[5:]
            if '#' in url_part:
                url_part, hashtag = url_part.split('#', 1)
                result["hashtag"] = urllib.parse.unquote(hashtag)
            if '?' in url_part:
                addr_part = url_part.split('?')[0]
            else:
                addr_part = url_part
            try:
                padded = addr_part + '=' * (-len(addr_part) % 4)
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                if '@' in decoded:
                    _, hp = decoded.rsplit('@', 1)
                    if ':' in hp:
                        result["address"] = hp.rsplit(':', 1)[0]
            except Exception:
                pass
            result["transport"] = "TCP"
            return result
    except Exception:
        pass
    return result

# ==================================================================================================
# МЕНЕДЖЕР ПОДПИСОК
# ==================================================================================================
class SubscriptionManager:
    def __init__(self, keys_path: str, subs_path: str):
        self.keys_path = keys_path
        self.subs_path = subs_path
        self.keys = self._load_keys()
        self.subscriptions = self._load_subscriptions()

    def _load_keys(self) -> list:
        raw = load_json_file(self.keys_path, [])
        if raw and isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], str):
            converted = []
            for key in raw:
                converted.append({
                    "key": key,
                    "source": "manual",
                    "sub_url": None,
                    "added": datetime.now().isoformat(),
                    "id": str(uuid.uuid4())[:8]
                })
            self._save_keys(converted)
            return converted
        return raw if isinstance(raw, list) else []

    def _load_subscriptions(self) -> list:
        raw = load_json_file(self.subs_path, {"subscriptions": []})
        return raw.get("subscriptions", []) if isinstance(raw, dict) else []

    def _save_keys(self, keys: list = None):
        if keys is not None:
            self.keys = keys
        save_json_file(self.keys_path, self.keys)

    def _save_subscriptions(self, subs: list = None):
        if subs is not None:
            self.subscriptions = subs
        save_json_file(self.subs_path, {"subscriptions": self.subscriptions})

    def add_subscription(self, url: str, interval: int = DEFAULT_UPDATE_INTERVAL) -> dict:
        for sub in self.subscriptions:
            if sub["url"] == url:
                return sub
        new_sub = {
            "id": str(uuid.uuid4()),
            "url": url,
            "name": f"Подписка {len(self.subscriptions) + 1}",
            "update_interval": interval,
            "last_update": None,
            "enabled": True,
            "key_count": 0
        }
        self.subscriptions.append(new_sub)
        self._save_subscriptions()
        return new_sub

    def remove_subscription(self, sub_id: str, remove_keys: bool = True):
        sub = self.get_subscription(sub_id)
        if not sub:
            return False
        if remove_keys:
            self.keys = [k for k in self.keys if k.get("sub_url") != sub["url"]]
            self._save_keys()
        self.subscriptions = [s for s in self.subscriptions if s["id"] != sub_id]
        self._save_subscriptions()
        return True

    def get_subscription(self, sub_id: str) -> Optional[dict]:
        for sub in self.subscriptions:
            if sub["id"] == sub_id:
                return sub
        return None

    def update_subscription(self, sub_id: str, **kwargs):
        sub = self.get_subscription(sub_id)
        if sub:
            sub.update(kwargs)
            self._save_subscriptions()
            return True
        return False

    def add_manual_key(self, key_string: str) -> bool:
        normalized = normalize_key(key_string)
        for k in self.keys:
            if normalize_key(k["key"]) == normalized:
                return False
        self.keys.append({
            "key": key_string,
            "source": "manual",
            "sub_url": None,
            "added": datetime.now().isoformat(),
            "id": str(uuid.uuid4())[:8]
        })
        self._save_keys()
        return True

    def add_keys_from_subscription(self, sub_url: str, key_strings: list) -> int:
        count = 0
        existing_keys = {normalize_key(k["key"]): k for k in self.keys
                         if k.get("sub_url") == sub_url}
        for key_str in key_strings:
            normalized = normalize_key(key_str)
            if normalized in existing_keys:
                existing_keys[normalized]["key"] = key_str
                existing_keys[normalized]["updated"] = datetime.now().isoformat()
            else:
                if any(normalize_key(k["key"]) == normalized for k in self.keys):
                    continue
                self.keys.append({
                    "key": key_str,
                    "source": "subscription",
                    "sub_url": sub_url,
                    "added": datetime.now().isoformat(),
                    "id": str(uuid.uuid4())[:8]
                })
                count += 1
        keys_to_keep = []
        normalized_new_keys = {normalize_key(ks) for ks in key_strings}
        for k in self.keys:
            if k.get("sub_url") == sub_url and normalize_key(k["key"]) not in normalized_new_keys:
                continue
            keys_to_keep.append(k)
        self.keys = keys_to_keep
        for sub in self.subscriptions:
            if sub["url"] == sub_url:
                sub["key_count"] = len([k for k in self.keys if k.get("sub_url") == sub_url])
                sub["last_update"] = datetime.now().isoformat()
                break
        self._save_keys()
        self._save_subscriptions()
        return count

    def get_keys_by_source(self, source: str = None, sub_id: str = None) -> list:
        result = self.keys
        if source == "manual":
            result = [k for k in result if k.get("source") == "manual"]
        elif source == "subscription":
            result = [k for k in result if k.get("source") == "subscription"]
        if sub_id:
            sub = self.get_subscription(sub_id)
            if sub:
                result = [k for k in result if k.get("sub_url") == sub["url"]]
        return result

    def get_subscriptions_due_update(self) -> list:
        due = []
        now = datetime.now()
        for sub in self.subscriptions:
            if not sub.get("enabled", True):
                continue
            last = sub.get("last_update")
            interval = sub.get("update_interval", DEFAULT_UPDATE_INTERVAL)
            if not last:
                due.append(sub)
            else:
                last_dt = datetime.fromisoformat(last)
                if now - last_dt >= timedelta(seconds=interval):
                    due.append(sub)
        return due

# ==================================================================================================
# СИСТЕМНЫЙ ПРОКСИ
# ==================================================================================================
def set_linux_proxy_gnome(enable: bool, host: str = "127.0.0.1", port: int = 25443):
    try:
        mode = "manual" if enable else "none"
        subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', mode],
                       check=False, capture_output=True, timeout=5)
        if enable:
            for proto in ['socks', 'http', 'https']:
                subprocess.run(['gsettings', 'set', f'org.gnome.system.proxy.{proto}', 'host', host],
                               check=False, capture_output=True, timeout=5)
                subprocess.run(['gsettings', 'set', f'org.gnome.system.proxy.{proto}', 'port', str(port)],
                               check=False, capture_output=True, timeout=5)
        return True
    except Exception:
        return False

def set_linux_proxy(enable: bool, host: str = "127.0.0.1", port: int = 25443) -> bool:
    return set_linux_proxy_gnome(enable, host, port)

def set_system_proxy(enable: bool, host: str = "127.0.0.1", port: int = 25443):
    system = platform.system()
    if system == 'Windows':
        try:
            import winreg
            import ctypes
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"socks={host}:{port}")
                else:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        except Exception as e:
            print(f"Ошибка прокси: {e}")
            return False
        try:
            ctypes.windll.wininet.InternetSetOptionW(None, 39, None, 0)
            ctypes.windll.wininet.InternetSetOptionW(None, 37, None, 0)
        except Exception:
            pass
        return True
    else:
        return set_linux_proxy(enable, host, port)

# ==================================================================================================
# МОНИТОР ЗАДЕРЖКИ
# ==================================================================================================
class LatencyMonitor(QThread):
    warning_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    CHECK_INTERVAL = 30
    TIMEOUT = 10
    WARNING_THRESHOLD = 600
    TEST_URL = "https://www.google.com/generate_204"

    def __init__(self, proxy_host: str, proxy_port: int):
        super().__init__()
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.running = False
        self.daemon = True

    def run(self):
        self.running = True
        self.status_signal.emit(fix_emojis("🔍 Мониторинг задержки запущен"))
        while self.running:
            for _ in range(self.CHECK_INTERVAL):
                if not self.running:
                    break
                self.msleep(1000)
            if not self.running:
                break
            latency = self._measure_latency()
            if latency is None:
                self.warning_signal.emit(fix_emojis("🔴 ПРЕДУПРЕЖДЕНИЕ: Таймаут соединения"))
            elif latency > self.WARNING_THRESHOLD:
                self.warning_signal.emit(fix_emojis(f"🔴 ПРЕДУПРЕЖДЕНИЕ: Высокая задержка ({latency} мс)"))
            else:
                self.status_signal.emit(fix_emojis(f"🟢 Задержка в норме: {latency} мс"))

    def _measure_latency(self):
        try:
            proxy_handler = urllib.request.ProxyHandler({
                'https': f'socks5h://{self.proxy_host}:{self.proxy_port}',
                'http': f'socks5h://{self.proxy_host}:{self.proxy_port}'
            })
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-Agent', get_current_useragent())]
            start_time = time.time()
            response = opener.open(self.TEST_URL, timeout=self.TIMEOUT)
            response.read()
            elapsed_ms = int((time.time() - start_time) * 1000)
            response.close()
            return elapsed_ms
        except Exception:
            return self._measure_latency_socket()

    def _measure_latency_socket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.TIMEOUT)
            start = time.time()
            sock.connect((self.proxy_host, self.proxy_port))
            elapsed = int((time.time() - start) * 1000)
            sock.close()
            return elapsed
        except Exception:
            return None

    def stop(self):
        self.running = False

# ==================================================================================================
# WORKER ОБНОВЛЕНИЯ ПОДПИСОК
# ==================================================================================================
class SubscriptionUpdateWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, int, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, sub_manager: SubscriptionManager):
        super().__init__()
        self.sub_manager = sub_manager
        self.running = True
        self.daemon = True

    def run(self):
        while self.running:
            due_subs = self.sub_manager.get_subscriptions_due_update()
            if due_subs:
                self.log_signal.emit(fix_emojis(f"📡 Найдено {len(due_subs)} подписок для обновления"))
                total = len(due_subs)
                for i, sub in enumerate(due_subs, 1):
                    if not self.running:
                        break
                    self.progress_signal.emit(sub.get("name", sub["url"]), i, total)
                    success, message = self._update_single_subscription(sub)
                    if success:
                        self.log_signal.emit(fix_emojis(f"✅ {sub.get('name', 'Подписка')}: {message}"))
                    else:
                        self.log_signal.emit(fix_emojis(f"❌ {sub.get('name', 'Подписка')}: {message}"))
                    self.msleep(2000)
            for _ in range(60):
                if not self.running:
                    break
                self.msleep(1000)

    def _fetch_url_with_ssl_fix(self, url: str) -> str:
        """Загружает URL с обработкой SSL ошибок"""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': get_current_useragent()
            })
            with URL_OPENER.open(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            try:
                import requests
                response = requests.get(url, timeout=30, verify=False, headers={
                    'User-Agent': get_current_useragent()
                })
                response.raise_for_status()
                return response.text
            except ImportError:
                raise e
            except Exception as e2:
                raise e2

    def _parse_subscription_data(self, data: str) -> Tuple[List[str], bool]:
        """Парсит данные подписки. Возвращает (ключи, успех_распознавания)"""
        data = data.strip()
        valid_keys = []
        try:
            json_data = json.loads(data)
            if isinstance(json_data, dict) and "inbounds" in json_data and "outbounds" in json_data:
                valid_keys.append(json.dumps(json_data, ensure_ascii=False))
                return valid_keys, True
            if isinstance(json_data, list):
                for item in json_data:
                    if isinstance(item, str):
                        item = item.strip()
                        if item.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
                            valid_keys.append(item)
                        elif isinstance(item, dict) and "outbounds" in item:
                            valid_keys.append(json.dumps(item, ensure_ascii=False))
                if valid_keys:
                    return valid_keys, True
            elif isinstance(json_data, dict):
                for value in json_data.values():
                    if isinstance(value, str) and value.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
                        valid_keys.append(value.strip())
                if valid_keys:
                    return valid_keys, True
            return valid_keys, False
        except json.JSONDecodeError:
            pass
        try:
            padded = data + '=' * (-len(data) % 4)
            decoded = base64.b64decode(padded).decode('utf-8')
            lines = [l.strip() for l in decoded.splitlines() if l.strip()]
            valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'ss://'))]
            if valid_keys:
                return valid_keys, True
        except Exception:
            pass
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'ss://'))]
        if valid_keys:
            return valid_keys, True
        return valid_keys, False

    def _update_single_subscription(self, sub: dict) -> Tuple[bool, str]:
        url = sub["url"]
        try:
            data = self._fetch_url_with_ssl_fix(url)
            valid_keys, recognized = self._parse_subscription_data(data)
            if valid_keys:
                count = self.sub_manager.add_keys_from_subscription(url, valid_keys)
                return True, f"Обновлено: {count} новых ключей, всего: {sub.get('key_count', len(valid_keys))}"
            else:
                if recognized:
                    return False, "Не найдено валидных ключей в подписке (формат распознан, но ключи отсутствуют)"
                else:
                    error_msg = (
                        f"❌ Невозможно распознать ключи из ответа сервера.\n"
                        f"Сырой ответ сервера:\n"
                        f"{'='*50}\n"
                        f"{data[:1000]}{'...' if len(data) > 1000 else ''}\n"
                        f"{'='*50}"
                    )
                    return False, error_msg
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    def stop(self):
        self.running = False

# ==================================================================================================
# XRAY WORKER
# ==================================================================================================
class XrayWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.process = None
        self.is_running = False

    def run(self):
        xray_path = find_xray_binary()
        if not xray_path or not os.path.exists(xray_path):
            self.log_signal.emit(fix_emojis(f"❌ ОШИБКА: {XRAY_BINARY} не найден"))
            self.log_signal.emit(fix_emojis("Нажмите 'Проверить обновления' для установки Xray-core"))
            self.finished_signal.emit()
            return
        self.log_signal.emit(fix_emojis(f"📍 Найден xray: {xray_path}"))
        system = platform.system()
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'text': True,
            'bufsize': 1
        }
        if system == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['close_fds'] = True
            kwargs['start_new_session'] = True
        try:
            self.process = subprocess.Popen(
                [xray_path, "run", "-c", self.config_path],
                **kwargs
            )
            self.is_running = True
            if self.process.stdout:
                for line in self.process.stdout:
                    if not self.is_running:
                        break
                    self.log_signal.emit(line.strip())
        except Exception as e:
            self.log_signal.emit(fix_emojis(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}"))
        finally:
            self.finished_signal.emit()

    def stop(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass

# ==================================================================================================
# ДИАЛОГ НАСТРОЕК МАРШРУТИЗАЦИИ
# ==================================================================================================
class TunnelingSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(fix_emojis("⚙️ Настройки маршрутизации"))
        self.setMinimumSize(550, 400)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_current_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        desc_label = QLabel(fix_emojis("Выберите режим маршрутизации трафика:"))
        desc_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(desc_label)
        self.mode_group = QGroupBox(fix_emojis("Режимы маршрутизации"))
        mode_layout = QVBoxLayout(self.mode_group)
        self.mode_radio = {}
        for mode_key, mode_info in TUNNEL_MODES.items():
            radio = QRadioButton(fix_emojis(f"{mode_info['name']}"))
            radio.setToolTip(fix_emojis(mode_info['desc']))
            radio.clicked.connect(lambda checked, k=mode_key: self._on_mode_changed(k))
            self.mode_radio[mode_key] = radio
            mode_layout.addWidget(radio)
        info_label = QLabel(fix_emojis("ℹ️ Режим 'Всё в VPN' направляет ВЕСЬ трафик через прокси-сервер"))
        info_label.setStyleSheet("color: #888; font-size: 9pt; margin-top: 8px;")
        mode_layout.addWidget(info_label)
        layout.addWidget(self.mode_group)
        self.file_status = QLabel("")
        self.file_status.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.file_status)
        btn_layout = QHBoxLayout()
        self.btn_download = QPushButton(fix_emojis("🔄 Проверить и скачать файлы"))
        self.btn_download.clicked.connect(self._check_and_download_files)
        self.btn_apply = QPushButton(fix_emojis("✅ Применить"))
        self.btn_apply.clicked.connect(self._apply_settings)
        self.btn_apply.setEnabled(False)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #0066cc;")
        layout.addWidget(self.progress_label)

    def _load_current_settings(self):
        settings = load_json_file(os.path.join(DATA_DIR, "tunnel_settings.json"), {})
        current_mode = settings.get("mode", "ru_direct")
        if current_mode in self.mode_radio:
            self.mode_radio[current_mode].setChecked(True)
            self._update_file_status(current_mode)

    def _on_mode_changed(self, mode_key: str):
        self._update_file_status(mode_key)
        self.btn_apply.setEnabled(True)

    def _update_file_status(self, mode_key: str):
        mode = TUNNEL_MODES.get(mode_key)
        if not mode:
            return
        file_path = mode.get("file")
        if file_path is None:
            self.file_status.setText(fix_emojis("✅ Для режима 'Всё в VPN' файлы не требуются"))
            return
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        self.file_status.setText(fix_emojis(f"{status} Файл: {os.path.basename(file_path)} | {'Найден' if exists else 'Требуется загрузка'}"))

    def _check_and_download_files(self):
        self.btn_download.setEnabled(False)
        self.progress_label.setText(fix_emojis("🔄 Проверка файлов..."))
        QApplication.processEvents()
        success_count = 0
        total = len([m for m in TUNNEL_MODES.values() if m.get("file") is not None])
        for i, (mode_key, mode_info) in enumerate(TUNNEL_MODES.items(), 1):
            if mode_info.get("file") is None:
                continue
            self.progress_label.setText(fix_emojis(f"📥 [{i}/{total}] {mode_info['name']}..."))
            QApplication.processEvents()
            if ensure_geosite_file(mode_key, DATA_DIR):
                success_count += 1
        if ensure_geoip_file(DATA_DIR):
            success_count += 1
        self.progress_label.setText(fix_emojis(f"✅ Готово: {success_count}/{total + 1} файлов"))
        self.btn_download.setEnabled(True)
        current_mode = next((k for k, r in self.mode_radio.items() if r.isChecked()), None)
        if current_mode:
            self._update_file_status(current_mode)
        QMessageBox.information(self, fix_emojis("Результат"), fix_emojis(f"Проверка завершена.\nУспешно: {success_count}/{total + 1}"))

    def _apply_settings(self):
        selected_mode = None
        for mode_key, radio in self.mode_radio.items():
            if radio.isChecked():
                selected_mode = mode_key
                break
        if not selected_mode:
            QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Выберите режим туннелирования!"))
            return
        mode = TUNNEL_MODES[selected_mode]
        file_path = mode.get("file")
        if file_path is not None and not os.path.exists(file_path):
            reply = QMessageBox.question(
                self, fix_emojis("Файл не найден"),
                fix_emojis(f"Файл для режима '{mode['name']}' отсутствует.\nСкачать сейчас?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.progress_label.setText(fix_emojis(f"⏬ Загрузка {os.path.basename(file_path)}..."))
                QApplication.processEvents()
                if not download_file(mode["url"], file_path):
                    QMessageBox.critical(self, fix_emojis("Ошибка"), fix_emojis("Не удалось скачать файл!"))
                    return
            else:
                return
        settings = {
            "mode": selected_mode,
            "mode_name": mode["name"],
            "updated": datetime.now().isoformat()
        }
        save_json_file(os.path.join(DATA_DIR, "tunnel_settings.json"), settings)
        if self.parent_window and hasattr(self.parent_window, 'update_tunnel_mode'):
            self.parent_window.update_tunnel_mode(selected_mode)
        QMessageBox.information(self, fix_emojis("Успех"), fix_emojis(f"Режим применён: {mode['name']}"))
        self.accept()

# ==================================================================================================
# ДИАЛОГ УПРАВЛЕНИЯ ПОДПИСКАМИ
# ==================================================================================================
class SubscriptionDialog(QDialog):
    def __init__(self, sub_manager: SubscriptionManager, parent=None):
        super().__init__(parent)
        self.sub_manager = sub_manager
        self.setWindowTitle(fix_emojis("Управление подписками"))
        self.setMinimumSize(500, 400)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_subscriptions()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_group = QGroupBox(fix_emojis("Добавить подписку"))
        form_layout = QFormLayout(form_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/sub")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (опционально)")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(MIN_UPDATE_INTERVAL // 60, 1440)
        self.interval_spin.setValue(DEFAULT_UPDATE_INTERVAL // 60)
        self.interval_spin.setSuffix(" мин")
        form_layout.addRow("URL:", self.url_input)
        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Интервал:", self.interval_spin)
        add_btn = QPushButton(fix_emojis("➕ Добавить подписку"))
        add_btn.clicked.connect(self._add_subscription)
        form_layout.addRow(add_btn)
        layout.addWidget(form_group)
        list_group = QGroupBox(fix_emojis("Активные подписки"))
        list_layout = QVBoxLayout(list_group)
        self.sub_list = QListWidget()
        self.sub_list.itemDoubleClicked.connect(self._edit_subscription)
        list_layout.addWidget(self.sub_list)
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton(fix_emojis("🔄 Обновить сейчас"))
        self.btn_refresh.clicked.connect(self._force_update_selected)
        self.btn_delete = QPushButton(fix_emojis("🗑️ Удалить"))
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_delete.setStyleSheet("background-color: #FF1800; color: white;")
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_delete)
        list_layout.addLayout(btn_layout)
        layout.addWidget(list_group)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load_subscriptions(self):
        self.sub_list.clear()
        for sub in self.sub_manager.subscriptions:
            last_upd = sub.get("last_update")
            if last_upd:
                last_str = datetime.fromisoformat(last_upd).strftime("%H:%M %d.%m")
            else:
                last_str = "никогда"
            status = "✅ " if sub.get("enabled", True) else "⏸️ "
            text = f"{status}{sub.get('name', 'Без названия')}\n"
            text += f"🔗 {sub['url'][:40]}...\n"
            text += f"📊 Ключей: {sub.get('key_count', 0)} | 🕐 Обновлено: {last_str}"
            text = fix_emojis(text)
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, sub["id"])
            self.sub_list.addItem(item)

    def _add_subscription(self):
        url = self.url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Введите корректный URL подписки!"))
            return
        name = self.name_input.text().strip() or f"Подписка {len(self.sub_manager.subscriptions) + 1}"
        interval = self.interval_spin.value() * 60
        new_sub = self.sub_manager.add_subscription(url, interval)
        if name != new_sub["name"]:
            self.sub_manager.update_subscription(new_sub["id"], name=name)
        self._load_subscriptions()
        self.url_input.clear()
        self.name_input.clear()
        QMessageBox.information(self, fix_emojis("Успех"), fix_emojis("Подписка добавлена!"))

    def _edit_subscription(self, item: QListWidgetItem):
        sub_id = item.data(Qt.ItemDataRole.UserRole)
        sub = self.sub_manager.get_subscription(sub_id)
        if not sub:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(fix_emojis(f"Редактировать: {sub.get('name', 'Подписка')}"))
        layout = QFormLayout(dialog)
        interval_spin = QSpinBox()
        interval_spin.setRange(MIN_UPDATE_INTERVAL // 60, 1440)
        interval_spin.setValue(sub.get("update_interval", DEFAULT_UPDATE_INTERVAL) // 60)
        interval_spin.setSuffix(" мин")
        enabled_check = QCheckBox(fix_emojis("Включено"))
        enabled_check.setChecked(sub.get("enabled", True))
        layout.addRow(fix_emojis("Интервал обновления:"), interval_spin)
        layout.addRow(enabled_check)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(lambda: self._save_edit(sub_id, interval_spin.value(), enabled_check.isChecked(), dialog))
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        dialog.exec()

    def _save_edit(self, sub_id: str, interval_min: int, enabled: bool, dialog: QDialog):
        self.sub_manager.update_subscription(sub_id, update_interval=interval_min * 60, enabled=enabled)
        self._load_subscriptions()
        dialog.accept()

    def _delete_selected(self):
        item = self.sub_list.currentItem()
        if not item:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Выберите подписку!"))
            return
        sub_id = item.data(Qt.ItemDataRole.UserRole)
        sub = self.sub_manager.get_subscription(sub_id)
        reply = QMessageBox.question(
            self, fix_emojis("Подтверждение"),
            fix_emojis(f"Удалить подписку '{sub.get('name', sub['url'])}'?\n\n"
                       f"⚠️ Также будут удалены все ключи из этой подписки!"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sub_manager.remove_subscription(sub_id, remove_keys=True)
            self._load_subscriptions()
            if self.parent() and hasattr(self.parent(), 'refresh_keys_list'):
                self.parent().refresh_keys_list()

    def _force_update_selected(self):
        item = self.sub_list.currentItem()
        if not item:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Выберите подписку!"))
            return
        sub_id = item.data(Qt.ItemDataRole.UserRole)
        sub = self.sub_manager.get_subscription(sub_id)
        if self.parent() and hasattr(self.parent(), 'update_subscription_now'):
            self.parent().update_subscription_now(sub)
            self.accept()

# ==================================================================================================
# ОСНОВНОЙ КЛАСС
# ==================================================================================================
class XrayClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(fix_emojis("Bobcat Proxy 2.6 pre2 - Прокси отключен"))
        self.setFont(QFont("Arial"))
        self.setMinimumSize(950, 700)
        self.sub_manager = SubscriptionManager(KEYS_DB_PATH, SUBS_DB_PATH)
        self.xray_thread = None
        self.latency_monitor = None
        self.sub_update_worker = None
        self.update_checker = None
        self.download_worker = None
        self.system_proxy_enabled = False
        self.current_source_filter = "manual"
        self.current_tunnel_mode = "ru_direct"
        self.current_update_channel = self._get_update_channel()
        self.log_styles = {
            "dark": "background-color: #1e1e1e; color: #00ff00;",
            "light": "background-color: #ffffff; color: #000000;",
        }
        self.current_theme = get_system_theme()
        self.init_ui()
        self.log_buffer = []
        self.log_timer = None
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
        except Exception:
            pass
        print(fix_emojis(f"📁 Логи будут в: {LOGS_DIR}"))
        self.log_text.append(fix_emojis(f"📁 Путь к логам: {LOGS_DIR}"))
        self.log_text.append(fix_emojis(f"🔧 Xray-core версия: {XRAY_VERSION}"))
        self.log_text.append(fix_emojis(f"📡 Канал обновлений: {UPDATE_CHANNELS[self.current_update_channel]['name']}"))
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows")
            if preset_key == "custom":
                ua_info = "Свой User-Agent"
            else:
                ua_info = USERAGENT_PRESETS.get(preset_key, {}).get("name", "Неизвестно")
            self.log_text.append(fix_emojis(f"🌐 User-Agent: {ua_info}"))
        else:
            self.log_text.append(fix_emojis("🌐 User-Agent: Стандартный"))
        self.refresh_keys_list()
        self.refresh_subs_list()
        self.start_subscription_updates()
        self.update_status(False)
        self._load_tunnel_settings()
        QTimer.singleShot(2000, self.auto_check_updates)

    def _get_update_channel(self) -> str:
        settings = load_json_file(os.path.join(DATA_DIR, "update_settings.json"), {})
        return settings.get("channel", DEFAULT_UPDATE_CHANNEL)

    def auto_check_updates(self):
        if not find_xray_binary():
            self.append_log(fix_emojis("🔄 Xray-core не найден. Проверяю наличие обновлений для установки..."))
            self.check_for_updates(silent=True)
        else:
            self.append_log(fix_emojis("🔄 Автоматическая проверка обновлений Xray-core..."))
            self.check_for_updates(silent=True)

    def check_for_updates(self, silent=False):
        self.btn_check_updates.setEnabled(False)
        self.btn_check_updates.setText(fix_emojis("⏳ Проверка..."))
        channel = self._get_update_channel()
        self.update_checker = UpdateChecker(channel)
        self.update_checker.update_available.connect(
            lambda version, tag, url, size, ch: self.on_update_available(version, tag, url, size, silent)
        )
        self.update_checker.no_update.connect(
            lambda version: self.on_no_update(version, silent)
        )
        self.update_checker.error.connect(
            lambda error: self.on_update_error(error, silent)
        )
        self.update_checker.finished.connect(
            lambda: self.on_check_finished()
        )
        self.update_checker.start()

    def on_check_finished(self):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText(fix_emojis("🔄 Проверить обновления"))

    def on_update_available(self, version: str, tag: str, url: str, size: str, silent: bool):
        current = get_current_xray_version() or "не установлена"
        msg = fix_emojis(f"Доступна новая версия Xray-core: {version}\nТекущая: {current}\nРазмер: {size}")
        self.append_log(fix_emojis(f"📦 {msg}"))
        if not silent:
            reply = QMessageBox.question(
                self, fix_emojis("Доступно обновление Xray-core"),
                fix_emojis(f"{msg}\n\nСкачать и установить автоматически?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.download_update(url, version)
        else:
            if not find_xray_binary():
                reply = QMessageBox.question(
                    self, fix_emojis("Xray-core не найден"),
                    fix_emojis(f"Xray-core не установлен.\n\n"
                               f"Доступна версия {version} ({size}).\n"
                               f"Скачать и установить сейчас?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.download_update(url, version)
            else:
                if not hasattr(self, '_auto_update_asked'):
                    self._auto_update_asked = True
                    reply = QMessageBox.question(
                        self, fix_emojis("Доступно обновление Xray-core"),
                        fix_emojis(f"{msg}\n\nУстановить сейчас?"),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.download_update(url, version)

    def on_no_update(self, version: str, silent: bool):
        if not silent:
            self.append_log(fix_emojis(f"✅ Установлена последняя версия Xray-core: {version}"))
            QMessageBox.information(self, fix_emojis("Обновления Xray-core"),
                                    fix_emojis(f"Установлена последняя версия: {version}"))
        else:
            self.append_log(fix_emojis(f"✅ Xray-core актуален: v{version}"))

    def on_update_error(self, error: str, silent: bool):
        self.append_log(fix_emojis(f"❌ {error}"))
        if not silent:
            QMessageBox.warning(self, fix_emojis("Ошибка обновления"), fix_emojis(error))

    def download_update(self, url: str, version: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.append_log(fix_emojis(f"📥 Начинаю скачивание Xray-core v{version}..."))
        self.btn_check_updates.setEnabled(False)
        self.btn_check_updates.setText(fix_emojis("⏬ Скачивание..."))
        self.download_worker = DownloadWorker(url, version)
        self.download_worker.progress.connect(self.progress_bar.setValue)
        self.download_worker.status.connect(self.append_log)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText(fix_emojis("🔄 Проверить обновления"))
        self.append_log(fix_emojis(message))
        if success:
            global XRAY_PATH, XRAY_VERSION
            XRAY_PATH = find_xray_binary()
            XRAY_VERSION = get_current_xray_version() or "неизвестно"
            QMessageBox.information(self, fix_emojis("Обновление Xray-core"), fix_emojis(message))
        else:
            QMessageBox.warning(self, fix_emojis("Ошибка обновления"), fix_emojis(message))

    def _load_tunnel_settings(self):
        settings = load_json_file(os.path.join(DATA_DIR, "tunnel_settings.json"), {})
        self.current_tunnel_mode = settings.get("mode", "ru_direct")
        self.log_text.append(fix_emojis(f"🔧 Режим туннелирования: {TUNNEL_MODES.get(self.current_tunnel_mode, {}).get('name', 'Неизвестно')}"))

    def update_tunnel_mode(self, mode_key: str):
        if mode_key in TUNNEL_MODES:
            self.current_tunnel_mode = mode_key
            self._update_tunnel_mode_label()
            self.log_text.append(fix_emojis(f"🔄 Режим изменён: {TUNNEL_MODES[mode_key]['name']}"))
            if self.xray_thread and self.xray_thread.isRunning():
                self.log_text.append(fix_emojis("⚠️ Перезапустите прокси для применения новых настроек маршрутизации"))

    def _get_key_display_mode(self) -> str:
        config = load_json_file(os.path.join(DATA_DIR, "ui_settings.json"), {})
        return config.get("key_display_mode", DEFAULT_KEY_DISPLAY_MODE)

    def _set_key_display_mode(self, mode: str):
        config = load_json_file(os.path.join(DATA_DIR, "ui_settings.json"), {})
        config["key_display_mode"] = mode
        save_json_file(os.path.join(DATA_DIR, "ui_settings.json"), config)

    def _get_log_mode(self) -> str:
        config = load_json_file(os.path.join(DATA_DIR, "ui_settings.json"), {})
        return config.get("log_mode", DEFAULT_LOG_MODE)

    def _get_xray_loglevel(self) -> str:
        log_mode = self._get_log_mode()
        return "debug" if log_mode == "debug" else "warning"

    def _set_log_mode(self, mode: str):
        config = load_json_file(os.path.join(DATA_DIR, "ui_settings.json"), {})
        config["log_mode"] = mode
        save_json_file(os.path.join(DATA_DIR, "ui_settings.json"), config)

    def _format_key_display(self, key_data: dict, index: int) -> str:
        key = key_data["key"]
        source_icon = "📡" if key_data.get("source") == "subscription" else "✋"
        mode = self._get_key_display_mode()
        if mode == "legacy":
            if key.startswith('{') and key.endswith('}'):
                name = "📄 JSON-конфиг"
            elif '://' in key:
                proto, rest = key.split('://', 1)
                preview = rest[:8] if len(rest) >= 8 else rest
                name = f"{proto}://{preview}..."
            else:
                name = key[:80] + "..." if len(key) > 80 else key
            return f"{source_icon}{index+1}. {name}"
        elif mode == "detailed":
            parsed = parse_key_for_display(key)
            addr_short = parsed["address"]
            if len(addr_short) > 20:
                addr_short = addr_short[:17] + "..."
            name = f"{parsed['protocol']} | {addr_short} | {parsed['transport']}"
            return f"{source_icon}{index+1}. {name}"
        else:
            parsed = parse_key_for_display(key)
            hashtag = parsed.get("hashtag", "").strip()
            if hashtag:
                if len(hashtag) > 30:
                    hashtag = hashtag[:27] + "..."
                name = f"🏷️ {hashtag}"
            else:
                proto = parsed.get("protocol", "???")
                addr = parsed.get("address", "???")
                if len(addr) > 15:
                    addr = addr[:12] + "..."
                name = f"🔗 {proto} | {addr}"
            return f"{source_icon}{index+1}. {name}"

    def _change_key_display_mode(self, mode: str):
        if mode in KEY_DISPLAY_MODES:
            self._set_key_display_mode(mode)
            self.refresh_keys_list()
            self.log_text.append(fix_emojis(f"🔑 Формат отображения: {KEY_DISPLAY_MODES[mode]}"))

    def _change_log_mode(self, mode: str):
        if mode in LOG_MODES:
            self._set_log_mode(mode)
            mode_name = LOG_MODES[mode]
            self.log_text.clear()
            if mode == "debug":
                self.log_text.append(f"<span style='color:#00bcd4'>{fix_emojis('🔍 Включен режим отладки (xray-core: debug)')}</span>")
                self.log_text.append("<span style='color:#888888'>В этом режиме отображаются все сообщения от xray-core</span>")
            else:
                self.log_text.append(fix_emojis("📝 Включен обычный режим логирования (xray-core: warning)"))
                self.log_text.append("<span style='color:#888888'>Отображаются только предупреждения и ошибки от xray-core</span>")
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _save_logs_to_file(self):
        if not self.log_buffer:
            return
        now = datetime.now()
        filename = f"xraylog_{now.day:02d}_{now.month:02d}_{now.year}_{now.hour:02d}_{now.minute:02d}.txt"
        filepath = os.path.join(LOGS_DIR, filename)
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                for entry in self.log_buffer:
                    clean_text = re.sub(r'<[^>]+>', '', entry) if '<' in entry else entry
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {clean_text}\n")
            self.log_buffer.clear()
        except Exception as e:
            print(f"❌ Ошибка записи лога: {e}")

    def append_log(self, text):
        try:
            text = fix_emojis(str(text))  # <-- Замена эмодзи
            log_mode = self._get_log_mode()
            self.log_buffer.append(text)
            if self.log_timer is None:
                self.log_timer = QTimer()
                self.log_timer.timeout.connect(self._save_logs_to_file)
                self.log_timer.start(60000)
            if log_mode == "debug":
                if "ПРЕДУПРЕЖДЕНИЕ" in text or "❌" in text or "ERROR" in text.upper():
                    txt = f"<span style='color:#ff6b6b;font-weight:bold'>[DEBUG] {text}</span>"
                elif "✅" in text or "🟢" in text:
                    txt = f"<span style='color:#51cf66'>[DEBUG] {text}</span>"
                elif "⚠️" in text or "🔴" in text or "CRITICAL" in text:
                    txt = f"<span style='color:#ffa94d'>[DEBUG] {text}</span>"
                elif "🔄" in text or "📡" in text or "⏳" in text or "📦" in text or "📥" in text:
                    txt = f"<span style='color:#00bcd4'>[DEBUG] {text}</span>"
                else:
                    txt = f"<span style='color:#888888'>[DEBUG] {text}</span>"
                self.log_text.append(txt)
                self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
                return
            if "ПРЕДУПРЕЖДЕНИЕ" in text or "❌" in text or "ERROR" in text.upper():
                txt = f"<span style='color:#ff6b6b;font-weight:bold'>{text}</span>"
            elif "✅" in text or "🟢" in text:
                txt = f"<span style='color:#51cf66'>{text}</span>"
            elif "⚠️" in text or "🔴" in text or "CRITICAL" in text:
                txt = f"<span style='color:#ffa94d'>{text}</span>"
            else:
                return
            self.log_text.append(txt)
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        except AttributeError:
            print(f"[LOG] {text}")

    def cleanup_all(self):
        if self.log_timer and self.log_timer.isActive():
            self.log_timer.stop()
            self._save_logs_to_file()
        if self.latency_monitor and self.latency_monitor.isRunning():
            self.latency_monitor.stop()
            self.latency_monitor.wait(1000)
        if self.sub_update_worker and self.sub_update_worker.isRunning():
            self.sub_update_worker.stop()
            self.sub_update_worker.wait(1000)
        if self.xray_thread and self.xray_thread.isRunning():
            self.xray_thread.stop()
            self.xray_thread.wait()
        if self.system_proxy_enabled:
            set_system_proxy(False)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        top_bar_layout = QHBoxLayout()
        self.btn_settings = QPushButton(fix_emojis("⚙️ Настройки"))
        self.btn_settings.clicked.connect(self.show_settings_menu)
        self.btn_subs_manager = QPushButton(fix_emojis("📡 Подписки"))
        self.btn_subs_manager.clicked.connect(self.show_subscription_manager)
        self.btn_check_updates = QPushButton(fix_emojis("🔄 Проверить обновления"))
        self.btn_check_updates.clicked.connect(lambda: self.check_for_updates())
        self.chk_system_proxy = QCheckBox(fix_emojis("Системный прокси"))
        self.chk_system_proxy.setChecked(False)
        top_bar_layout.addWidget(self.btn_settings)
        top_bar_layout.addWidget(self.btn_subs_manager)
        top_bar_layout.addWidget(self.btn_check_updates)
        top_bar_layout.addWidget(self.chk_system_proxy)
        top_bar_layout.addStretch()
        left_layout.addLayout(top_bar_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedHeight(20)
        left_layout.addWidget(self.progress_bar)
        version_text = f"Xray-core: v{XRAY_VERSION} | Канал: {UPDATE_CHANNELS[self.current_update_channel]['name']}"
        self.version_label = QLabel(version_text)
        self.version_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")
        left_layout.addWidget(self.version_label)
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows")
            if preset_key == "custom":
                ua_text = "🌐 UA: Свой"
            else:
                ua_text = f"🌐 UA: {USERAGENT_PRESETS.get(preset_key, {}).get('name', 'Chrome')}"
        else:
            ua_text = "🌐 UA: Стандартный"
        self.ua_label = QLabel(fix_emojis(ua_text))
        self.ua_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")
        self.ua_label.setToolTip(get_current_useragent())
        left_layout.addWidget(self.ua_label)
        keys_tabs = QTabWidget()
        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        self.key_selector_all = QComboBox()
        self.key_selector_all.setEditable(False)
        self.key_selector_all.currentIndexChanged.connect(self._on_key_selected)
        all_layout.addWidget(self.key_selector_all)
        keys_tabs.addTab(all_tab, fix_emojis("📋 Все"))
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        self.key_selector_manual = QComboBox()
        self.key_selector_manual.setEditable(False)
        self.key_selector_manual.currentIndexChanged.connect(
            lambda: self._on_key_selected_tab("manual"))
        manual_layout.addWidget(self.key_selector_manual)
        keys_tabs.addTab(manual_tab, fix_emojis("✋ Ручные"))
        sub_tab = QWidget()
        sub_layout = QVBoxLayout(sub_tab)
        self.key_selector_sub = QComboBox()
        self.key_selector_sub.setEditable(False)
        self.key_selector_sub.currentIndexChanged.connect(
            lambda: self._on_key_selected_tab("subscription"))
        sub_layout.addWidget(self.key_selector_sub)
        self.sub_filter = QComboBox()
        self.sub_filter.addItem(fix_emojis("Все подписки"))
        self.sub_filter.currentIndexChanged.connect(self._filter_subs_keys)
        sub_layout.addWidget(self.sub_filter)
        keys_tabs.addTab(sub_tab, fix_emojis("📡 Подписки"))
        keys_group = QGroupBox(fix_emojis("Добавить конфигурацию"))
        keys_layout = QVBoxLayout(keys_group)
        input_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("vless://... или vmess://... или JSON")
        self.btn_add = QPushButton(fix_emojis("➕ Добавить"))
        self.btn_add.clicked.connect(self.add_manual_key)
        input_layout.addWidget(self.key_input)
        input_layout.addWidget(self.btn_add)
        keys_layout.addLayout(input_layout)
        add_sub_layout = QHBoxLayout()
        self.sub_url_input = QLineEdit()
        self.sub_url_input.setPlaceholderText("URL подписки (Base64/JSON/plain)")
        self.btn_add_sub_once = QPushButton(fix_emojis("📥 Импорт"))
        self.btn_add_sub_once.clicked.connect(self.import_subscription_once)
        add_sub_layout.addWidget(self.sub_url_input)
        add_sub_layout.addWidget(self.btn_add_sub_once)
        keys_layout.addLayout(add_sub_layout)
        json_import_layout = QHBoxLayout()
        self.json_input = QLineEdit()
        self.json_input.setPlaceholderText("Путь к .json файлу или вставьте JSON-конфиг")
        self.btn_import_json = QPushButton(fix_emojis("📄 Импорт JSON"))
        self.btn_import_json.clicked.connect(self.import_json_config)
        self.btn_import_json.setToolTip(fix_emojis("Импортировать полный конфиг Xray (inbounds/outbounds)"))
        json_import_layout.addWidget(self.json_input)
        json_import_layout.addWidget(self.btn_import_json)
        keys_layout.addLayout(json_import_layout)
        keys_layout.addWidget(keys_tabs)
        delete_layout = QHBoxLayout()
        self.btn_delete_selected = QPushButton(fix_emojis("🗑️ Удалить выбранный"))
        self.btn_delete_selected.clicked.connect(self.delete_selected_key)
        self.btn_delete_selected.setStyleSheet("background-color: #FF1800; color: white;")
        self.btn_delete_all = QPushButton(fix_emojis("🗑️ Удалить все"))
        self.btn_delete_all.clicked.connect(self.delete_all_keys)
        self.btn_delete_all.setStyleSheet("background-color: #FF1800; color: white;")
        delete_layout.addWidget(self.btn_delete_selected)
        delete_layout.addWidget(self.btn_delete_all)
        keys_layout.addLayout(delete_layout)
        left_layout.addWidget(keys_group)
        log_group = QGroupBox(fix_emojis("Лог xray-core"))
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 9))
        self.log_text.setStyleSheet(self.log_styles[self.current_theme])
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group, stretch=1)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch()
        self.btn_power = QPushButton(fix_emojis("ВКЛЮЧИТЬ"))
        self.btn_power.setFixedSize(150, 150)
        self.btn_power.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; color: white; border-radius: 75px;
                font-size: 20px; font-weight: bold; border: 4px solid #27ae60;
            }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:disabled { background-color: #95a5a6; border-color: #7f8c8d; }
        """)
        self.btn_power_off_style = """
            QPushButton {
                background-color: #e74c3c; color: white; border-radius: 75px;
                font-size: 20px; font-weight: bold; border: 4px solid #c0392b;
            }
            QPushButton:hover { background-color: #c0392b; }
        """
        self.btn_power.clicked.connect(self.toggle_proxy)
        right_layout.addWidget(self.btn_power, alignment=Qt.AlignmentFlag.AlignCenter)
        status_label = QLabel(f"SOCKS5 :{LOCAL_PROXY_PORT}")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.tunnel_mode_label = QLabel("")
        self.tunnel_mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tunnel_mode_label.setStyleSheet("color: #0066cc; font-size: 9pt; font-weight: bold;")
        self._update_tunnel_mode_label()
        right_layout.addWidget(self.tunnel_mode_label)
        self.status_info = QLabel("")
        self.status_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_info.setStyleSheet("color: #888; font-size: 9pt;")
        right_layout.addWidget(self.status_info)
        right_layout.addStretch()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)
        self.current_key_index = -1
        self.current_tab = "all"

    def _update_tunnel_mode_label(self):
        mode_info = TUNNEL_MODES.get(self.current_tunnel_mode, {})
        self.tunnel_mode_label.setText(fix_emojis(f"🔗 {mode_info.get('name', 'Режим не выбран')}"))

    def _update_ua_label(self):
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows")
            if preset_key == "custom":
                ua_text = "🌐 UA: Свой"
            else:
                ua_text = f"🌐 UA: {USERAGENT_PRESETS.get(preset_key, {}).get('name', 'Chrome')}"
        else:
            ua_text = "🌐 UA: Стандартный"
        self.ua_label.setText(fix_emojis(ua_text))
        self.ua_label.setToolTip(get_current_useragent())
        global URL_OPENER
        URL_OPENER = create_opener_with_ssl_fix()

    def show_settings_menu(self):
        menu = QMenu(self)
        menu.setFont(QFont("Arial", 10))
        display_menu = QMenu(fix_emojis("🔑 Формат отображения ключей"), self)
        current_display_mode = self._get_key_display_mode()
        for mode_key, mode_name in KEY_DISPLAY_MODES.items():
            action = QAction(fix_emojis(mode_name), self)
            action.setCheckable(True)
            action.setChecked(mode_key == current_display_mode)
            action.triggered.connect(lambda checked, m=mode_key: self._change_key_display_mode(m))
            display_menu.addAction(action)
        menu.addMenu(display_menu)
        log_menu = QMenu(fix_emojis("📝 Режим логирования xray-core"), self)
        current_log_mode = self._get_log_mode()
        for mode_key, mode_name in LOG_MODES.items():
            action = QAction(fix_emojis(mode_name), self)
            action.setCheckable(True)
            action.setChecked(mode_key == current_log_mode)
            action.triggered.connect(lambda checked, m=mode_key: self._change_log_mode(m))
            log_menu.addAction(action)
        menu.addMenu(log_menu)
        menu.addSeparator()
        ua_action = QAction(fix_emojis("🌐 Настройка User-Agent"), self)
        ua_action.triggered.connect(self.show_useragent_settings)
        menu.addAction(ua_action)
        menu.addSeparator()
        tunnel_action = QAction(fix_emojis("🔐 Маршрутизация"), self)
        tunnel_action.triggered.connect(self.show_tunneling_settings)
        menu.addAction(tunnel_action)
        menu.addSeparator()
        update_settings_action = QAction(fix_emojis("🔄 Настройки обновлений Xray-core"), self)
        update_settings_action.triggered.connect(self.show_update_settings)
        menu.addAction(update_settings_action)
        check_updates_action = QAction(fix_emojis("🔄 Проверить обновления Xray-core"), self)
        check_updates_action.triggered.connect(lambda: self.check_for_updates())
        menu.addAction(check_updates_action)
        geoip_action = QAction(fix_emojis("🌍 Обновить GeoIP/GeoSite"), self)
        geoip_action.triggered.connect(self.update_geo_files)
        menu.addAction(geoip_action)
        menu.addSeparator()
        about_action = QAction(fix_emojis("ℹ️ О программе"), self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))

    def show_useragent_settings(self):
        dialog = UserAgentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_ua_label()
            ua = get_current_useragent()
            self.append_log(fix_emojis(f"🌐 User-Agent изменён: {ua[:60]}..."))
            global URL_OPENER
            URL_OPENER = create_opener_with_ssl_fix()

    def show_update_settings(self):
        dialog = UpdateSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_update_channel = self._get_update_channel()
            channel_name = UPDATE_CHANNELS[self.current_update_channel]['name']
            self.append_log(fix_emojis(f"📡 Канал обновлений изменён: {channel_name}"))
            self.version_label.setText(fix_emojis(f"Xray-core: v{XRAY_VERSION} | Канал: {channel_name}"))

    def show_tunneling_settings(self):
        dialog = TunnelingSettingsDialog(self)
        dialog.exec()

    def update_geo_files(self):
        self.log_text.append(fix_emojis("🔄 Обновление GeoIP/GeoSite..."))
        success = ensure_geoip_file(DATA_DIR)
        for mode_key in TUNNEL_MODES:
            if TUNNEL_MODES[mode_key].get("file") is not None:
                if ensure_geosite_file(mode_key, DATA_DIR):
                    success = True
        if success:
            self.log_text.append(fix_emojis("✅ Файлы обновлены"))
        else:
            self.log_text.append(fix_emojis("❌ Ошибка обновления файлов"))

    def show_about(self):
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows")
            if preset_key == "custom":
                ua_info = "Свой User-Agent"
            else:
                ua_info = USERAGENT_PRESETS.get(preset_key, {}).get("name", "Неизвестно")
        else:
            ua_info = "Стандартный"
        QMessageBox.information(
            self, fix_emojis("О программе"),
            fix_emojis(f"Bobcat Proxy 2.6 pre2 \n\n"
                       f"Клиент для Xray-core с поддержкой:\n"
                       f"• VLESS/VMess/Trojan/Shadowsocks\n"
                       f"• Автообновление подписок\n"
                       f"• Гибкая маршрутизация (включая режим 'Всё в VPN')\n"
                       f"• Автоматическое обновление Xray-core\n"
                       f"• Выбор канала обновлений (стабильный/пре-релиз)\n"
                       f"• Настройка User-Agent\n"
                       f"• Кроссплатформенность (Linux/Windows)\n\n"
                       f"Xray-core версия: {XRAY_VERSION}\n"
                       f"Канал обновлений: {UPDATE_CHANNELS[self.current_update_channel]['name']}\n"
                       f"User-Agent: {ua_info}\n"
                       f"https://github.com/XTLS/Xray-core\n"
                       f"Сообщить о багах BugreportBobcatProxy@protonmail.com\n\n")
        )

    def _on_key_selected(self, index: int):
        self.current_tab = "all"
        self.current_key_index = index
        self._update_status_info()

    def _on_key_selected_tab(self, source: str):
        self.current_tab = "filtered"
        self.current_source_filter = source
        self._update_status_info()

    def _update_status_info(self):
        keys = self._get_current_keys_list()
        if 0 <= self.current_key_index < len(keys):
            key_data = keys[self.current_key_index]
            source = "✋ Ручной" if key_data.get("source") == "manual" else "📡 Подписка"
            self.status_info.setText(fix_emojis(f"{source} | Добавлен: {key_data.get('added', '?')[:16]}"))
        else:
            self.status_info.setText("")

    def _get_current_keys_list(self) -> list:
        if self.current_tab == "all":
            return self.sub_manager.keys
        elif self.current_tab == "filtered":
            return self.sub_manager.get_keys_by_source(self.current_source_filter)
        return self.sub_manager.keys

    def closeEvent(self, event):
        self.cleanup_all()
        event.accept()

    def cleanup_system_proxy(self):
        if self.system_proxy_enabled:
            set_system_proxy(False)
            self.system_proxy_enabled = False
            self.log_text.append(fix_emojis("🔌 Системный прокси отключён"))

    def show_subscription_manager(self):
        dialog = SubscriptionDialog(self.sub_manager, self)
        dialog.exec()
        self.refresh_keys_list()
        self.refresh_subs_list()

    def refresh_keys_list(self):
        self.key_selector_all.clear()
        for i, key_data in enumerate(self.sub_manager.keys):
            display_text = fix_emojis(self._format_key_display(key_data, i))
            self.key_selector_all.addItem(display_text)
            if i < self.key_selector_all.count():
                self.key_selector_all.setItemData(i, key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"], Qt.ItemDataRole.ToolTipRole)
        self.key_selector_manual.clear()
        manual_keys = self.sub_manager.get_keys_by_source("manual")
        for i, key_data in enumerate(manual_keys):
            display_text = fix_emojis(self._format_key_display(key_data, i))
            self.key_selector_manual.addItem(display_text)
            if i < self.key_selector_manual.count():
                self.key_selector_manual.setItemData(i, key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"], Qt.ItemDataRole.ToolTipRole)
        self.key_selector_sub.clear()
        sub_keys = self.sub_manager.get_keys_by_source("subscription")
        for i, key_data in enumerate(sub_keys):
            display_text = fix_emojis(self._format_key_display(key_data, i))
            sub_name = self._get_sub_name_by_url(key_data.get("sub_url"))
            full_text = f"[{sub_name}] {display_text.split('. ', 1)[-1]}"
            self.key_selector_sub.addItem(full_text)
            if i < self.key_selector_sub.count():
                self.key_selector_sub.setItemData(i, key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"], Qt.ItemDataRole.ToolTipRole)
        self._refresh_sub_filter()
        has_keys = len(self.sub_manager.keys) > 0
        self.btn_delete_selected.setEnabled(has_keys)
        self.btn_delete_all.setEnabled(has_keys)

    def _get_sub_name_by_url(self, url: str) -> str:
        if not url:
            return "???"
        for sub in self.sub_manager.subscriptions:
            if sub["url"] == url:
                return sub.get("name", url.split("/")[-1][:15])
        return url.split("/")[-1][:15]

    def _refresh_sub_filter(self):
        current = self.sub_filter.currentText()
        self.sub_filter.blockSignals(True)
        self.sub_filter.clear()
        self.sub_filter.addItem(fix_emojis("Все подписки"))
        for sub in self.sub_manager.subscriptions:
            name = sub.get("name", sub["url"].split("/")[-1][:20])
            count = sub.get("key_count", 0)
            self.sub_filter.addItem(fix_emojis(f"{name} ({count})"), sub["url"])
        idx = self.sub_filter.findText(current)
        if idx >= 0:
            self.sub_filter.setCurrentIndex(idx)
        self.sub_filter.blockSignals(False)

    def _filter_subs_keys(self, index: int):
        if index == 0:
            keys = self.sub_manager.get_keys_by_source("subscription")
        else:
            sub_url = self.sub_filter.itemData(index)
            keys = [k for k in self.sub_manager.keys
                    if k.get("source") == "subscription" and k.get("sub_url") == sub_url]
        self.key_selector_sub.clear()
        for i, key_data in enumerate(keys):
            display_text = fix_emojis(self._format_key_display(key_data, i))
            sub_name = self._get_sub_name_by_url(key_data.get('sub_url'))
            full_text = f"[{sub_name}] {display_text.split('. ', 1)[-1]}"
            self.key_selector_sub.addItem(full_text)
            if i < self.key_selector_sub.count():
                self.key_selector_sub.setItemData(i, key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"], Qt.ItemDataRole.ToolTipRole)

    def refresh_subs_list(self):
        active = len([s for s in self.sub_manager.subscriptions if s.get("enabled")])
        if active > 0:
            self.log_text.append(fix_emojis(f"📡 Активно подписок: {active}"))

    def delete_selected_key(self):
        keys = self._get_current_keys_list()
        if self.current_tab == "all":
            idx = self.key_selector_all.currentIndex()
        elif self.current_source_filter == "manual":
            idx = self.key_selector_manual.currentIndex()
        else:
            idx = self.key_selector_sub.currentIndex()
        if idx == -1 or not keys:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Нет выбранного ключа!"))
            return
        key_data = keys[idx]
        preview = key_data["key"][:30] + "..." if len(key_data["key"]) > 30 else key_data["key"]
        if key_data.get("source") == "subscription":
            reply = QMessageBox.question(
                self, fix_emojis("Подтверждение"),
                fix_emojis(f"Удалить ключ?\n{preview}\n\n"
                           f"⚠️ Ключ из подписки! Он может вернуться при следующем обновлении."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        else:
            reply = QMessageBox.question(
                self, fix_emojis("Подтверждение"),
                fix_emojis(f"Удалить ключ?\n{preview}"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        if reply == QMessageBox.StandardButton.Yes:
            key_id = key_data.get("id")
            self.sub_manager.keys = [k for k in self.sub_manager.keys if k.get("id") != key_id]
            self.sub_manager._save_keys()
            self.refresh_keys_list()
            self.log_text.append(fix_emojis("🗑️ Ключ удалён"))
            if not self.sub_manager.keys and self.xray_thread and self.xray_thread.isRunning():
                self.toggle_proxy()

    def delete_all_keys(self):
        if not self.sub_manager.keys:
            QMessageBox.information(self, fix_emojis("Информация"), fix_emojis("Список уже пуст!"))
            return
        reply = QMessageBox.question(
            self, fix_emojis("Подтверждение"),
            fix_emojis(f"Удалить ВСЕ ключи ({len(self.sub_manager.keys)})?\n\n"
                       f"⚠️ Ключи из подписок можно будет восстановить обновлением!"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sub_manager.keys.clear()
            self.sub_manager._save_keys()
            self.refresh_keys_list()
            self.log_text.append(fix_emojis("🗑️ Все ключи удалены!"))
            if self.xray_thread and self.xray_thread.isRunning():
                self.toggle_proxy()

    def _parse_subscription_data(self, data: str) -> List[str]:
        """Парсит данные подписки. Если не удалось распознать - выводит сырой ответ сервера."""
        data = data.strip()
        valid_keys = []
        try:
            json_data = json.loads(data)
            if isinstance(json_data, dict) and "inbounds" in json_data and "outbounds" in json_data:
                valid_keys.append(json.dumps(json_data, ensure_ascii=False))
                return valid_keys
            if isinstance(json_data, list):
                for item in json_data:
                    if isinstance(item, str):
                        item = item.strip()
                        if item.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
                            valid_keys.append(item)
                        elif isinstance(item, dict) and "outbounds" in item:
                            valid_keys.append(json.dumps(item, ensure_ascii=False))
            elif isinstance(json_data, dict):
                for value in json_data.values():
                    if isinstance(value, str) and value.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
                        valid_keys.append(value.strip())
            if valid_keys:
                return valid_keys
        except json.JSONDecodeError:
            pass
        try:
            padded = data + '=' * (-len(data) % 4)
            decoded = base64.b64decode(padded).decode('utf-8')
            lines = [l.strip() for l in decoded.splitlines() if l.strip()]
            valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'ss://'))]
            if valid_keys:
                return valid_keys
        except Exception:
            pass
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'ss://'))]
        if not valid_keys:
            self.log_text.append(fix_emojis("❌ Невозможно распознать ключи из ответа сервера"))
            self.log_text.append(f"Сырой ответ сервера:\n{'='*50}")
            preview = data[:2000] + ('...' if len(data) > 2000 else '')
            self.log_text.append(preview)
            self.log_text.append(f"{'='*50}")
        return valid_keys

    def _validate_xray_config(self, config: dict) -> bool:
        return isinstance(config, dict) and "inbounds" in config and "outbounds" in config

    def import_json_config(self):
        text = self.json_input.text().strip()
        if not text:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Введите путь к файлу или вставьте JSON-конфиг!"))
            return
        config = None
        if os.path.exists(text) and text.lower().endswith('.json'):
            try:
                with open(text, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                self.log_text.append(fix_emojis(f"❌ Ошибка парсинга файла: {e}"))
                return
            except Exception as e:
                self.log_text.append(fix_emojis(f"❌ Ошибка чтения файла: {e}"))
                return
        elif text.startswith('{') and text.endswith('}'):
            try:
                config = json.loads(text)
            except json.JSONDecodeError as e:
                self.log_text.append(fix_emojis(f"❌ Ошибка парсинга JSON: {e}"))
                return
        if config and self._validate_xray_config(config):
            config_json = json.dumps(config, ensure_ascii=False, indent=2)
            for k in self.sub_manager.keys:
                try:
                    if json.loads(k["key"]) == config:
                        self.log_text.append(fix_emojis("⚠️ Этот конфиг уже в списке"))
                        self.json_input.clear()
                        return
                except Exception:
                    continue
            self.sub_manager.add_manual_key(config_json)
            self.sub_manager._save_keys()
            self.refresh_keys_list()
            self.log_text.append(fix_emojis(f"✅ JSON-конфиг импортирован | inbounds: {len(config.get('inbounds', []))}, outbounds: {len(config.get('outbounds', []))}"))
        else:
            self.log_text.append(fix_emojis("❌ Неверный формат: требуется конфиг Xray с полями inbounds/outbounds"))
        self.json_input.clear()

    def add_manual_key(self):
        text = self.key_input.text().strip()
        if not text:
            return
        if text.startswith('{') and text.endswith('}'):
            try:
                parsed = json.loads(text)
                if "outbounds" in parsed and "inbounds" in parsed:
                    if self.sub_manager.add_manual_key(text):
                        self.log_text.append(fix_emojis("✅ JSON-конфиг добавлен"))
                    else:
                        self.log_text.append(fix_emojis("⚠️ Конфиг уже в списке"))
                    self.sub_manager._save_keys()
                    self.refresh_keys_list()
                    self.key_input.clear()
                    return
                else:
                    self.log_text.append(fix_emojis("❌ Неверный JSON: отсутствуют outbounds/inbounds"))
                    return
            except json.JSONDecodeError:
                self.log_text.append(fix_emojis("❌ Ошибка парсинга JSON"))
                return
        if text.startswith("http"):
            reply = QMessageBox.question(
                self, fix_emojis("Обнаружена ссылка"),
                fix_emojis("Это ссылка на подписку.\nДобавить как автообновляемую подписку?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.sub_manager.add_subscription(text)
                self.log_text.append(fix_emojis("📡 Подписка добавлена! Обновление в фоне."))
                self.refresh_subs_list()
                self.update_subscription_now(self.sub_manager.get_subscription(text))
            else:
                self.import_subscription_once()
        else:
            if text.startswith(('vmess://', 'vless://', 'trojan://', 'ss://')):
                if self.sub_manager.add_manual_key(text):
                    self.log_text.append(fix_emojis("✅ Ключ добавлен"))
                else:
                    self.log_text.append(fix_emojis("⚠️ Ключ уже в списке"))
            else:
                self.log_text.append(fix_emojis("❌ Неверный формат ключа"))
        self.sub_manager._save_keys()
        self.refresh_keys_list()
        self.key_input.clear()

    def import_subscription_once(self):
        url = self.sub_url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Введите корректный URL!"))
            return
        self.log_text.append(fix_emojis("📥 Импорт подписки..."))
        try:
            req = urllib.request.Request(url, headers={'User-Agent': get_current_useragent()})
            with URL_OPENER.open(req, timeout=30) as response:
                data = response.read().decode('utf-8')
                valid_keys = self._parse_subscription_data(data)
                count = 0
                for key_str in valid_keys:
                    if self.sub_manager.add_manual_key(key_str):
                        count += 1
                self.log_text.append(fix_emojis(f"✅ Импортировано {count} ключей"))
                self.sub_manager._save_keys()
                self.refresh_keys_list()
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Ошибка импорта: {e}"))
        self.sub_url_input.clear()

    def update_subscription_now(self, sub: dict):
        if not sub:
            return
        self.log_text.append(fix_emojis(f"🔄 Обновление: {sub.get('name', sub['url'])}"))
        try:
            req = urllib.request.Request(sub["url"], headers={'User-Agent': get_current_useragent()})
            with URL_OPENER.open(req, timeout=30) as response:
                data = response.read().decode('utf-8')
                valid_keys = self._parse_subscription_data(data)
                if valid_keys:
                    count = self.sub_manager.add_keys_from_subscription(sub["url"], valid_keys)
                    self.log_text.append(fix_emojis(f"✅ {sub.get('name', 'Подписка')}: +{count} новых, всего: {len(valid_keys)}"))
                    self.refresh_keys_list()
                else:
                    self.log_text.append(fix_emojis(f"⚠️ Не удалось распознать формат данных от сервера"))
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Ошибка обновления: {e}"))

    def start_subscription_updates(self):
        if self.sub_update_worker and self.sub_update_worker.isRunning():
            return
        self.sub_update_worker = SubscriptionUpdateWorker(self.sub_manager)
        self.sub_update_worker.log_signal.connect(self.append_log)
        self.sub_update_worker.progress_signal.connect(
            lambda name, cur, total: self.log_text.append(fix_emojis(f"⏳ {name}: {cur}/{total}")))
        self.sub_update_worker.start()
        self.log_text.append(fix_emojis("📡 Автообновление подписок: АКТИВНО"))

    def _build_routing_rules(self, tunnel_mode: str) -> List[dict]:
        rules = []
        if tunnel_mode == "all_vpn":
            rules.append({
                "type": "field",
                "outboundTag": "proxy",
                "network": "tcp,udp"
            })
        elif tunnel_mode == "ru_direct":
            rules.append({
                "type": "field",
                "ip": ["geoip:ru"],
                "outboundTag": "direct"
            })
            rules.append({
                "type": "field",
                "outboundTag": "proxy",
                "network": "tcp,udp"
            })
        elif tunnel_mode == "blocked_tunnel":
            domains = load_geosite_domains(RU_BLOCKED_PATH, "blocked_tunnel")
            if domains:
                rules.append({
                    "type": "field",
                    "domain": domains,
                    "outboundTag": "proxy"
                })
            rules.append({
                "type": "field",
                "outboundTag": "direct",
                "network": "tcp,udp"
            })
        return rules

    def generate_config(self, key_string):
        try:
            config = json.loads(key_string)
            if "outbounds" in config and "inbounds" in config:
                self.log_text.append(fix_emojis("📄 Загружен JSON конфиг"))
                config["log"] = {"loglevel": self._get_xray_loglevel()}
                if "routing" not in config:
                    config["routing"] = {}
                config["routing"]["rules"] = self._build_routing_rules(self.current_tunnel_mode)
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return True
        except Exception:
            pass
        if key_string.startswith("vless://"):
            return self._parse_vless(key_string)
        elif key_string.startswith("vmess://"):
            return self._parse_vmess(key_string)
        elif key_string.startswith("trojan://"):
            return self._parse_trojan(key_string)
        elif key_string.startswith("ss://"):
            return self._parse_shadowsocks(key_string)
        self.log_text.append(fix_emojis("❌ Неподдерживаемый формат"))
        return False

    def _parse_vless(self, key_string):
        try:
            url_part = key_string[8:]
            if '#' in url_part:
                url_part, _ = url_part.split('#', 1)
            if '?' in url_part:
                addr_part, query_part = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query_part)
            else:
                addr_part = url_part
                params = {}
            get = lambda n, d='': params.get(n, [d])[0]
            allow_insecure_param = get('allowInsecure', '0')
            if allow_insecure_param == '1' or allow_insecure_param.lower() == 'true':
                warning_msg = ("Из соображений безопасности соединений, запуск конфига с параметром "
                               "allowInsecure невозможен. Поддержка этого параметра прекращена. "
                               "Использование allowInsecure подвергает ваш трафик риску перехвата "
                               "и компрометации. Пожалуйста, обратитесь к вашему VPN провайдеру "
                               "для получения конфигурации без этого параметра. "
                               "Ваш провайдер, вероятно, использует устаревшие или небезопасные методы настройки.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            uuid_addr = addr_part.split('@')
            if len(uuid_addr) != 2:
                raise ValueError("Invalid VLESS")
            uuid = uuid_addr[0]
            address, port_str = uuid_addr[1].rsplit(':', 1)
            port = int(port_str)
            sni = get('sni', address)
            pbk = get('pbk')
            sid = get('sid')
            flow = get('flow')
            fp = get('fp', 'chrome')
            alpn = get('alpn', 'h2,http/1.1').split(',')
            net = get('type', 'tcp')
            path = get('path', '/')
            host = get('host', sni)
            security = get('security', 'none')
            if security == 'none':
                warning_msg = ("Из соображений безопасности соединений, запуск конфига с параметром "
                               "security=none невозможен. Пожалуйста, обратитесь к своему VPN провайдеру, "
                               "т.к. в случае данного параметра ваш трафик идет В ОТКРЫТУЮ и ВИДЕН ПРОВАЙДЕРУ. "
                               "В том числе ресурсы, которые вы посещаете. Мы не собираемся делать ошибки VPN Generator "
                               "и подставлять пользователей клиента под статьи из разряда ст.13.53 КоАП РФ за поиск и просмотр чего-либо.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            stream = {"network": net, "security": "reality" if pbk else ("tls" if security == "tls" else "none")}
            if pbk:
                stream["realitySettings"] = {"show": False, "fingerprint": fp, "serverName": sni,
                                              "publicKey": pbk, "shortId": sid, "spiderX": get('spx', '')}
            elif security == "tls":
                stream["tlsSettings"] = {"allowInsecure": False, "fingerprint": fp, "serverName": sni, "alpn": alpn}
            if net == "ws":
                stream["wsSettings"] = {"path": path, "headers": {"Host": host} if host else {}}
            elif net == "grpc":
                stream["grpcSettings"] = {"serviceName": get('serviceName', path)}
            elif net == "tcp" and get('headerType') == 'http':
                stream["tcpSettings"] = {"header": {"type": "http", "request": {
                    "path": [path], "headers": {"Host": [host]}}}}
            outbound = {"vnext": [{"address": address, "port": port, "users": [{
                "id": uuid, "encryption": "none", "flow": flow if flow else None}]}]}
            return self._build_config(outbound, stream, f"{address}:{port} (VLESS)")
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ VLESS ошибка: {e}"))
            return False

    def _parse_vmess(self, key_string):
        try:
            b64 = key_string[8:].strip()
            b64 += '=' * (-len(b64) % 4)
            vmess = json.loads(base64.b64decode(b64).decode('utf-8'))
            allow_insecure = vmess.get('allowInsecure', False)
            if allow_insecure is True or allow_insecure == '1' or allow_insecure == 1 or str(allow_insecure).lower() == 'true':
                warning_msg = ("Из соображений безопасности соединений, запуск конфига с параметром "
                               "allowInsecure невозможен. Поддержка этого параметра прекращена. "
                               "Использование allowInsecure подвергает ваш трафик риску перехвата "
                               "и компрометации. Пожалуйста, обратитесь к вашему VPN провайдеру "
                               "для получения конфигурации без этого параметра.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            address = vmess.get('add', '')
            port = int(vmess.get('port', 443))
            uuid = vmess.get('id', '')
            aid = int(vmess.get('aid', 0))
            net = vmess.get('net', 'tcp')
            sni = vmess.get('sni', '') or vmess.get('host', '') or address
            fp = vmess.get('fp', 'chrome')
            alpn = vmess.get('alpn', 'h2,http/1.1').split(',') if vmess.get('alpn') else ['h2', 'http/1.1']
            stream = {"network": net, "security": "tls" if vmess.get('tls') == 'tls' else "none"}
            if stream["security"] == "tls":
                stream["tlsSettings"] = {
                    "allowInsecure": False,
                    "fingerprint": fp,
                    "serverName": sni,
                    "alpn": alpn
                }
            if net == "ws":
                stream["wsSettings"] = {"path": vmess.get('path', '/'),
                                        "headers": {"Host": vmess.get('host', '') or sni}}
            elif net == "grpc":
                stream["grpcSettings"] = {"serviceName": vmess.get('path', 'grpc')}
            elif net == "tcp" and vmess.get('type') == 'http':
                stream["tcpSettings"] = {"header": {"type": "http", "request": {
                    "path": [vmess.get('path', '/')], "headers": {"Host": [vmess.get('host', address)]}}}}
            outbound = {"vnext": [{"address": address, "port": port, "users": [{
                "id": uuid, "alterId": aid, "security": "auto"}]}]}
            return self._build_config(outbound, stream, f"{address}:{port} (VMESS)")
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ VMESS ошибка: {e}"))
            return False

    def _parse_trojan(self, key_string):
        try:
            url_part = key_string[9:]
            if '#' in url_part:
                url_part, _ = url_part.split('#', 1)
            if '?' in url_part:
                addr_part, query_part = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query_part)
            else:
                addr_part = url_part
                params = {}
            get = lambda n, d='': params.get(n, [d])[0]
            allow_insecure_param = get('allowInsecure', '0')
            if allow_insecure_param == '1':
                warning_msg = ("Из соображений безопасности соединений, запуск конфига с параметром "
                               "allowInsecure невозможен. Поддержка этого параметра прекращена. "
                               "Использование allowInsecure подвергает ваш трафик риску перехвата "
                               "и компрометации. Пожалуйста, обратитесь к вашему VPN провайдеру "
                               "для получения конфигурации без этого параметра.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            auth_part, host_port = addr_part.split('@')
            password = urllib.parse.unquote(auth_part)
            if host_port.startswith('['):
                end = host_port.index(']')
                address = host_port[1:end]
                port_str = host_port[end+2:]
            elif ':' in host_port:
                address, port_str = host_port.rsplit(':', 1)
            else:
                address = host_port
                port_str = '443'
            port = int(port_str)
            sni = get('sni', address)
            fp = get('fp', 'chrome')
            alpn = get('alpn', 'h2,http/1.1').split(',')
            net = get('type', 'tcp')
            path = get('path', '/')
            host = get('host', sni)
            stream = {"network": net, "security": "tls",
                      "tlsSettings": {"allowInsecure": False,
                                      "fingerprint": fp if fp else 'chrome',
                                      "serverName": sni, "alpn": alpn}}
            if net == "ws":
                stream["wsSettings"] = {"path": path, "headers": {"Host": host} if host else {}}
            elif net == "grpc":
                stream["grpcSettings"] = {"serviceName": get('serviceName', path)}
            elif net == "tcp" and get('headerType') == 'http':
                stream["tcpSettings"] = {"header": {"type": "http", "request": {
                    "path": [path] if path else ["/"], "headers": {"Host": [host] if host else [address]}}}}
            outbound = {"servers": [{"address": address, "port": port, "password": password,
                                     "flow": get('flow')}]}
            return self._build_config(outbound, stream, f"{address}:{port} (Trojan)", protocol="trojan")
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Trojan ошибка: {e}"))
            return False

    def _parse_shadowsocks(self, key_string):
        try:
            url_part = key_string[5:]
            if '#' in url_part:
                url_part, _ = url_part.split('#', 1)
            if '?' in url_part:
                addr_part, query_part = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query_part)
            else:
                addr_part = url_part
                params = {}
            address = port = method = password = None
            try:
                part = addr_part
                part += '=' * (-len(part) % 4)
                decoded = base64.b64decode(part).decode('utf-8')
                if '@' in decoded:
                    auth, hp = decoded.rsplit('@', 1)
                    method, password = auth.split(':', 1)
                    if ':' in hp:
                        address, port_str = hp.rsplit(':', 1)
                        port = int(port_str)
                    else:
                        address, port = hp, 80
            except Exception:
                if '@' in addr_part:
                    auth, hp = addr_part.split('@', 1)
                    method, password = auth.split(':', 1)
                    password = urllib.parse.unquote(password)
                    if ':' in hp:
                        address, port_str = hp.rsplit(':', 1)
                        port = int(port_str)
                    else:
                        address, port = hp, 80
            if not all([address, port, method, password]):
                raise ValueError("SS parse failed")
            stream = {"network": "tcp", "security": "none"}
            plugin = params.get('plugin', [None])[0]
            if plugin:
                pparams = dict(p.split('=', 1) for p in plugin.split(';') if '=' in p)
                if pparams.get('obfs') == 'http':
                    stream["tcpSettings"] = {"header": {"type": "http", "request": {
                        "path": [pparams.get('path', '/')],
                        "headers": {"Host": [pparams.get('host', address)]}}}}
            outbound = {"servers": [{"address": address, "port": port, "method": method,
                                     "password": password, "uot": True, "ivCheck": True}]}
            return self._build_config(outbound, stream, f"{address}:{port} (SS-{method})", protocol="shadowsocks")
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Shadowsocks ошибка: {e}"))
            return False

    def _build_config(self, outbound_settings, stream_settings, server_info, protocol="vless"):
        proto_map = {"trojan": "trojan", "shadowsocks": "shadowsocks"}
        outbound_proto = proto_map.get(protocol, "vless")
        routing_rules = self._build_routing_rules(self.current_tunnel_mode)
        config = {
            "log": {"loglevel": self._get_xray_loglevel()},
            "dns": {"servers": ["1.1.1.1", "8.8.8.8", "localhost"]},
            "inbounds": [{"port": LOCAL_PROXY_PORT, "listen": LOCAL_PROXY_HOST, "protocol": "socks",
                          "settings": {"auth": "noauth", "udp": True, "allowTransparent": False},
                          "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic", "fakedns"],
                                       "routeOnly": False, "metadataOnly": False}}],
            "outbounds": [
                {"protocol": outbound_proto, "tag": "proxy", "settings": outbound_settings,
                 "streamSettings": stream_settings, "mux": {"enabled": False, "concurrency": -1}},
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"}
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": routing_rules
            }
        }
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            mode_name = TUNNEL_MODES.get(self.current_tunnel_mode, {}).get('name', 'Неизвестно')
            loglevel = self._get_xray_loglevel()
            self.log_text.append(fix_emojis(f"✅ Конфиг: {server_info} | 🔗 {mode_name} | 📋 loglevel: {loglevel}"))
            return True
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Ошибка сохранения: {e}"))
            return False

    def toggle_proxy(self):
        if self.xray_thread and self.xray_thread.isRunning():
            self.log_text.append(fix_emojis("⏹️ Остановка Xray..."))
            if self.latency_monitor and self.latency_monitor.isRunning():
                self.latency_monitor.stop()
                self.latency_monitor.wait(1000)
            if self.chk_system_proxy.isChecked():
                self.cleanup_system_proxy()
            self.xray_thread.stop()
            self.xray_thread.wait()
            self.update_status(False)
        else:
            if not find_xray_binary():
                reply = QMessageBox.question(
                    self, fix_emojis("Xray-core не найден"),
                    fix_emojis("Xray-core не установлен.\n\n"
                               "Проверить наличие обновлений и скачать сейчас?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.check_for_updates()
                return
            keys = self._get_current_keys_list()
            if self.current_tab == "all":
                idx = self.key_selector_all.currentIndex()
            elif self.current_source_filter == "manual":
                idx = self.key_selector_manual.currentIndex()
            else:
                idx = self.key_selector_sub.currentIndex()
            if idx == -1 or not keys:
                QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Выберите ключ!"))
                return
            key_data = keys[idx]
            key = key_data["key"]
            if not self.generate_config(key):
                return
            self.log_text.append(fix_emojis("🚀 Запуск Xray Core..."))
            self.xray_thread = XrayWorker(CONFIG_PATH)
            self.xray_thread.log_signal.connect(self.append_log)
            self.xray_thread.finished_signal.connect(self.on_xray_finished)
            self.xray_thread.start()
            self.log_text.append(fix_emojis("🔍 Монитор задержки: старт"))
            self.latency_monitor = LatencyMonitor(LOCAL_PROXY_HOST, LOCAL_PROXY_PORT)
            self.latency_monitor.warning_signal.connect(self.append_log)
            self.latency_monitor.status_signal.connect(self.append_status)
            self.latency_monitor.start()
            if self.chk_system_proxy.isChecked():
                if set_system_proxy(True, LOCAL_PROXY_HOST, LOCAL_PROXY_PORT):
                    self.system_proxy_enabled = True
                    self.log_text.append(fix_emojis(f"🔌 Системный прокси: {LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}"))
                else:
                    self.log_text.append(fix_emojis("⚠️ Не удалось настроить системный прокси"))
            self.update_status(True)

    def append_status(self, text: str):
        text = fix_emojis(str(text))  # <-- Замена эмодзи
        log_mode = self._get_log_mode()
        if log_mode == "debug":
            self.log_text.append(f"<span style='color:#888888'>[DEBUG] {text}</span>")
        else:
            self.log_text.append(f"<span style='color:#888888'>{text}</span>")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def on_xray_finished(self):
        if self.latency_monitor and self.latency_monitor.isRunning():
            self.latency_monitor.stop()
            self.latency_monitor.wait(1000)
            self.latency_monitor = None
        if self.system_proxy_enabled:
            self.cleanup_system_proxy()
        self.update_status(False)
        self.log_text.append(fix_emojis("🔚 Процесс Xray завершён"))

    def update_status(self, is_active):
        if is_active:
            self.btn_power.setText(fix_emojis("ВЫКЛЮЧИТЬ"))
            self.btn_power.setStyleSheet(self.btn_power_off_style)
            self.setWindowTitle(fix_emojis("Bobcat Proxy 2.6 pre1 - ВКЛЮЧЕН"))
            self.key_selector_all.setEnabled(False)
            self.key_selector_manual.setEnabled(False)
            self.key_selector_sub.setEnabled(False)
            self.btn_add.setEnabled(False)
            self.key_input.setEnabled(False)
            self.sub_url_input.setEnabled(False)
            self.json_input.setEnabled(False)
            self.btn_import_json.setEnabled(False)
            self.chk_system_proxy.setEnabled(False)
            self.btn_delete_selected.setEnabled(False)
            self.btn_delete_all.setEnabled(False)
            self.btn_subs_manager.setEnabled(False)
            self.btn_settings.setEnabled(False)
            self.btn_check_updates.setEnabled(False)
        else:
            self.btn_power.setText(fix_emojis("ВКЛЮЧИТЬ"))
            self.btn_power.setStyleSheet("""
                QPushButton { background-color:#00F267;color:white;border-radius:75px;
                    font-size:20px;font-weight:bold;border:4px solid #27ae60; }
                QPushButton:hover { background-color:#27ae60; }""")
            self.setWindowTitle(fix_emojis("Bobcat Proxy 2.6 pre2 - Прокси отключен"))
            self.key_selector_all.setEnabled(True)
            self.key_selector_manual.setEnabled(True)
            self.key_selector_sub.setEnabled(True)
            self.btn_add.setEnabled(True)
            self.key_input.setEnabled(True)
            self.sub_url_input.setEnabled(True)
            self.json_input.setEnabled(True)
            self.btn_import_json.setEnabled(True)
            self.chk_system_proxy.setEnabled(True)
            self.btn_subs_manager.setEnabled(True)
            self.btn_settings.setEnabled(True)
            self.btn_check_updates.setEnabled(True)
            has = len(self.sub_manager.keys) > 0
            self.btn_delete_selected.setEnabled(has)
            self.btn_delete_all.setEnabled(has)

# ==================================================================================================
# ЗАПУСК
# ==================================================================================================
if __name__ == "__main__":
    if platform.system() != 'Windows':
        os.environ.setdefault('QT_QPA_PLATFORM', 'wayland;xcb')
        os.environ.setdefault('QT_STYLE_OVERRIDE', 'fusion')
    app = QApplication([])
    app.setFont(QFont("Arial", 10))
    
    # ПРИМЕНИТЬ ПАТЧ ЭМОДЗИ ПЕРЕД СОЗДАНИЕМ ГЛАВНОГО ОКНА
    apply_emoji_fallbacks()
    
    window = XrayClient()
    window.show()
    app.exec()
