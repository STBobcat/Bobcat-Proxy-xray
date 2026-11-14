#Tested on Windows 11 25H2
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
import threading
import hashlib
import struct
from pathlib import Path
from typing import Any, Callable, List, Dict, Optional, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
QHBoxLayout, QPushButton, QTextEdit, QLineEdit,
QComboBox, QLabel, QDialog, QMessageBox, QSplitter,
QGroupBox, QCheckBox, QListWidget, QListWidgetItem,
QTabWidget, QFormLayout, QSpinBox, QDateTimeEdit,
QMenu, QRadioButton, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QAction, QFont, QPalette, QIcon, QPixmap
#==================================================================================================
# ПОДДЕРЖКА ЭМОДЗИ И FALLBACK (ДЛЯ LINUX)
#==================================================================================================
def check_emoji_support() -> bool:
    """Проверяет, поддерживает ли система цветные эмодзи."""
    system = platform.system()
    if system in ('Windows', 'Darwin'):
        return True
    if system == 'Linux':
        try:
            result = subprocess.run(
                ['fc-list', ':color'],
                capture_output=True, text=True, timeout=2
            )
            if 'emoji' in result.stdout.lower() or 'noto' in result.stdout.lower():
                return True
        except Exception:
            pass
    # FreeBSD: тот же fc-list :color, что и на Linux; если fontconfig не установлен — просто False (без падения)
    elif system == 'FreeBSD':
        try:
            if shutil.which('fc-list') is None:
                return False
            result = subprocess.run(
                ['fc-list', ':color'],
                capture_output=True, text=True, timeout=2
            )
            if 'emoji' in result.stdout.lower() or 'noto' in result.stdout.lower():
                return True
        except Exception:
            return False
    return False

EMOJI_SUPPORT = check_emoji_support()

UNICODE_FALLBACKS = {
    "⚙️ ": "⚙ ", "⚙ ": "⚙ ", "📡 ": "≋ ", "🔄 ": "↻ ", "✅ ": "✔ ", "❌ ": "✖ ",
    "🔴 ": "● ", "🟢 ": "● ", "📥 ": "↓ ", "📦 ": "▣ ", "🔍 ": "⌕ ", "🚀 ": "➤ ",
    "🔌 ": "⚡ ", "🔗 ": "⛓ ", "📋 ": "▤ ", "📄 ": "▤ ", "🔑 ": "⚷ ", "📝 ": "✎ ",
    "🌐 ": "⊕ ", "🧪 ": "⚗ ", "💾 ": "▣ ", "🗑️ ": "✕ ", "🗑 ": "✕ ", "➕ ": "＋ ",
    "📊 ": "≡ ", "🕐 ": "⏱ ", "⏸️ ": "⏸ ", "⏸ ": "⏸ ", "⏳ ": "⏳ ", "⏬ ": "⤵ ",
    "⏹️ ": "⏹ ", "⏹ ": "⏹ ", "🔚 ": "⏏ ", "ℹ️ ": "ⓘ ", "ℹ ": "ⓘ ", "✋ ": "✋ ",
    "🏷️ ": "⚲ ", "🏷 ": "⚲ ", "📍 ": "➤ ", "⚠️ ": "⚠ ", "⚠ ": "⚠ ", "📁 ": "▤ ", "🔧 ": "⚒ ",
    "🔐 ": "🔒 ", "🔒 ": "🔒 ", "🌍 ": "⊕ ", "🪟 ": "▢ ", "📤 ": "↑ ", "⏱️ ": "⏱ ",
    "⏱ ": "⏱ ", "🔛 ": "⏻ ", "🔜 ": "⏭ ", "🔝 ": "⏫ ", "🔽 ": "⤓ ", "🔼 ": "⤒ ",
    "🔁 ": "⟳ ", "🔂 ": "⟳ ", "🔃 ": "⟳ ", "🆗 ": "OK ", "🆕 ": "NEW ", "🆙 ": "UP "
}

# Регулярка для полного удаления эмодзи (режим "off")
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF "   # symbols  & pictographs
    "\U0001F600-\U0001F64F "   # emoticons
    "\U0001F680-\U0001F6FF "   # transport  & map
    "\U0001F700-\U0001F77F "   # alchemical
    "\U0001F780-\U0001F7FF "   # geometric extended
    "\U0001F800-\U0001F8FF "   # supplemental arrows
    "\U0001F900-\U0001F9FF "   # supplemental symbols
    "\U0001FA00-\U0001FAFF "   # symbols extended-A
    "\U0001F000-\U0001F02F "   # mahjong
    "\U0001F0A0-\U0001F0FF "   # playing cards
    "\U0001F100-\U0001F1FF "   # enclosed alphanumerics
    "\U0001F1E0-\U0001F1FF "   # flags
    "\U00002600-\U000026FF "   # misc symbols
    "\U00002700-\U000027BF "   # dingbats
    "\U00002B00-\U00002BFF "   # arrows
    "\U00002190-\U000021FF "   # arrows
    "\U00002300-\U000023FF "   # technical
    "\U0000FE00-\U0000FE0F "   # variation selectors
    "\U0001F3FB-\U0001F3FF "   # skin tone modifiers
    "\U0000200D "              # zero-width joiner
    "]+ ",
    flags=re.UNICODE
)

def _get_ui_settings_path() -> str:
    """Вычисляет путь к ui_settings.json без зависимости от порядка объявлений."""
    system = platform.system()
    if system == 'Windows':
        appdata = os.getenv('APPDATA') or os.path.expanduser(r'~\AppData\Roaming')
        return os.path.join(appdata, 'BobcatProxy', 'ui_settings.json')
    # FreeBSD: тот же XDG-путь ~/.config/BobcatProxy; каталог создаёт get_app_data_dir() (os.makedirs)
    xdg_config = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(xdg_config, 'BobcatProxy', 'ui_settings.json')

def _emoji_mode() -> str:
    """Возвращает режим эмодзи: 'auto' или 'off'."""
    try:
        path = _get_ui_settings_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            mode = data.get("emoji_mode ", "auto ")
            if mode in ("auto ", "off "):
                return mode
    except Exception:
        pass
    return "auto "

def fix_emojis(text: str) -> str:
    """
    Обрабатывает эмодзи:
    - auto: если система не поддерживает цветные эмодзи — заменяет на Unicode-фолбэки
    - off:  полностью удаляет все эмодзи
    """
    if not isinstance(text, str):
        text = str(text)
    if _emoji_mode() == "off":
        text = _EMOJI_PATTERN.sub("", text)
        text = re.sub(r"  +", " ", text)
        return text.strip()
    if not EMOJI_SUPPORT:
        for emoji, fallback in UNICODE_FALLBACKS.items():
            text = text.replace(emoji, fallback)
    return text

def apply_emoji_fallbacks():
    mode = _emoji_mode()
    if mode == "auto" and EMOJI_SUPPORT:
        return  # всё поддерживается, патчить нечего
    if mode == "off":
        print("ℹ️ Эмодзи полностью отключены.")
    else:
        print("ℹ️ Цветные эмодзи не поддерживаются системой. Используются Unicode-символы.")

    _orig_label_setText = QLabel.setText
    def _label_setText(self, text):
        _orig_label_setText(self, fix_emojis(str(text)))
    QLabel.setText = _label_setText

    _orig_btn_setText = QPushButton.setText
    def _btn_setText(self, text):
        _orig_btn_setText(self, fix_emojis(str(text)))
    QPushButton.setText = _btn_setText

    _orig_chk_setText = QCheckBox.setText
    def _chk_setText(self, text):
        _orig_chk_setText(self, fix_emojis(str(text)))
    QCheckBox.setText = _chk_setText

    _orig_grp_setTitle = QGroupBox.setTitle
    def _grp_setTitle(self, title):
        _orig_grp_setTitle(self, fix_emojis(str(title)))
    QGroupBox.setTitle = _grp_setTitle

    _orig_win_setTitle = QMainWindow.setWindowTitle
    def _win_setTitle(self, title):
        _orig_win_setTitle(self, fix_emojis(str(title)))
    QMainWindow.setWindowTitle = _win_setTitle

    _orig_item_setText = QListWidgetItem.setText
    def _item_setText(self, text):
        _orig_item_setText(self, fix_emojis(str(text)))
    QListWidgetItem.setText = _item_setText

    _orig_combo_addItem = QComboBox.addItem
    def _combo_addItem(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (fix_emojis(args[0]),) + args[1:]
        _orig_combo_addItem(self, *args, **kwargs)
    QComboBox.addItem = _combo_addItem

    for msg_type in ['information', 'warning', 'question', 'critical']:
        orig_method = getattr(QMessageBox, msg_type)
        def make_patched(method):
            def patched(*args, **kwargs):
                args = list(args)
                if len(args) >= 2:
                    args[1] = fix_emojis(str(args[1]))
                if len(args) >= 3:
                    args[2] = fix_emojis(str(args[2]))
                return method(*args, **kwargs)
            return patched
        setattr(QMessageBox, msg_type, make_patched(orig_method))

#==================================================================================================
# ПОДДЕРЖКА HWID (HARDWARE ID)
#==================================================================================================
def get_machine_id() -> str:
    system = platform.system()
    if system == 'Windows':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Cryptography")
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if machine_guid and machine_guid.strip():
                return machine_guid.strip()
        except Exception:
            pass
        try:
            result = subprocess.run(
                ['wmic', 'csproduct', 'get', 'uuid'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                if len(lines) >= 2:
                    uuid_val = lines[1].strip()
                    if uuid_val:
                        return uuid_val
        except Exception:
            pass
    elif system == 'Linux':
        try:
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id:
                    return machine_id
        except Exception:
            pass
        try:
            with open('/var/lib/dbus/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id:
                    return machine_id
        except Exception:
            pass
        try:
            result = subprocess.run(
                ['hostnamectl', 'status'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if 'Machine ID' in line or 'Machine ID:' in line:
                        parts = line.split(':', 1)
                        if len(parts) >= 2:
                            machine_id = parts[1].strip()
                            if machine_id:
                                return machine_id
        except Exception:
            pass
    # FreeBSD: /etc/machine-id обычно нет — пробуем hostid, SMBIOS UUID, sysctl
    elif system == 'FreeBSD':
        _null_ids = ('', '0', '00000000-0000-0000-0000-000000000000')

        def _fb_cmd(cmd: list) -> str:
            try:
                if shutil.which(cmd[0]) is None:
                    return ''
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    return r.stdout.strip()
            except Exception:
                pass
            return ''

        # FreeBSD: /etc/hostid
        try:
            with open('/etc/hostid', 'r') as f:
                host_id = f.read().strip()
            if host_id.lower() not in _null_ids:
                return host_id
        except Exception:
            pass
        # FreeBSD: SMBIOS UUID
        for cmd in (['kenv', '-q', 'smbios.system.uuid'],
                    ['sysctl', '-n', 'kern.hostuuid'],      # FreeBSD 12+
                    ['sysctl', '-n', 'kern.hostid']):
            value = _fb_cmd(cmd)
            if value.lower() not in _null_ids:
                return value
    elif system == 'Darwin':
        try:
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if 'Hardware UUID' in line:
                        uuid_val = line.split(':', 1)[-1].strip()
                        if uuid_val:
                            return uuid_val
        except Exception:
            pass
    try:
        mac = uuid.getnode()
        if mac & 0xFFFFFFFFFFFF != 0xFFFFFFFFFFFF:
            return f"fallback_{mac:012x}"
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        return f"fallback_{hostname}_{int(time.time())}"
    except Exception:
        return f"fallback_{uuid.uuid4().hex[:16]}"

def hash_to_uuid(hex_string: str) -> str:
    hex_string = hex_string.upper()
    if len(hex_string) < 32:
        hex_string = hex_string.ljust(32, '0')
    elif len(hex_string) > 32:
        hex_string = hex_string[:32]
    return f"{hex_string[:8]}-{hex_string[8:12]}-{hex_string[12:16]}-{hex_string[16:20]}-{hex_string[20:32]}"

# FreeBSD: версия ОС (os-release есть на FreeBSD 13+, иначе uname -sr / platform.platform())
def _get_freebsd_os_version() -> str:
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    value = line.split('=', 1)[1].strip().strip('"')
                    if value:
                        return value
    except Exception:
        pass
    try:
        r = subprocess.run(['uname', '-sr'], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return platform.platform()

def get_hwid() -> str:
    """Генерирует HWID на основе уникальных характеристик устройства."""
    system = platform.system()
    try:
        if system == 'Windows':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            winreg.CloseKey(key)
            os_version = product_name.strip()
        elif system == 'Linux':
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            os_version = line.split('=', 1)[1].strip().strip('"')
                            break
                    else:
                        os_version = platform.platform()
            except Exception:
                os_version = platform.platform()
        elif system == 'FreeBSD':
            # FreeBSD: отдельная ветка определения версии ОС
            os_version = _get_freebsd_os_version()
        else:
            os_version = platform.platform()
    except Exception:
        os_version = platform.platform()

    # FreeBSD: platform.machine() даёт amd64 / arm64 / i386 — все уже покрыты маппингом ниже
    arch = platform.machine().lower()
    if arch in ('x86_64', 'amd64'):
        arch = 'amd64'
    elif arch in ('aarch64', 'arm64'):
        arch = 'arm64'
    elif arch in ('i386', 'i686'):
        arch = 'x86'

    try:
        user = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
    except Exception:
        user = 'unknown'
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = 'unknown'

    machine_id = get_machine_id()
    components = [machine_id, hostname, os_version, arch, user]
    combined = '|'.join(components)
    device_id = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    final_hash = hashlib.sha256(f"bobcat_hwid_{device_id}".encode('utf-8')).hexdigest()
    return hash_to_uuid(final_hash)

def get_hwid_metadata() -> dict:
    """Возвращает метаданные устройства вместе с HWID."""
    system = platform.system()
    try:
        if system == 'Windows':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            winreg.CloseKey(key)
            os_version = product_name.strip()
        elif system == 'Linux':
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            os_version = line.split('=', 1)[1].strip().strip('"')
                            break
                    else:
                        os_version = platform.platform()
            except Exception:
                os_version = platform.platform()
        elif system == 'FreeBSD':
            # FreeBSD: отдельная ветка определения версии ОС
            os_version = _get_freebsd_os_version()
        else:
            os_version = platform.platform()
    except Exception:
        os_version = platform.platform()

    model = platform.machine()
    if platform.system() == 'Windows':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            model = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            winreg.CloseKey(key)
        except Exception:
            model = platform.processor() or model
    elif platform.system() == 'Linux':
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        model = line.split(':', 1)[1].strip()
                        break
        except Exception:
            pass
    # FreeBSD: модель CPU через sysctl hw.model
    elif platform.system() == 'FreeBSD':
        try:
            r = subprocess.run(['sysctl', '-n', 'hw.model'],
                               capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                model = r.stdout.strip()
        except Exception:
            pass
    return {
        'hwid': get_hwid(),
        'device_os': system.lower(),
        'ver_os': os_version,
        'device_model': model,
        'arch': platform.machine()
    }

def get_hwid_short() -> str:
    return get_hwid()[:8]

def get_hwid_full() -> str:
    hwid = get_hwid()
    system = platform.system().lower()
    return f"{hwid}-{system}"

_HWID_CACHE = None

def get_cached_hwid(force_refresh: bool = False) -> str:
    global _HWID_CACHE
    if _HWID_CACHE is None or force_refresh:
        _HWID_CACHE = get_hwid()
    return _HWID_CACHE

def get_cached_hwid_full(force_refresh: bool = False) -> str:
    global _HWID_CACHE
    if _HWID_CACHE is None or force_refresh:
        metadata = get_hwid_metadata()
        _HWID_CACHE = metadata['hwid']
    return _HWID_CACHE

#==================================================================================================
# КОНСТАНТЫ И ПУТИ
#==================================================================================================
def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_app_data_dir() -> str:
    """Возвращает гарантированно созданный каталог данных приложения."""
    if platform.system() == 'Windows':
        appdata = os.environ.get('APPDATA')
        if not appdata:
            appdata = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
        data_dir = os.path.join(appdata, 'BobcatProxy')
    else:
        # FreeBSD: тот же XDG-путь ~/.config/BobcatProxy, что и на Linux (каталог создаётся ниже)
        xdg_config = os.environ.get('XDG_CONFIG_HOME') or os.path.join(
            os.path.expanduser('~'), '.config'
        )
        data_dir = os.path.join(xdg_config, 'BobcatProxy')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.abspath(data_dir)


BASE_DIR = get_base_dir()
DATA_DIR = get_app_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)

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
ICON_DIR = os.path.join(DATA_DIR, "icons")
UPDATE_VIA_PROXY_FILE = os.path.join(DATA_DIR, "update_via_proxy.json")
DOH_SETTINGS_FILE = os.path.join(DATA_DIR, "doh_settings.json")
UI_SETTINGS_FILE = os.path.join(DATA_DIR, "ui_settings.json")
TUNNEL_SETTINGS_FILE = os.path.join(DATA_DIR, "tunnel_settings.json")

for _required_dir in (LOGS_DIR, DOWNLOAD_DIR, ICON_DIR):
    os.makedirs(_required_dir, exist_ok=True)

ICON_LIGHT_URL = "https://raw.githubusercontent.com/STBobcat/Bobcat-Proxy-xray/main/logo_light.png"
ICON_DARK_URL = "https://raw.githubusercontent.com/STBobcat/Bobcat-Proxy-xray/main/logo_dark.png"
HTTP_SERVER_TEST = "https://raw.githubusercontent.com/STBobcat/Bobcat-Proxy-xray/refs/heads/main/checker.txt"
LOCAL_PROXY_HOST = "127.0.0.1"
LOCAL_PROXY_PORT = 25443
DEFAULT_UPDATE_INTERVAL = 3600
MIN_UPDATE_INTERVAL = 300
DEFAULT_UPDATE_VIA_PROXY = False

#==================================================================================================
# ПРЕСЕТЫ USER-AGENT (АКТУАЛЬНЫЕ НА ОКТЯБРЬ 2026)
#==================================================================================================
USERAGENT_PRESETS = {
    "chrome_windows ": {
        "name ": "Chrome 154 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 "
    },
    "chrome_windows_153 ": {
        "name ": "Chrome 153 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 "
    },
    "chrome_windows_152 ": {
        "name ": "Chrome 152 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 "
    },
    "chrome_windows_148 ": {
        "name ": "Chrome 148 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 "
    },
    "firefox_windows ": {
        "name ": "Firefox 157 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0 "
    },
    "firefox_windows_155 ": {
        "name ": "Firefox 155 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0 "
    },
    "firefox_windows_148 ": {
        "name ": "Firefox 148 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0 "
    },
    "edge_windows ": {
        "name ": "Edge 152 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0 "
    },
    "edge_windows_150 ": {
        "name ": "Edge 150 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0 "
    },
    "opera_windows ": {
        "name ": "Opera 135 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 OPR/135.0.0.0 "
    },
    "vivaldi_windows ": {
        "name ": "Vivaldi 8.0 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Vivaldi/8.0.3312.30 "
    },
    "chrome_linux ": {
        "name ": "Chrome 154 (Linux) ",
        "ua ": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 "
    },
    "chrome_linux_152 ": {
        "name ": "Chrome 152 (Linux) ",
        "ua ": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 "
    },
    "chrome_linux_148 ": {
        "name ": "Chrome 148 (Linux) ",
        "ua ": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 "
    },
    "firefox_linux ": {
        "name ": "Firefox 157 (Linux) ",
        "ua ": "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0 "
    },
    "firefox_linux_148 ": {
        "name ": "Firefox 148 (Linux) ",
        "ua ": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0 "
    },
    "safari_mac ": {
        "name ": "Safari 27 (macOS 15) ",
        "ua ": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Safari/605.1.15 "
    },
    "safari_mac_18 ": {
        "name ": "Safari 18 (macOS 14) ",
        "ua ": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15 "
    },
    "chrome_mac ": {
        "name ": "Chrome 154 (macOS) ",
        "ua ": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 "
    },
    "chrome_android ": {
        "name ": "Chrome 154 (Android 16, Pixel 10 Pro) ",
        "ua ": "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36 "
    },
    "chrome_android_samsung ": {
        "name ": "Chrome 154 (Samsung Galaxy S26) ",
        "ua ": "Mozilla/5.0 (Linux; Android 16; SM-S948B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36 "
    },
    "chrome_android_xiaomi ": {
        "name ": "Chrome 154 (Xiaomi 16) ",
        "ua ": "Mozilla/5.0 (Linux; Android 16; 25129PN74C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36 "
    },
    "firefox_android ": {
        "name ": "Firefox 157 (Android 16) ",
        "ua ": "Mozilla/5.0 (Android 16; Mobile; rv:157.0) Gecko/157.0 Firefox/157.0 "
    },
    "safari_ios ": {
        "name ": "Safari 26 (iOS 26, iPhone 17 Pro) ",
        "ua ": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1 "
    },
    "safari_ios_18 ": {
        "name ": "Safari 18 (iOS 18, iPhone 16) ",
        "ua ": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1 "
    },
    "chrome_ios ": {
        "name ": "Chrome 154 (iOS 26, CriOS) ",
        "ua ": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/154.0.0.0 Mobile/15E148 Safari/604.1 "
    },
    "safari_ipad ": {
        "name ": "Safari 26 (iPadOS 26, iPad Pro) ",
        "ua ": "Mozilla/5.0 (iPad; CPU OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1 "
    },
    "edge_android ": {
        "name ": "Edge 154 (Android 16) ",
        "ua ": "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36 EdgA/154.0.0.0 "
    },
    "yandex_windows ": {
        "name ": "Yandex Browser 26 (Windows) ",
        "ua ": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 YaBrowser/26.1.0.0 Safari/537.36 "
    },
    "yandex_android ": {
        "name ": "Yandex Browser 26 (Android 16) ",
        "ua ": "Mozilla/5.0 (Linux; Android 16; Pixel 10 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36 YaBrowser/26.1.0.0 "
    },
    "googlebot ": {
        "name ": "Googlebot (краулер Google) ",
        "ua ": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) "
    },
    "curl ": {
        "name ": "curl (CLI) ",
        "ua ": "curl/8.10.1 "
    },
    "wget ": {
        "name ": "Wget (CLI) ",
        "ua ": "Wget/1.25.0 "
    },
    "custom ": {
        "name ": "Свой User-Agent ",
        "ua ": ""
    }
}

#==================================================================================================
# USER-AGENT ПО УМОЛЧАНИЮ (Chrome 154, Windows)
#==================================================================================================
DEFAULT_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"

def get_recommended_ua_preset() -> str:
    system = platform.system()
    if system == 'Windows':
        return "chrome_windows"
    elif system == 'Darwin':
        return "safari_mac"
    elif system == 'Linux':
        return "chrome_linux"
    elif system == 'FreeBSD':
        # FreeBSD: браузеры представляются как X11/Linux — берём linux-пресет, а не windows
        return "chrome_linux"
    return "chrome_windows"

GEOIP_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat"
GEOSITE_URL = "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/download/202604112225/geosite.dat"
GEOSITE_RU_ONLY_URL = "https://github.com/runetfreedom/russia-blocked-geosite/releases/download/202604112126/geosite-ru-only.dat"
RU_BLOCKED_URL = "https://github.com/runetfreedom/russia-blocked-geosite/releases/download/202604112126/ru-blocked-all.txt"
XRAY_RELEASES_URL = "https://github.com/XTLS/Xray-core/releases"
XRAY_API_URL = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
UPDATE_CHANNELS = {
    "stable": {
        "name ": "Стабильный релиз ",
        "desc ": "Обновляется редко , прошлый релиз вышел более полугода назад  ",
        "api_url ": "https://api.github.com/repos/XTLS/Xray-core/releases/latest "
    },
    "prerelease": {
        "name ": "rolling-release канал ",
        "desc ": "Предназначена для экстренных апдейтов  ",
        "api_url ": "https://api.github.com/repos/XTLS/Xray-core/releases "
    }
}
DEFAULT_UPDATE_CHANNEL = "prerelease"

TUNNEL_MODES = {
    "ru_direct ": {
        "name ": "Российские напрямую ",
        "desc ": "Домены из geosite-ru-only.dat идут напрямую ",
        "file ": GEOSITE_RU_ONLY_PATH,
        "url ": GEOSITE_RU_ONLY_URL
    },
    "blocked_tunnel ": {
        "name ": "Всё напрямую кроме заблокированных ",
        "desc ": "Домены из ru-blocked-all.txt идут в туннель ",
        "file ": RU_BLOCKED_PATH,
        "url ": RU_BLOCKED_URL
    },
    "all_vpn ": {
        "name ": "Всё в VPN ",
        "desc ": "Весь трафик идёт через VPN (все домены и IP через прокси) ",
        "file ": None,
        "url ": None
    }
}

KEY_DISPLAY_MODES = {
    "legacy": "Старый формат . Или просто голая строка с ключем",
    "detailed": "Протокол | домен/IP | транспорт",
    "hashtag": "Хештег / название сервера"
}
DEFAULT_KEY_DISPLAY_MODE = "hashtag"

LOG_MODES = {
    "normal": "Обычный режим (warning)",
    "debug": "Режим отладки (debug)"
}
DEFAULT_LOG_MODE = "normal"

#==================================================================================================
# DNS OVER HTTPS (DoH)
#==================================================================================================
DOH_PROVIDERS = {
    "cloudflare ": {
        "name ": "Cloudflare (1.1.1.1) ",
        "url ": "https://cloudflare-dns.com/dns-query ",
        "ip ": "1.1.1.1 "
    },
    "google ": {
        "name ": "Google (8.8.8.8) ",
        "url ": "https://dns.google/dns-query ",
        "ip ": "8.8.8.8 "
    },
    "quad9 ": {
        "name ": "Quad9 (9.9.9.9) ",
        "url ": "https://dns.quad9.net/dns-query ",
        "ip ": "9.9.9.9 "
    },
    "adguard ": {
        "name ": "AdGuard DNS ",
        "url ": "https://dns.adguard-dns.com/dns-query ",
        "ip ": "94.140.14.14 "
    },
    "opendns ": {
        "name ": "OpenDNS (Cisco) ",
        "url ": "https://doh.opendns.com/dns-query ",
        "ip ": "208.67.222.222 "
    },
    "custom ": {
        "name ": "Свой DoH-сервер ",
        "url ": "",
        "ip ": ""
    }
}

DEFAULT_DOH_SETTINGS = {
    "enabled ": False,
    "provider ": "cloudflare ",
    "custom_url ": "",
    "custom_ip ": "",
    "use_for_subscriptions ": True,
    "use_for_xray_checks ": False,
    "timeout ": 10
}

#==================================================================================================
# НАСТРОЙКИ UI (в т.ч. скрытие рамки окна и режим эмодзи)
#==================================================================================================
def get_ui_settings() -> dict:
    """Загружает настройки интерфейса."""
    default_settings = {
        "key_display_mode ": DEFAULT_KEY_DISPLAY_MODE,
        "log_mode ": DEFAULT_LOG_MODE,
        "hide_window_frame ": False,
        "emoji_mode ": "auto ",           # auto | off
        "auto_select_last_key ": False   # NEW: авто-выбор последнего ручного ключа
    }
    config = load_json_file(UI_SETTINGS_FILE, {})
    if isinstance(config, dict):
        default_settings.update(config)
    return default_settings

def save_ui_settings(settings: dict):
    """Сохраняет настройки интерфейса."""
    current = get_ui_settings()
    current.update(settings)
    save_json_file(UI_SETTINGS_FILE, current)

def apply_window_frame_setting(window: QMainWindow):
    """Применяет настройку скрытия рамки окна."""
    settings = get_ui_settings()
    hide_frame = settings.get("hide_window_frame", False)
    if hide_frame:
        window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    else:
        window.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
    window.show()

#==================================================================================================
# УПРАВЛЕНИЕ USER-AGENT
#==================================================================================================
def load_useragent_settings() -> dict:
    default_settings = {
        "preset": get_recommended_ua_preset(),
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
    with open(USERAGENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_current_useragent() -> str:
    settings = load_useragent_settings()
    if not settings.get("enabled ", True):
        return DEFAULT_USERAGENT
    preset_key = settings.get("preset ", "chrome_windows ")
    if preset_key == "custom ":
        return settings.get("custom_ua ", DEFAULT_USERAGENT)
    preset = USERAGENT_PRESETS.get(preset_key, USERAGENT_PRESETS["chrome_windows "])
    return preset["ua "]

#==================================================================================================
# УПРАВЛЕНИЕ НАСТРОЙКОЙ ОБНОВЛЕНИЯ ЧЕРЕЗ ПРОКСИ
#==================================================================================================
def load_update_via_proxy_settings() -> bool:
    default = DEFAULT_UPDATE_VIA_PROXY
    if os.path.exists(UPDATE_VIA_PROXY_FILE):
        try:
            with open(UPDATE_VIA_PROXY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("enabled", default)
        except Exception:
            pass
    return default

def save_update_via_proxy_settings(enabled: bool):
    with open(UPDATE_VIA_PROXY_FILE, 'w', encoding='utf-8') as f:
        json.dump({"enabled": enabled, "updated": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

def is_proxy_running(parent_window) -> bool:
    if parent_window and hasattr(parent_window, 'xray_thread'):
        if parent_window.xray_thread and parent_window.xray_thread.isRunning():
            return True
    return False

#==================================================================================================
# УПРАВЛЕНИЕ DNS OVER HTTPS (DoH)
#==================================================================================================
def load_doh_settings() -> dict:
    settings = dict(DEFAULT_DOH_SETTINGS)
    if os.path.exists(DOH_SETTINGS_FILE):
        try:
            with open(DOH_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    return settings

def save_doh_settings(settings: dict):
    merged = dict(DEFAULT_DOH_SETTINGS)
    merged.update(settings)
    merged["updated"] = datetime.now().isoformat()
    with open(DOH_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

def get_active_doh_endpoint() -> Optional[Tuple[str, str]]:
    settings = load_doh_settings()
    if not settings.get("enabled ", False):
        return None
    provider = settings.get("provider ", "cloudflare ")
    if provider == "custom ":
        url = settings.get("custom_url ", " ").strip()
        ip = settings.get("custom_ip ", " ").strip()
        if not url:
            return None
        return (url, ip)
    info = DOH_PROVIDERS.get(provider)
    if not info:
        return None
    return (info["url "], info["ip "])

def _parse_dns_answer(packet: bytes, record_type: str) -> Optional[str]:
    try:
        if len(packet) < 12:
            return None
        qdcount = struct.unpack('!H', packet[4:6])[0]
        ancount = struct.unpack('!H', packet[6:8])[0]
        offset = 12
        for _ in range(qdcount):
            while offset < len(packet) and packet[offset] != 0:
                if packet[offset] & 0xC0 == 0xC0:
                    offset += 2
                    break
                offset += packet[offset] + 1
            else:
                offset += 1
            offset += 4
        for _ in range(ancount):
            if offset >= len(packet):
                break
            if packet[offset] & 0xC0 == 0xC0:
                offset += 2
            else:
                while offset < len(packet) and packet[offset] != 0:
                    offset += packet[offset] + 1
                offset += 1
            if offset + 10 > len(packet):
                break
            rtype, rclass, ttl, rdlength = struct.unpack('!HHIH', packet[offset:offset+10])
            offset += 10
            rdata = packet[offset:offset+rdlength]
            offset += rdlength
            if rtype == 1 and len(rdata) == 4:
                return socket.inet_ntoa(rdata)
            elif rtype == 28 and len(rdata) == 16:
                return socket.inet_ntop(socket.AF_INET6, rdata)
    except Exception:
        pass
    return None

def resolve_via_doh(hostname: str, doh_url: str, doh_ip: str,
                    timeout: int = 10, record_type: str = "A") -> Optional[str]:
    try:
        query_id = int.from_bytes(os.urandom(2), 'big')
        flags = 0x0100
        qtype = 1 if record_type == "A" else 28
        qclass = 1
        header = struct.pack('!HHHHHH', query_id, flags, 1, 0, 0, 0)
        qname_parts = hostname.split('.')
        qname = b''.join(bytes([len(p)]) + p.encode('ascii') for p in qname_parts) + b'\x00'
        question = qname + struct.pack('!HH', qtype, qclass)
        dns_query = header + question
        parsed = urllib.parse.urlparse(doh_url)
        if doh_ip:
            doh_request_url = f"{parsed.scheme}://{doh_ip}:{parsed.port or 443}{parsed.path}"
            host_header = parsed.hostname
        else:
            doh_request_url = doh_url
            host_header = parsed.hostname
        req = urllib.request.Request(doh_request_url, data=dns_query, method='POST')
        req.add_header('Content-Type', 'application/dns-message')
        req.add_header('Accept', 'application/dns-message')
        req.add_header('User-Agent', get_current_useragent())
        if host_header:
            req.add_header('Host', host_header)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            answer = response.read()
        return _parse_dns_answer(answer, record_type)
    except Exception as e:
        print(f"⚠️ DoH resolve error для {hostname}: {e}")
        return None

def create_doh_opener(timeout: int = 10):
    endpoint = get_active_doh_endpoint()
    if not endpoint:
        return None
    doh_url, doh_ip = endpoint
    settings = load_doh_settings()
    doh_timeout = settings.get("timeout", 10)
    cache: Dict[str, str] = {}

    def doh_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            socket.inet_aton(host)
            return socket.getaddrinfo(host, port, family, type, proto, flags)
        except OSError:
            pass
        if host in ('localhost', '127.0.0.1', '::1'):
            return socket.getaddrinfo(host, port, family, type, proto, flags)
        if host not in cache:
            ip = resolve_via_doh(host, doh_url, doh_ip, timeout=doh_timeout, record_type="A")
            if not ip:
                ip = resolve_via_doh(host, doh_url, doh_ip, timeout=doh_timeout, record_type="AAAA")
            if ip:
                cache[host] = ip
            else:
                return socket.getaddrinfo(host, port, family, type, proto, flags)
        ip = cache[host]
        try:
            socket.inet_aton(ip)
            fam = socket.AF_INET
        except OSError:
            fam = socket.AF_INET6
        return [(fam, socket.SOCK_STREAM, 6, '', (ip, port))]

    original = socket.getaddrinfo
    socket.getaddrinfo = doh_getaddrinfo

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    opener.addheaders = [('User-Agent', get_current_useragent())]
    return opener, original, doh_getaddrinfo

class DoHContext:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.original = None
        self.patched = None
        self.opener = None

    def __enter__(self):
        result = create_doh_opener(self.timeout)
        if result is None:
            return None
        self.opener, self.original, self.patched = result
        return self.opener

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original is not None:
            socket.getaddrinfo = self.original
        return False

def doh_enabled_for_subscriptions() -> bool:
    settings = load_doh_settings()
    return settings.get("enabled", False) and settings.get("use_for_subscriptions", True)

def doh_enabled_for_checks() -> bool:
    settings = load_doh_settings()
    return settings.get("enabled", False) and settings.get("use_for_xray_checks", False)

#==================================================================================================
# ОПРЕДЕЛЕНИЕ ТЕМЫ СИСТЕМЫ
#==================================================================================================
def get_unix_theme() -> str:
    """Тема для Linux / FreeBSD / прочих Unix: gsettings (если есть) -> палитра Qt."""
    # FreeBSD: gsettings обычно нет (нет GNOME) — тогда единственный рабочий путь это QApplication.palette()
    if shutil.which('gsettings'):
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

# Алиас для обратной совместимости (старое имя)
get_linux_theme = get_unix_theme

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
        # FreeBSD: не Windows-ветка, идёт в get_unix_theme() (gsettings -> палитра Qt)
        return get_unix_theme()

#==================================================================================================
# ЗАГРУЗКА ИКОНОК ПРОГРАММЫ (С КЭШИРОВАНИЕМ)
#==================================================================================================
def ensure_icon_dir():
    os.makedirs(ICON_DIR, exist_ok=True)

def _is_valid_png(path: str) -> bool:
    """Проверяет, что файл — валидный PNG (по сигнатуре)."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 8:
            return False
        with open(path, 'rb') as f:
            return f.read(8) == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False

def get_icon_path(theme: str = None, force_download: bool = False) -> Optional[str]:
    if theme is None:
        theme = get_system_theme()
    ensure_icon_dir()
    icon_name = "logo_light.png" if theme == "light" else "logo_dark.png"
    icon_path = os.path.join(ICON_DIR, icon_name)
    if os.path.exists(icon_path) and not force_download:
        if _is_valid_png(icon_path):
            return icon_path
        try:
            os.remove(icon_path)
        except Exception:
            pass
    url = ICON_LIGHT_URL if theme == "light" else ICON_DARK_URL
    try:
        print(f"⏬ Скачивание иконки для {theme} темы...")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header('User-Agent', get_current_useragent())
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = response.read()
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            print("⚠️ Скачанный файл не является PNG")
            return None
        with open(icon_path, 'wb') as f:
            f.write(data)
        print(f"✅ Иконка сохранена: {icon_path}")
        return icon_path
    except Exception as e:
        print(f"⚠️ Не удалось скачать иконку: {e}")
        return None

def get_icon(theme: str = None) -> Optional[QIcon]:
    icon_path = get_icon_path(theme)
    if icon_path and os.path.exists(icon_path):
        try:
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
        except Exception:
            pass
    return None

def set_window_icon(window: QMainWindow, theme: str = None):
    if theme is None:
        theme = get_system_theme()
    icon = get_icon(theme)
    if icon:
        window.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        return True
    return False

#==================================================================================================
# МОНИТОРИНГ СМЕНЫ ТЕМЫ (для Linux)
#==================================================================================================
class ThemeMonitor(QThread):
    theme_changed = pyqtSignal(str)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.running = True
        self.current_theme = get_system_theme()
        self.daemon = True

    def run(self):
        while self.running:
            new_theme = get_system_theme()
            if new_theme != self.current_theme:
                self.current_theme = new_theme
                self.theme_changed.emit(new_theme)
            for _ in range(5):
                if not self.running:
                    return
                self.msleep(1000)

    def stop(self):
        self.running = False

#==================================================================================================
# УТИЛИТЫ ОБНОВЛЕНИЯ XRAY-CORE
#==================================================================================================
def get_current_xray_version() -> Optional[str]:
    try:
        if os.path.isfile(VERSION_FILE):
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip() or None
    except OSError as exc:
        print(f"⚠️ Не удалось прочитать версию Xray-core: {exc}")
    return None


def save_current_xray_version(version: str):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_path = VERSION_FILE + ".tmp"
    with open(temp_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(str(version).strip())
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, VERSION_FILE)


def _github_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': get_current_useragent() or 'BobcatProxy-Xray-Updater',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def get_latest_xray_release(channel: str = "stable") -> Optional[Dict]:
    try:
        channel = str(channel or '').strip().lower()
        if channel == "stable":
            data = _github_json(
                "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
            )
            return data if isinstance(data, dict) and not data.get('draft') else None

        releases = _github_json(
            "https://api.github.com/repos/XTLS/Xray-core/releases?per_page=30"
        )
        if not isinstance(releases, list):
            return None
        published = [
            item for item in releases
            if isinstance(item, dict) and not item.get('draft', False)
        ]
        prereleases = [item for item in published if item.get('prerelease', False)]
        return (prereleases or published or [None])[0]
    except Exception as exc:
        print(f"⚠️ Ошибка получения релиза через GitHub API: {exc}")
        return None


def system_is_freebsd() -> bool:
    # FreeBSD: явная проверка платформы
    return platform.system() == 'FreeBSD'

# FreeBSD: текст для случая, когда официальных сборок Xray-core нет
FREEBSD_XRAY_HINT = ("Для FreeBSD официальных сборок Xray-core нет. "
                     "Установите pkg install xray-core или соберите вручную.")

def _platform_asset_tokens():
    system = platform.system().lower()
    machine = platform.machine().lower()
    # FreeBSD: в релизах XTLS/Xray-core нет сборок под FreeBSD — пустой кортеж токенов
    if system == 'freebsd':
        return system, ()
    if machine in ('amd64', 'x86_64', 'x64'):
        arch_aliases = ('64', 'x64', 'amd64', 'x86_64')
    elif machine in ('aarch64', 'arm64'):
        arch_aliases = ('arm64', 'aarch64')
    elif machine in ('i386', 'i686', 'x86'):
        arch_aliases = ('32', '386', 'i386', 'i686', 'x86')
    else:
        return system, ()
    if system == 'windows':
        os_aliases = ('windows', 'win')
    elif system == 'linux':
        os_aliases = ('linux',)
    elif system == 'darwin':
        os_aliases = ('macos', 'darwin', 'mac')
    else:
        return system, ()
    return system, (os_aliases, arch_aliases)


def find_asset_for_platform(assets: List[Dict]) -> Optional[Dict]:
    system, token_groups = _platform_asset_tokens()
    # FreeBSD: ассета нет -> None, UpdateChecker покажет FREEBSD_XRAY_HINT
    if system == 'freebsd':
        return None
    if not token_groups:
        return None
    os_aliases, arch_aliases = token_groups
    matches = []
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get('name') or '').lower()
        url = str(asset.get('browser_download_url') or '').strip()
        if not url or not name.endswith('.zip'):
            continue
        if any(x in name for x in ('debug', 'symbol', 'pdb', 'sha256', '.sig', '.asc', '.dgst')):
            continue

        # Имена официальных архивов имеют варианты xray-windows-64.zip,
        # Xray-windows-64.zip и xray-windows-amd64.zip.
        os_match = any(x in name for x in os_aliases)
        arch_match = any(x in name for x in arch_aliases)
        if os_match and arch_match:
            score = 2 if name.startswith('xray-') else 0
            score += 1 if '64' in name else 0
            matches.append((score, asset))
    return max(matches, key=lambda x: x[0])[1] if matches else None


def download_file_with_progress(url: str, destination: str, progress_callback=None, timeout: int = 180) -> bool:
    temp_path = destination + ".part"
    try:
        if not url or not str(url).startswith(('https://', 'http://')):
            raise ValueError("Некорректная ссылка скачивания")
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        req = urllib.request.Request(url, headers={
            'User-Agent': get_current_useragent() or 'BobcatProxy-Updater'
        })
        downloaded = 0
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_size = response.headers.get('Content-Length', '')
            total_size = int(raw_size) if raw_size.isdigit() else 0
            with open(temp_path, 'wb') as output:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        progress_callback(min(99, int(downloaded * 100 / total_size)))
                output.flush()
                os.fsync(output.fileno())
        if downloaded == 0:
            raise OSError("Сервер вернул пустой файл")
        if total_size and downloaded != total_size:
            raise OSError(f"Загрузка неполная: {downloaded}/{total_size} байт")
        os.replace(temp_path, destination)
        if progress_callback:
            progress_callback(100)
        return True
    except Exception as exc:
        print(f"❌ Ошибка загрузки: {exc}")
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        return False


def _safe_extract_zip(zip_path: str, extract_dir: str):
    base = os.path.realpath(extract_dir)
    with zipfile.ZipFile(zip_path, 'r') as archive:
        for member in archive.infolist():
            target = os.path.realpath(os.path.join(base, member.filename))
            if target != base and not target.startswith(base + os.sep):
                raise ValueError(f"Небезопасный путь в ZIP: {member.filename}")
        archive.extractall(base)


def install_xray_from_zip(zip_path: str, target_dir: str) -> bool:
    # FreeBSD: имя бинарника "xray" (не xray.exe) — Windows-ветка не срабатывает; chmod 755 ниже применяется
    binary_name = "xray.exe" if platform.system() == 'Windows' else "xray"
    extract_dir = os.path.join(target_dir, "_xray_update_extract")
    target_path = os.path.join(target_dir, binary_name)
    staged_path = target_path + ".new"
    backup_path = target_path + ".backup"
    had_old_binary = False
    try:
        os.makedirs(target_dir, exist_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.makedirs(extract_dir, exist_ok=True)
        if not zipfile.is_zipfile(zip_path):
            raise zipfile.BadZipFile("Скачанный файл не является ZIP-архивом")
        _safe_extract_zip(zip_path, extract_dir)

        source_path = None
        for root, _dirs, files in os.walk(extract_dir):
            if binary_name in files:
                candidate = os.path.join(root, binary_name)
                if os.path.getsize(candidate) > 1024 * 1024:
                    source_path = candidate
                    break
        if not source_path:
            raise FileNotFoundError(f"В архиве не найден корректный {binary_name}")

        shutil.copy2(source_path, staged_path)
        if os.path.getsize(staged_path) <= 1024 * 1024:
            raise OSError("Размер нового бинарника подозрительно мал")
        if platform.system() != 'Windows':
            os.chmod(staged_path, 0o755)

        if os.path.exists(backup_path):
            os.remove(backup_path)
        had_old_binary = os.path.exists(target_path)
        if had_old_binary:
            os.replace(target_path, backup_path)
        try:
            os.replace(staged_path, target_path)
        except Exception:
            if had_old_binary and os.path.exists(backup_path):
                os.replace(backup_path, target_path)
            raise

        if not os.path.isfile(target_path) or os.path.getsize(target_path) <= 1024 * 1024:
            raise OSError("Проверка установленного файла не пройдена")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return True
    except Exception as exc:
        print(f"❌ Ошибка установки Xray-core: {exc}")
        try:
            if os.path.exists(staged_path):
                os.remove(staged_path)
            if os.path.exists(backup_path) and not os.path.exists(target_path):
                os.replace(backup_path, target_path)
        except OSError as rollback_error:
            print(f"❌ Ошибка отката: {rollback_error}")
        return False
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


#==================================================================================================
# КЛАССЫ ДЛЯ ОБНОВЛЕНИЯ
#==================================================================================================
class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str, str, str, str)
    no_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, channel: str = "stable"):
        super().__init__()
        self.channel = str(channel or "stable").strip()

    def run(self):
        try:
            release = get_latest_xray_release(self.channel)
            if not release:
                self.error.emit(
                    "GitHub не вернул опубликованный релиз Xray-core. "
                    "Проверьте интернет, канал обновлений и доступ к api.github.com."
                )
                return
            tag = str(release.get('tag_name') or '').strip()
            version = tag.lstrip('vV').strip()
            if not version:
                self.error.emit("В ответе GitHub отсутствует tag_name релиза")
                return

            asset = find_asset_for_platform(release.get('assets') or [])
            if not asset and platform.system() == 'FreeBSD':
                # FreeBSD: понятная ошибка вместо «не найден архив»
                self.error.emit(FREEBSD_XRAY_HINT)
                return
            if not asset:
                names = ', '.join(
                    str(a.get('name', '')) for a in release.get('assets', [])
                    if isinstance(a, dict)
                ) or "нет файлов"
                self.error.emit(
                    f"Не найден архив для {platform.system()} {platform.machine()}. "
                    f"Файлы релиза: {names}"
                )
                return
            url = str(asset.get('browser_download_url') or '').strip()
            if not url:
                self.error.emit("У архива отсутствует ссылка скачивания")
                return
            size = int(asset.get('size') or 0)
            size_text = f"{size / (1024 * 1024):.1f} МБ" if size else "размер неизвестен"
            current = (get_current_xray_version() or '').strip().lstrip('vV')
            if current == version:
                self.no_update.emit(version)
            else:
                channel_name = "пре-релиз" if release.get('prerelease') else "стабильная"
                self.update_available.emit(version, tag, url, size_text, channel_name)
        except Exception as exc:
            self.error.emit(f"Ошибка проверки обновлений: {exc}")


# FreeBSD: установка Xray-core через pkg в фоне (чтобы не вешать GUI)
class PkgInstallWorker(QThread):
    status = pyqtSignal(str)
    done = pyqtSignal(bool, str)

    def run(self):
        try:
            ok, message = install_xray_via_pkg(self.status.emit)
        except Exception as exc:
            ok, message = False, f"Ошибка установки через pkg: {exc}"
        self.done.emit(ok, message)


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, download_url: str, version: str):
        super().__init__()
        self.download_url = str(download_url or '').strip()
        self.version = str(version or '').strip()

    def run(self):
        download_path = None
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            filename = os.path.basename(urllib.parse.urlparse(self.download_url).path)
            if not filename.lower().endswith('.zip'):
                filename = f"Xray-{platform.system().lower()}-{platform.machine()}.zip"
            download_path = os.path.join(DOWNLOAD_DIR, filename)

            self.status.emit(fix_emojis(f"Скачивание Xray-core v{self.version}..."))
            if not download_file_with_progress(
                self.download_url, download_path,
                progress_callback=self.progress.emit, timeout=240
            ):
                self.finished.emit(False, fix_emojis(
                    "❌ Не удалось скачать архив. Установленное ядро не изменено."
                ))
                return
            if not zipfile.is_zipfile(download_path):
                raise zipfile.BadZipFile("GitHub вернул файл, который не является ZIP")

            self.status.emit(fix_emojis("Проверка и установка Xray-core..."))
            if not install_xray_from_zip(download_path, DATA_DIR):
                self.finished.emit(False, fix_emojis(
                    "❌ Установка не удалась. Предыдущая версия сохранена."
                ))
                return
            save_current_xray_version(self.version)
            self.progress.emit(100)
            self.finished.emit(True, fix_emojis(
                f"✅ Xray-core v{self.version} успешно установлен"
            ))
        except Exception as exc:
            self.finished.emit(False, fix_emojis(f"❌ Ошибка обновления Xray-core: {exc}"))
        finally:
            if download_path and os.path.exists(download_path):
                try:
                    os.remove(download_path)
                except OSError:
                    pass


#==================================================================================================
# ДИАЛОГ НАСТРОЕК ОБНОВЛЕНИЙ
#==================================================================================================
class UpdateSettingsDialog(QDialog):
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
            radio = QRadioButton(fix_emojis(f"{channel_info['name ']}"))
            radio.setToolTip(fix_emojis(channel_info['desc ']))
            radio.clicked.connect(lambda checked, k=channel_key: self._on_channel_changed(k))
            self.channel_radio[channel_key] = radio
            radio_layout = QVBoxLayout()
            radio_layout.addWidget(radio)
            desc_label = QLabel(fix_emojis(f"   {channel_info['desc ']}"))
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
        current_channel = str(settings.get("channel", DEFAULT_UPDATE_CHANNEL)).strip()
        if current_channel not in self.channel_radio:
            current_channel = DEFAULT_UPDATE_CHANNEL
        if current_channel in self.channel_radio:
            self.channel_radio[current_channel].setChecked(True)
            self._on_channel_changed(current_channel)

    def _on_channel_changed(self, channel_key: str):
        channel_info = UPDATE_CHANNELS.get(channel_key, {})
        self.channel_info.setText(fix_emojis(f"Канал: {channel_info.get('name ', 'Неизвестно')}"))
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
            "channel_name": UPDATE_CHANNELS[selected_channel]["name "],
            "updated": datetime.now().isoformat()
        }
        save_json_file(os.path.join(DATA_DIR, "update_settings.json"), settings)
        channel_name = UPDATE_CHANNELS[selected_channel]["name "]
        QMessageBox.information(
            self,
            fix_emojis("Настройки сохранены"),
            fix_emojis(f"Выбран канал обновлений: {channel_name}")
        )
        self.accept()

#==================================================================================================
# ДИАЛОГ НАСТРОЕК ОБНОВЛЕНИЯ ПОДПИСОК ЧЕРЕЗ VPN
#==================================================================================================
class UpdateViaProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(fix_emojis("🔌 Обновление подписок через VPN"))
        self.setMinimumSize(450, 300)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_settings()
        self._update_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(fix_emojis("Настройка обновления подписок"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 10px;")
        layout.addWidget(title)

        desc = QLabel(
            fix_emojis("Если включено, подписки будут обновляться через активное VPN-соединение.\n\n"
                       "⚠️ ВНИМАНИЕ: Для работы этой опции VPN должен быть ВКЛЮЧЕН!\n"
                       "Если VPN выключен, обновление будет выполняться напрямую.")
        )
        desc.setStyleSheet("color: #888; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.enabled_check = QCheckBox(fix_emojis("✅ Обновлять подписки через VPN"))
        self.enabled_check.setStyleSheet("font-size: 11pt; margin-top: 15px;")
        self.enabled_check.stateChanged.connect(self._update_status)
        layout.addWidget(self.enabled_check)

        status_group = QGroupBox(fix_emojis("Текущий статус"))
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_group)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton(fix_emojis("🧪 Проверить соединение"))
        self.btn_test.clicked.connect(self._test_connection)
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
        enabled = load_update_via_proxy_settings()
        self.enabled_check.setChecked(enabled)
        self._update_status()

    def _update_status(self):
        enabled = self.enabled_check.isChecked()
        proxy_running = is_proxy_running(self.parent_window)
        if enabled:
            if proxy_running:
                status = "✅ VPN включен, подписки будут обновляться через прокси"
                color = "#51cf66"
            else:
                status = "⚠️ VPN выключен! Подписки будут обновляться напрямую"
                color = "#ffa94d"
        else:
            status = "🔌 Опция отключена, подписки обновляются напрямую"
            color = "#888"
        self.status_label.setText(fix_emojis(status))
        self.status_label.setStyleSheet(f"color: {color}; font-size: 9pt; padding: 5px;")

    def _test_connection(self):
        enabled = self.enabled_check.isChecked()
        proxy_running = is_proxy_running(self.parent_window)
        self.btn_test.setEnabled(False)
        self.btn_test.setText(fix_emojis("⏳ Проверка..."))
        QApplication.processEvents()
        try:
            test_url = "https://httpbin.org/ip"
            headers = {'User-Agent': get_current_useragent()}
            if enabled and proxy_running:
                proxy_handler = urllib.request.ProxyHandler({
                    'http': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}',
                    'https': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}'
                })
                opener = urllib.request.build_opener(proxy_handler)
                req = urllib.request.Request(test_url, headers=headers)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with opener.open(req, timeout=15, context=ctx) as response:
                    data = response.read().decode('utf-8')
                QMessageBox.information(
                    self,
                    fix_emojis("✅ Тест пройден"),
                    fix_emojis(f"Соединение через VPN работает!\n\n Ответ сервера:\n{data}")
                )
            else:
                req = urllib.request.Request(test_url, headers=headers)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                    data = response.read().decode('utf-8')
                if enabled and not proxy_running:
                    QMessageBox.information(
                        self,
                        fix_emojis("ℹ️ Информация"),
                        fix_emojis("Соединение прямое (VPN выключен).\n\n"
                                   f"Ответ сервера:\n{data}")
                    )
                else:
                    QMessageBox.information(
                        self,
                        fix_emojis("✅ Тест пройден"),
                        fix_emojis(f"Прямое соединение работает!\n\nОтвет сервера:\n{data}")
                    )
        except Exception as e:
            QMessageBox.warning(
                self,
                fix_emojis("❌ Ошибка"),
                fix_emojis(f"Не удалось установить соединение:\n{str(e)}")
            )
        finally:
            self.btn_test.setEnabled(True)
            self.btn_test.setText(fix_emojis("🧪 Проверить соединение"))

    def _save_settings(self):
        enabled = self.enabled_check.isChecked()
        save_update_via_proxy_settings(enabled)
        proxy_running = is_proxy_running(self.parent_window)
        if enabled and proxy_running:
            msg = "Включено обновление подписок через VPN"
        elif enabled and not proxy_running:
            msg = "Включено обновление через VPN, но VPN выключен! Подписки будут обновляться напрямую"
        else:
            msg = "Обновление подписок через VPN отключено"
        QMessageBox.information(self, fix_emojis("Настройки сохранены"), fix_emojis(msg))
        if self.parent_window:
            self.parent_window.append_log(fix_emojis(f"🔌 {msg}"))
        self.accept()

#==================================================================================================
# ДИАЛОГ НАСТРОЕК DNS OVER HTTPS (DoH)
#==================================================================================================
class DoHSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(fix_emojis("🌐 Настройки DNS over HTTPS (DoH)"))
        self.setMinimumSize(600, 560)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(fix_emojis("DNS over HTTPS (DoH)"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 5px;")
        layout.addWidget(title)

        desc = QLabel(fix_emojis(
            "DoH шифрует DNS-запросы и позволяет обходить DNS-блокировки\n"
            "при загрузке подписок. Работает без VPN."
        ))
        desc.setStyleSheet("color: #888; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.enabled_check = QCheckBox(fix_emojis("✅ Включить DNS over HTTPS"))
        self.enabled_check.setStyleSheet("font-size: 11pt; margin-top: 10px; font-weight: bold;")
        self.enabled_check.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_check)

        provider_group = QGroupBox(fix_emojis("Провайдер DoH"))
        provider_layout = QVBoxLayout(provider_group)
        self.provider_combo = QComboBox()
        for key, info in DOH_PROVIDERS.items():
            self.provider_combo.addItem(fix_emojis(info["name "]), key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        self.custom_url_label = QLabel(fix_emojis("URL DoH-сервера:"))
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText("https://example.com/dns-query")
        self.custom_url_input.textChanged.connect(self._on_custom_changed)
        provider_layout.addWidget(self.custom_url_label)
        provider_layout.addWidget(self.custom_url_input)

        self.custom_ip_label = QLabel(fix_emojis("Bootstrap IP (для резолва самого DoH-хоста):"))
        self.custom_ip_input = QLineEdit()
        self.custom_ip_input.setPlaceholderText("1.1.1.1")
        self.custom_ip_input.textChanged.connect(self._on_custom_changed)
        provider_layout.addWidget(self.custom_ip_label)
        provider_layout.addWidget(self.custom_ip_input)

        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet(
            "color: #666; font-size: 8pt; padding: 8px; "
            "background-color: #f5f5f5; border-radius: 5px;"
        )
        self.preview_label.setWordWrap(True)
        provider_layout.addWidget(self.preview_label)
        layout.addWidget(provider_group)

        scope_group = QGroupBox(fix_emojis("Область применения"))
        scope_layout = QVBoxLayout(scope_group)
        self.sub_check = QCheckBox(fix_emojis("📡 Обновление подписок"))
        self.sub_check.setChecked(True)
        self.sub_check.setToolTip(fix_emojis("Использовать DoH при загрузке подписок"))
        scope_layout.addWidget(self.sub_check)

        self.checks_check = QCheckBox(fix_emojis("🔍 Проверка серверов"))
        self.checks_check.setToolTip(fix_emojis("Использовать DoH при проверке работоспособности серверов"))
        scope_layout.addWidget(self.checks_check)
        layout.addWidget(scope_group)

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel(fix_emojis("⏱️ Таймаут (сек):")))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(3, 60)
        self.timeout_spin.setValue(10)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        self.btn_test = QPushButton(fix_emojis("🧪 Проверить DoH"))
        self.btn_test.clicked.connect(self._test_doh)
        layout.addWidget(self.btn_test)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(fix_emojis("💾 Сохранить"))
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        settings = load_doh_settings()
        self.enabled_check.setChecked(settings.get("enabled", False))
        provider = settings.get("provider", "cloudflare ")
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break
        self.custom_url_input.setText(settings.get("custom_url", ""))
        self.custom_ip_input.setText(settings.get("custom_ip", ""))
        self.sub_check.setChecked(settings.get("use_for_subscriptions", True))
        self.checks_check.setChecked(settings.get("use_for_xray_checks", False))
        self.timeout_spin.setValue(settings.get("timeout", 10))
        self._update_preview()
        self._on_enabled_changed()

    def _on_enabled_changed(self):
        enabled = self.enabled_check.isChecked()
        self.provider_combo.setEnabled(enabled)
        is_custom = self.provider_combo.currentData() == "custom "
        self.custom_url_input.setEnabled(enabled and is_custom)
        self.custom_ip_input.setEnabled(enabled and is_custom)
        self.sub_check.setEnabled(enabled)
        self.checks_check.setEnabled(enabled)
        self.timeout_spin.setEnabled(enabled)
        self.btn_test.setEnabled(enabled)
        self._update_preview()

    def _on_provider_changed(self):
        is_custom = self.provider_combo.currentData() == "custom "
        enabled = self.enabled_check.isChecked()
        self.custom_url_input.setEnabled(enabled and is_custom)
        self.custom_ip_input.setEnabled(enabled and is_custom)
        self._update_preview()

    def _on_custom_changed(self):
        self._update_preview()

    def _update_preview(self):
        provider = self.provider_combo.currentData()
        if provider == "custom ":
            url = self.custom_url_input.text().strip() or "(не задан)"
            ip = self.custom_ip_input.text().strip() or "(не задан)"
        else:
            info = DOH_PROVIDERS.get(provider, {})
            url = info.get("url ", "")
            ip = info.get("ip ", "")
        if not self.enabled_check.isChecked():
            self.preview_label.setText(fix_emojis("🔌 DoH отключён"))
        else:
            self.preview_label.setText(fix_emojis(f"📋 URL: {url}\n🌐 Bootstrap IP: {ip}"))

    def _test_doh(self):
        provider = self.provider_combo.currentData()
        if provider == "custom ":
            url = self.custom_url_input.text().strip()
            ip = self.custom_ip_input.text().strip()
        else:
            info = DOH_PROVIDERS.get(provider, {})
            url = info.get("url ", "")
            ip = info.get("ip ", "")
        if not url:
            QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("URL DoH-сервера не задан!"))
            return
        self.btn_test.setEnabled(False)
        self.btn_test.setText(fix_emojis("⏳ Проверка..."))
        self.status_label.setText(fix_emojis(f"🔄 Резолвинг example.com через {url}..."))
        QApplication.processEvents()
        try:
            start = time.time()
            ip_result = resolve_via_doh("example.com", url, ip,
                                        timeout=self.timeout_spin.value(), record_type="A")
            elapsed = int((time.time() - start) * 1000)
            if ip_result:
                msg = f"✅ DoH работает!\n\nexample.com → {ip_result}\nВремя: {elapsed} мс"
                self.status_label.setText(fix_emojis(msg))
                self.status_label.setStyleSheet("color: #51cf66; font-size: 9pt; padding: 5px;")
                QMessageBox.information(self, fix_emojis("✅ DoH работает"), fix_emojis(msg))
            else:
                msg = "❌ Не удалось получить ответ от DoH-сервера"
                self.status_label.setText(fix_emojis(msg))
                self.status_label.setStyleSheet("color: #ff6b6b; font-size: 9pt; padding: 5px;")
                QMessageBox.warning(self, fix_emojis("❌ Ошибка DoH"), fix_emojis(msg))
        except Exception as e:
            msg = f"❌ Ошибка: {e}"
            self.status_label.setText(fix_emojis(msg))
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 9pt; padding: 5px;")
            QMessageBox.warning(self, fix_emojis("❌ Ошибка DoH"), fix_emojis(msg))
        finally:
            self.btn_test.setEnabled(True)
            self.btn_test.setText(fix_emojis("🧪 Проверить DoH"))

    def _save_settings(self):
        provider = self.provider_combo.currentData()
        settings = {
            "enabled": self.enabled_check.isChecked(),
            "provider": provider,
            "custom_url": self.custom_url_input.text().strip(),
            "custom_ip": self.custom_ip_input.text().strip(),
            "use_for_subscriptions": self.sub_check.isChecked(),
            "use_for_xray_checks": self.checks_check.isChecked(),
            "timeout": self.timeout_spin.value()
        }
        save_doh_settings(settings)
        QMessageBox.information(self, fix_emojis("Настройки сохранены"),
                                fix_emojis("Настройки DoH сохранены"))
        if self.parent_window and hasattr(self.parent_window, '_update_doh_label'):
            self.parent_window._update_doh_label()
        self.accept()

#==================================================================================================
# ДИАЛОГ НАСТРОЕК USER-AGENT
#==================================================================================================
class UserAgentDialog(QDialog):
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
            self.preset_combo.addItem(fix_emojis(preset["name "]), key)
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
        preset_key = settings.get("preset", "chrome_windows ")
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
        self.custom_input.setEnabled(enabled and self.preset_combo.currentData() == "custom ")
        self._update_current_ua()

    def _on_preset_changed(self):
        preset_key = self.preset_combo.currentData()
        self.custom_input.setEnabled(preset_key == "custom " and self.enabled_check.isChecked())
        self._update_preview()
        self._update_current_ua()

    def _on_custom_changed(self):
        self._update_preview()
        self._update_current_ua()

    def _update_preview(self):
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom ":
            ua = self.custom_input.text() or "(пусто)"
        else:
            preset = USERAGENT_PRESETS.get(preset_key, {})
            ua = preset.get("ua ", "(не задан)")
        self.preview_label.setText(fix_emojis(f"📋 Предпросмотр:\n{ua}"))

    def _update_current_ua(self):
        if not self.enabled_check.isChecked():
            self.current_ua_label.setText(fix_emojis(f"🔌 Кастомный User-Agent отключен\n{DEFAULT_USERAGENT}"))
            return
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom ":
            ua = self.custom_input.text().strip()
            if not ua:
                self.current_ua_label.setText(fix_emojis("⚠️ Свой User-Agent не задан!\nБудет использован стандартный."))
                return
            self.current_ua_label.setText(fix_emojis(f"✏️ Свой User-Agent:\n{ua}"))
        else:
            preset = USERAGENT_PRESETS.get(preset_key, {})
            ua = preset.get("ua ", "")
            name = preset.get("name ", "")
            self.current_ua_label.setText(fix_emojis(f"✅ {name}:\n{ua}"))

    def _test_useragent(self):
        ua = get_current_useragent() if self.enabled_check.isChecked() else DEFAULT_USERAGENT
        if self.enabled_check.isChecked():
            preset_key = self.preset_combo.currentData()
            if preset_key == "custom ":
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
            if preset_key == "custom ":
                ua = settings["custom_ua"] or DEFAULT_USERAGENT
                msg = fix_emojis(f"Свой User-Agent сохранён:\n{ua}")
            else:
                preset = USERAGENT_PRESETS.get(preset_key, {})
                msg = fix_emojis(f"User-Agent сохранён: {preset.get('name ', 'Неизвестно')}")
        else:
            msg = fix_emojis("Кастомный User-Agent отключен.\nБудет использован стандартный.")
        QMessageBox.information(self, fix_emojis("Настройки сохранены"), msg)
        self.accept()

#==================================================================================================
# НАСТРОЙКА SSL
#==================================================================================================
def create_ssl_context():
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    except Exception:
        return None

def create_opener_with_ssl_fix():
    context = create_ssl_context()
    if context:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
    else:
        opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', get_current_useragent())]
    return opener

URL_OPENER = create_opener_with_ssl_fix()

#==================================================================================================
# ЗАГРУЗКА ФАЙЛОВ
#==================================================================================================
def download_file(url: str, destination: str, timeout: int = 120) -> bool:
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
    if not mode or mode.get("file ") is None:
        return True
    file_path = mode["file "]
    url = mode["url "]
    if not os.path.exists(file_path):
        print(fix_emojis(f"⏬ Файл не найден: {file_path}. Загрузка..."))
        return download_file(url, file_path)
    print(fix_emojis(f"✅ Файл найден: {file_path}"))
    return True

def find_xray_binary() -> Optional[str]:
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
    # FreeBSD: явные пути (GUI-сессия может запускаться без /usr/local/bin в PATH)
    if platform.system() == 'FreeBSD':
        for freebsd_path in ('/usr/local/bin/xray', '/usr/local/lib/xray/xray', '/usr/bin/xray'):
            if os.path.isfile(freebsd_path) and os.access(freebsd_path, os.X_OK):
                return freebsd_path
    return None

# FreeBSD: установка Xray-core через pkg (ZIP-сборок под FreeBSD нет)
def install_xray_via_pkg(log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """pkg install -y xray-core (запасной вариант: xray). Возвращает (успех, сообщение).
    Не из root: пробует `sudo -n` / `doas -n` (без запроса пароля — у GUI нет терминала)."""
    log = log or (lambda msg: None)
    if platform.system() != 'FreeBSD':
        return False, "Установка через pkg доступна только на FreeBSD."
    pkg_bin = shutil.which('pkg') or ('/usr/sbin/pkg' if os.path.exists('/usr/sbin/pkg') else None)
    if not pkg_bin:
        return False, "Команда pkg не найдена. Установите Xray-core вручную: pkg install xray-core"
    prefix: List[str] = []
    if os.geteuid() != 0:
        if shutil.which('sudo'):
            prefix = ['sudo', '-n']
        elif shutil.which('doas'):
            prefix = ['doas', '-n']
        else:
            return False, ("Нужны права root, а sudo/doas не найдены. "
                           "Выполните в терминале от root: pkg install xray-core")
    last_error = ""
    for pkg_name in ('xray-core', 'xray'):
        cmd = prefix + [pkg_bin, 'install', '-y', pkg_name]
        log(f"▶ {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return False, "Установка через pkg превысила время ожидания (10 минут)."
        except Exception as exc:
            return False, f"Не удалось запустить pkg: {exc}"
        if result.returncode == 0 and find_xray_binary():
            return True, f"Xray-core установлен через pkg ({pkg_name})."
        last_error = (result.stderr or result.stdout or "").strip().splitlines()[-1:] or [""]
        last_error = last_error[0]
    hint = ("Если требуется пароль, выполните в терминале: sudo pkg install xray-core "
            "(или от root: pkg install xray-core).")
    return False, f"Не удалось установить Xray-core через pkg. {last_error}\n{hint}".strip()

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

#==================================================================================================
# УТИЛИТЫ
#==================================================================================================
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
    if '#' in key_string and key_string.startswith(('vless://', 'vmess://', 'trojan://', 'hysteria://', 'hysteria2://')):
        return key_string.split('#')[0].strip()
    return key_string.strip()

# SS-removed: детектор ss://-ссылок нужен только чтобы один раз написать в лог о пропуске
def _contains_ss_link(data: str) -> bool:
    """True, если в сыром ответе (plain / base64 / JSON-список) есть ss://-ссылки. Только для лога о скипе."""
    pattern = re.compile(r'(?im)(?:^|["\'\s,])ss://')
    try:
        if pattern.search(data):
            return True
        stripped = (data or '').strip()
        padded = stripped + '=' * (-len(stripped) % 4)
        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
        return bool(pattern.search(decoded))
    except Exception:
        return False

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
                        domains.append(f"domain:{line[1:]} ")
                    else:
                        domains.append(f"domain:{line} ")
    elif file_path.endswith('.dat'):
        if "ru-only " in file_path or "russia-blocked " in file_path:
            return []
        elif "geosite.dat " in file_path and "Loyalsoldier " in file_path:
            return ["geosite:category-ru ", "geosite:ru "]
        else:
            return ["geosite:ru "]
    return domains

def parse_key_for_display(key_string: str) -> Dict[str, str]:
    result = {"protocol ": "??? ", "address ": "??? ", "transport ": "??? ", "hashtag ": " "}
    try:
        if key_string.startswith('{') and key_string.endswith('}'):
            config = json.loads(key_string)
            outbounds = config.get("outbounds ", [])
            for ob in outbounds:
                if ob.get("tag ") == "proxy ":
                    result["protocol "] = ob.get("protocol ", "unknown ").upper()
                    settings = ob.get("settings ", {})
                    if "vnext " in settings and settings["vnext "]:
                        result["address "] = settings["vnext "][0].get("address ", "??? ")
                    elif "servers " in settings and settings["servers "]:
                        result["address "] = settings["servers "][0].get("address ", "??? ")
                    stream = ob.get("streamSettings ", {})
                    result["transport "] = stream.get("network ", "tcp ").upper()
                    tag = ob.get("tag ", " ")
                    if tag and tag != "proxy ":
                        result["hashtag "] = tag
                    break
            return result

        if key_string.startswith("vless://"):
            result["protocol "] = "VLESS "
            url_part = key_string[8:]
            if '#' in url_part:
                url_part, hashtag = url_part.split('#', 1)
                result["hashtag "] = urllib.parse.unquote(hashtag)
            if '?' in url_part:
                addr_part, query = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query)
            else:
                addr_part, params = url_part, {}
            if '@' in addr_part:
                _, host_port = addr_part.rsplit('@', 1)
                if host_port.startswith('['):
                    end = host_port.index(']')
                    result["address "] = host_port[1:end]
                elif ':' in host_port:
                    result["address "] = host_port.rsplit(':', 1)[0]
            result["transport "] = params.get('type', ['tcp'])[0].upper()
            return result

        if key_string.startswith("vmess://"):
            result["protocol "] = "VMESS "
            b64 = key_string[8:].strip()
            if '#' in b64:
                b64, hashtag = b64.split('#', 1)
                result["hashtag "] = urllib.parse.unquote(hashtag)
            b64 += '=' * (-len(b64) % 4)
            try:
                vmess = json.loads(base64.b64decode(b64).decode('utf-8'))
                result["address "] = vmess.get('add', '???')
                result["transport "] = vmess.get('net', 'tcp').upper()
                if not result["hashtag "]:
                    ps = vmess.get('ps', '')
                    if ps:
                        result["hashtag "] = ps
            except Exception:
                pass
            return result

        if key_string.startswith("trojan://"):
            result["protocol "] = "TROJAN "
            url_part = key_string[9:]
            if '#' in url_part:
                url_part, hashtag = url_part.split('#', 1)
                result["hashtag "] = urllib.parse.unquote(hashtag)
            if '?' in url_part:
                addr_part, query = url_part.split('?', 1)
                params = urllib.parse.parse_qs(query)
            else:
                addr_part, params = url_part, {}
            if '@' in addr_part:
                _, host_port = addr_part.rsplit('@', 1)
                if host_port.startswith('['):
                    end = host_port.index(']')
                    result["address "] = host_port[1:end]
                elif ':' in host_port:
                    result["address "] = host_port.rsplit(':', 1)[0]
            result["transport "] = params.get('type', ['tcp'])[0].upper()
            return result

        # SS-removed: разбор ss:// для отображения удалён

        if key_string.startswith("hysteria:// ") or key_string.startswith("hysteria2://"):
            from urllib.parse import urlparse
            parsed = urlparse(key_string)
            result["protocol "] = "HYSTERIA2 " if key_string.startswith("hysteria2://") else "HYSTERIA "
            result["address "] = parsed.hostname or "??? "
            result["transport "] = "UDP "
            if parsed.username:
                result["hashtag "] = parsed.username[:20]
            return result
    except Exception:
        pass
    return result

#==================================================================================================
# CLASH (YAML) ПОДПИСКИ
#==================================================================================================
_CLASH_SECTION_RE = re.compile(r'^(proxies|proxy-providers)\s*:', re.MULTILINE)

def looks_like_clash(data: str) -> bool:
    """Похоже ли содержимое на Clash-конфиг (есть секция proxies / proxy-providers)."""
    return bool(_CLASH_SECTION_RE.search(data.lstrip('\ufeff')))

# ---------------------------------------------------------------- мини-YAML (запасной парсер)
def _yaml_strip_comment(line: str) -> str:
    out = []
    quote = None
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if quote:
            if quote == '"' and ch == '\\' and i + 1 < n:
                out.append(ch)
                out.append(line[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ('"', "'") and (i == 0 or line[i - 1] in ' \t,[{:'):
            quote = ch
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            break
        out.append(ch)
        i += 1
    return ''.join(out).rstrip()

def _yaml_scalar(s: str):
    s = s.strip()
    if not s:
        return None
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            return json.loads(s)
        except Exception:
            return s[1:-1]
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    low = s.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', '~'):
        return None
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    return s

def _yaml_flow_token(s: str, p: int, stops: str):
    n = len(s)
    while p < n and s[p] in ' \t':
        p += 1
    if p < n and s[p] in '"\'':
        q = s[p]
        j = p + 1
        while j < n:
            if q == '"' and s[j] == '\\':
                j += 2
                continue
            if s[j] == q:
                if q == "'" and j + 1 < n and s[j + 1] == "'":
                    j += 2
                    continue
                break
            j += 1
        return _yaml_scalar(s[p:j + 1]), j + 1
    j = p
    while j < n and s[j] not in stops:
        j += 1
    return _yaml_scalar(s[p:j]), j

def _yaml_flow(s: str, p: int = 0):
    n = len(s)

    def ws(pos):
        while pos < n and s[pos] in ' \t':
            pos += 1
        return pos

    p = ws(p)
    if p < n and s[p] in '{[':
        is_map = s[p] == '{'
        close = '}' if is_map else ']'
        p += 1
        res = {} if is_map else []
        while True:
            p = ws(p)
            if p >= n:
                break
            if s[p] == close:
                p += 1
                break
            if s[p] == ',':
                p += 1
                continue
            if is_map:
                key, p = _yaml_flow_token(s, p, ':,}')
                p = ws(p)
                if p < n and s[p] == ':':
                    val, p = _yaml_flow(s, p + 1)
                else:
                    val = None
                res[str(key)] = val
            else:
                val, p = _yaml_flow(s, p)
                res.append(val)
        return res, p
    return _yaml_flow_token(s, p, ',]}')

def _yaml_value(text: str):
    text = text.strip()
    if text[:1] in ('{', '['):
        return _yaml_flow(text)[0]
    return _yaml_scalar(text)

def _yaml_split_key(text: str):
    if not text or text[0] in '{[':
        return None
    if text[0] in '"\'':
        q = text[0]
        j = 1
        while j < len(text):
            if q == '"' and text[j] == '\\':
                j += 2
                continue
            if text[j] == q:
                break
            j += 1
        end = j + 1
        if end <= len(text) and (end == len(text) or text[end] == ':') and end < len(text) \
                and (end + 1 == len(text) or text[end + 1] in ' \t'):
            return _yaml_scalar(text[:end]), text[end + 1:].strip()
        return None
    m = re.search(r':(?:\s|$)', text)
    if not m:
        return None
    return text[:m.start()].strip(), text[m.end():].strip()

def _yaml_is_item(text: str) -> bool:
    return text == '-' or text.startswith('- ')

def _yaml_block(lines: list, i: int, indent: int):
    if _yaml_is_item(lines[i][1]):
        res = []
        while i < len(lines) and lines[i][0] == indent and _yaml_is_item(lines[i][1]):
            body = lines[i][1][1:]
            stripped = body.lstrip(' ')
            if not stripped:
                if i + 1 < len(lines) and lines[i + 1][0] > indent:
                    val, i = _yaml_block(lines, i + 1, lines[i + 1][0])
                else:
                    val, i = None, i + 1
                res.append(val)
                continue
            inner_indent = indent + 1 + (len(body) - len(stripped))
            if _yaml_split_key(stripped) is not None:
                lines[i] = [inner_indent, stripped]
                val, i = _yaml_block(lines, i, inner_indent)
            else:
                val = _yaml_value(stripped)
                i += 1
            res.append(val)
        return res, i
    res = {}
    while i < len(lines) and lines[i][0] == indent:
        text = lines[i][1]
        if _yaml_is_item(text):
            break
        kv = _yaml_split_key(text)
        i += 1
        if kv is None:
            continue
        key, rest = kv
        if rest == '':
            if i < len(lines) and lines[i][0] > indent:
                val, i = _yaml_block(lines, i, lines[i][0])
            elif i < len(lines) and lines[i][0] == indent and _yaml_is_item(lines[i][1]):
                val, i = _yaml_block(lines, i, indent)
            else:
                val = None
        else:
            val = _yaml_value(rest)
        res[str(key)] = val
    return res, i

def _yaml_mini_load(text: str, wanted=('proxies', 'proxy-providers')) -> dict:
    """Минимальный разбор только нужных секций Clash-конфига (если нет PyYAML)."""
    raw = []
    for line in text.splitlines():
        s = _yaml_strip_comment(line.replace('\t', '  '))
        t = s.strip()
        if not t or t in ('---', '...'):
            continue
        raw.append([len(s) - len(s.lstrip(' ')), t])
    result = {}
    i = 0
    while i < len(raw):
        ind, txt = raw[i]
        kv = _yaml_split_key(txt) if (ind == 0 and not _yaml_is_item(txt)) else None
        if kv is None:
            i += 1
            continue
        key, rest = kv
        j = i + 1
        while j < len(raw) and (raw[j][0] > 0 or _yaml_is_item(raw[j][1])):
            j += 1
        if str(key) in wanted:
            if rest:
                result[str(key)] = _yaml_value(rest)
            elif j > i + 1:
                section = raw[i + 1:j]
                result[str(key)], _ = _yaml_block(section, 0, section[0][0])
        i = j
    return result

def load_clash_yaml(text: str) -> dict:
    text = text.lstrip('\ufeff')
    try:
        import yaml
        doc = yaml.safe_load(text)
        if isinstance(doc, dict):
            return doc
    except Exception:
        pass
    try:
        return _yaml_mini_load(text)
    except Exception:
        return {}

# ---------------------------------------------------------------- Clash proxy -> share-ссылка
def _as_dict(v) -> dict:
    return v if isinstance(v, dict) else {}

def _clash_alpn(v) -> str:
    if isinstance(v, (list, tuple)):
        return ','.join(str(x) for x in v)
    return str(v) if v else ''

def _clash_query(params: dict) -> str:
    return '&'.join(f"{k}={urllib.parse.quote(str(v), safe=',/')}"
                    for k, v in params.items() if v not in (None, '', False))

def _clash_host(server) -> str:
    server = str(server).strip()
    return f"[{server}]" if ':' in server and not server.startswith('[') else server

def _clash_transport(p: dict) -> dict:
    net = str(p.get('network') or 'tcp').lower()
    out = {'type': net}
    if net == 'ws':
        ws = _as_dict(p.get('ws-opts') or p.get('ws-opt'))
        headers = _as_dict(ws.get('headers') or p.get('ws-headers'))
        out['path'] = ws.get('path') or p.get('ws-path') or '/'
        out['host'] = headers.get('Host') or headers.get('host')
    elif net == 'grpc':
        out['serviceName'] = _as_dict(p.get('grpc-opts')).get('grpc-service-name') or ''
    elif net in ('h2', 'http'):
        h2 = _as_dict(p.get('h2-opts') or p.get('http-opts'))
        host = h2.get('host')
        if isinstance(host, (list, tuple)):
            host = host[0] if host else None
        path = h2.get('path')
        if isinstance(path, (list, tuple)):
            path = path[0] if path else None
        out['host'] = host
        out['path'] = path or '/'
    return out

def clash_proxy_to_link(p) -> Optional[str]:
    """Преобразует один элемент `proxies` Clash в ссылку формата, который понимает программа.
    Возвращает None для неподдерживаемых типов/некорректных записей."""
    if not isinstance(p, dict):
        return None
    ptype = str(p.get('type') or '').lower()
    server = p.get('server')
    try:
        port = int(p.get('port'))
    except (TypeError, ValueError):
        return None
    if not server or not port:
        return None
    name = str(p.get('name') or f"{ptype}-{server}")
    tag = urllib.parse.quote(name, safe='')
    host = _clash_host(server)
    sni = p.get('servername') or p.get('sni')
    insecure = '1' if p.get('skip-cert-verify') else None

    if ptype == 'vless':
        uid = p.get('uuid')
        if not uid:
            return None
        reality = _as_dict(p.get('reality-opts'))
        pbk = reality.get('public-key')
        security = 'reality' if pbk else ('tls' if p.get('tls') else 'none')
        params = {
            'encryption': 'none',
            'security': security,
            'sni': sni,
            'fp': p.get('client-fingerprint') or ('chrome' if security != 'none' else None),
            'flow': p.get('flow'),
            'pbk': pbk,
            'sid': reality.get('short-id'),
            'alpn': _clash_alpn(p.get('alpn')),
            'allowInsecure': insecure,
        }
        params.update(_clash_transport(p))
        return f"vless://{uid}@{host}:{port}?{_clash_query(params)}#{tag}"

    if ptype == 'vmess':
        uid = p.get('uuid')
        if not uid:
            return None
        tr = _clash_transport(p)
        obj = {
            'v': '2', 'ps': name, 'add': str(server), 'port': str(port), 'id': str(uid),
            'aid': str(p.get('alterId', 0)), 'scy': p.get('cipher') or 'auto',
            'net': tr['type'], 'type': 'none',
            'host': tr.get('host') or '',
            'path': tr.get('path') or tr.get('serviceName') or '',
            'tls': 'tls' if p.get('tls') else '',
        }
        if sni:
            obj['sni'] = str(sni)
        if p.get('client-fingerprint'):
            obj['fp'] = str(p.get('client-fingerprint'))
        if _clash_alpn(p.get('alpn')):
            obj['alpn'] = _clash_alpn(p.get('alpn'))
        if insecure:
            obj['allowInsecure'] = True
        b64 = base64.b64encode(json.dumps(obj, ensure_ascii=False).encode('utf-8')).decode()
        return f"vmess://{b64}"

    if ptype == 'trojan':
        password = p.get('password')
        if password is None or password == '':
            return None
        params = {
            'security': 'tls',
            'sni': sni,
            'fp': p.get('client-fingerprint'),
            'alpn': _clash_alpn(p.get('alpn')),
            'allowInsecure': insecure,
        }
        params.update(_clash_transport(p))
        return f"trojan://{urllib.parse.quote(str(password), safe='')}@{host}:{port}?{_clash_query(params)}#{tag}"

    # SS-removed: конвертация Clash ss -> ss:// удалена (такие прокси попадают в счётчик skipped)

    if ptype in ('hysteria2', 'hy2'):
        password = p.get('password') or p.get('auth')
        if not password:
            return None
        params = {
            'sni': sni, 'peer': sni,
            'obfs': p.get('obfs'), 'obfs-password': p.get('obfs-password'),
            'insecure': insecure, 'auth': password,
        }
        return f"hysteria2://{urllib.parse.quote(str(password), safe='')}@{host}:{port}?{_clash_query(params)}#{tag}"

    if ptype == 'hysteria':
        auth = p.get('auth-str') or p.get('auth_str') or p.get('auth')
        if not auth:
            return None
        def _mbps(v):
            m = re.match(r'\s*(\d+)', str(v or ''))
            return m.group(1) if m else None
        params = {
            'auth': auth, 'peer': sni, 'obfs': p.get('obfs'),
            'up': _mbps(p.get('up')), 'down': _mbps(p.get('down')),
            'insecure': insecure,
        }
        return f"hysteria://{host}:{port}?{_clash_query(params)}#{tag}"

    return None

def parse_clash_subscription(data: str, fetch, parse_nested, log=None,
                             depth: int = 0, max_depth: int = 2, should_stop=None) -> List[str]:
    """Разбирает Clash-конфиг: inline `proxies` и внешние `proxy-providers` (http / inline).
    fetch(url) -> str          — загрузка провайдера
    parse_nested(text) -> list — разбор содержимого провайдера (Base64/plain/YAML/JSON)
    """
    log = log or (lambda msg: None)
    should_stop = should_stop or (lambda: False)
    doc = load_clash_yaml(data)
    keys: List[str] = []
    skipped: Dict[str, int] = {}

    def add_proxies(items):
        for item in (items if isinstance(items, list) else []):
            link = clash_proxy_to_link(item)
            if link:
                if link not in keys:
                    keys.append(link)
            elif isinstance(item, dict):
                t = str(item.get('type') or '?').lower()
                skipped[t] = skipped.get(t, 0) + 1

    add_proxies(doc.get('proxies'))

    providers = doc.get('proxy-providers')
    if isinstance(providers, dict):
        if depth >= max_depth:
            log("⚠️ Clash: слишком глубокая вложенность proxy-providers, пропущено")
        else:
            for pname, prov in providers.items():
                if should_stop():
                    break
                if not isinstance(prov, dict):
                    continue
                ptype = str(prov.get('type') or 'http').lower()
                if ptype == 'inline':
                    add_proxies(prov.get('payload'))
                    continue
                url = prov.get('url')
                if ptype != 'http' or not url:
                    log(f"⚠️ Clash: провайдер '{str(pname)[:40]}' (type={ptype}) пропущен — нужен type: http с url")
                    continue
                try:
                    log(f"📦 Clash: загрузка провайдера '{str(pname)[:40]}'")
                    body = fetch(str(url))
                    found = parse_nested(body) or []
                except Exception as e:
                    log(f"❌ Clash: провайдер '{str(pname)[:40]}': {e}")
                    continue
                added = 0
                for link in found:
                    if link not in keys:
                        keys.append(link)
                        added += 1
                log(f"✅ Clash: провайдер '{str(pname)[:40]}': {added} ключей")

    if skipped:
        summary = ', '.join(f"{t}: {c}" for t, c in skipped.items())
        log(f"⚠️ Clash: пропущены неподдерживаемые прокси ({summary})")
    return keys

#==================================================================================================
# CLASH PARSER V2 (устойчивый парсер Clash-подписок; v1 выше остаётся как запасной режим)
#==================================================================================================
# ===== SECTION 1: Clash Parser V2 (core) =====
_V2_SUPPORTED_TYPES: Dict[str, str] = {
    'vless': 'vless',
    'vmess': 'vmess',
    'trojan': 'trojan',
    'hysteria': 'hysteria', 'hy': 'hysteria',
    'hysteria2': 'hysteria2', 'hy2': 'hysteria2',
}
_V2_EOL_TYPES = frozenset({'ss', 'shadowsocks'})
_V2_LINK_PREFIXES = ('vless://', 'vmess://', 'trojan://', 'hysteria://', 'hysteria2://')
_V2_MAX_BODY_BYTES = 10 * 1024 * 1024
_V2_SECTION_RE = re.compile(r'^(?:proxies|proxy-providers)\s*:', re.MULTILINE)
_V2_BARE_LIST_RE = re.compile(r'^-\s*(?:\{|"?name"?\s*:|"?type"?\s*:)')


def _v2_new_stats() -> Dict[str, Any]:
    """Создаёт пустой словарь статистики разбора."""
    return {
        'total': 0,
        'converted': {'vless': 0, 'vmess': 0, 'trojan': 0, 'hysteria': 0, 'hysteria2': 0},
        'skipped_eol': 0,
        'skipped_unknown': 0,
        'skipped_error': 0,
        'duplicates': 0,
        'unknown_types': {},
    }


def _v2_format_stats(stats: Dict[str, Any]) -> str:
    """Форматирует статистику одной строкой для log()."""
    conv = stats['converted']
    converted_total = sum(conv.values())
    by_type = ', '.join(f"{t}={c}" for t, c in conv.items())
    line = (f"📊 Clash v2: всего={stats['total']}, конвертировано={converted_total} ({by_type}), "
            f"skipped_eol={stats['skipped_eol']}, skipped_unknown={stats['skipped_unknown']}, "
            f"skipped_error={stats['skipped_error']}")
    if stats['duplicates']:
        line += f", дубликатов={stats['duplicates']}"
    if stats['unknown_types']:
        unknown = ', '.join(f"{t}: {c}" for t, c in stats['unknown_types'].items())
        line += f" [неизвестные типы: {unknown}]"
    return line


def _v2_looks_like_clash(text: str) -> bool:
    """Похож ли текст на Clash (секция proxies / proxy-providers или голый список прокси)."""
    t = text.lstrip('\ufeff').lstrip()
    if not t:
        return False
    return bool(_V2_SECTION_RE.search(t)) or bool(_V2_BARE_LIST_RE.match(t))


def _v2_try_base64(text: str) -> Optional[str]:
    """Пытается декодировать Base64 (обычный и url-safe) в UTF-8; при неудаче возвращает None."""
    compact = re.sub(r'\s+', '', text)
    if len(compact) < 8 or not re.fullmatch(r'[A-Za-z0-9+/_\-]+=*', compact):
        return None
    compact = compact.replace('-', '+').replace('_', '/')
    compact += '=' * (-len(compact) % 4)
    try:
        return base64.b64decode(compact).decode('utf-8-sig')
    except Exception:
        return None


def _v2_label(value: Any, limit: int = 60) -> str:
    """Безопасная короткая подпись для логов (без управляющих символов)."""
    s = re.sub(r'[\x00-\x1f\x7f]+', ' ', str(value if value is not None else '?')).strip()
    return (s[:limit] + '…') if len(s) > limit else (s or '?')


def _v2_url_key(url: str) -> str:
    """Ключ URL для защиты от циклов: схема/хост в нижнем регистре, без #fragment."""
    parsed = urllib.parse.urlparse(url.strip())
    return urllib.parse.urlunparse((parsed.scheme.lower(), parsed.netloc.lower(),
                                    parsed.path, parsed.params, parsed.query, ''))


def _v2_parse_with_stats(data: str,
                         log: Optional[Callable[[str], None]] = None,
                         should_stop: Optional[Callable[[], bool]] = None,
                         max_depth: int = 2,
                         fetch: Optional[Callable[[str], str]] = None) -> Tuple[List[str], Dict[str, Any]]:
    """Ядро разбора: возвращает (ссылки, статистика). Итоговая статистика пишется в log() одной строкой."""
    log = log or (lambda msg: None)
    should_stop = should_stop or (lambda: False)
    fetch = fetch or _v2_fetch_provider
    stats = _v2_new_stats()
    keys: List[str] = []
    seen_ids: set = set()
    seen_urls: set = set()

    def push(link: str, kind: str) -> None:
        ident = link.split('#', 1)[0]
        if ident in seen_ids:
            stats['duplicates'] += 1
            return
        seen_ids.add(ident)
        keys.append(link)
        stats['converted'][kind] += 1

    def add_items(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if should_stop():
                return
            stats['total'] += 1
            if not isinstance(item, dict):
                stats['skipped_unknown'] += 1
                continue
            ptype = _v2_proxy_type(item)
            name = _v2_label(item.get('name') or item.get('Name') or f"{ptype}-{item.get('server', '?')}")
            if ptype in _V2_EOL_TYPES:
                stats['skipped_eol'] += 1
                continue
            kind = _V2_SUPPORTED_TYPES.get(ptype)
            if kind is None:
                stats['skipped_unknown'] += 1
                label = ptype or '?'
                stats['unknown_types'][label] = stats['unknown_types'].get(label, 0) + 1
                continue
            try:
                link = _v2_clash_proxy_to_link(item)
            except Exception as e:  # один битый прокси не должен ронять разбор
                stats['skipped_error'] += 1
                log(f"⚠️ Clash v2: пропущен proxy '{name}' (type={ptype}): {e}")
                continue
            if not link:
                stats['skipped_error'] += 1
                log(f"⚠️ Clash v2: пропущен proxy '{name}' (type={ptype}): не удалось собрать ссылку")
                continue
            push(link, kind)

    def add_link_lines(text: str) -> None:
        for raw in text.splitlines():
            if should_stop():
                return
            line = raw.strip()
            if not line or '://' not in line:
                continue
            low = line.lower()
            stats['total'] += 1
            if low.startswith('ss://'):
                stats['skipped_eol'] += 1
            elif low.startswith(_V2_LINK_PREFIXES):
                push(line, low.split('://', 1)[0])
            else:
                stats['skipped_unknown'] += 1

    def consume_body(body: str, depth: int) -> None:
        text = body.lstrip('\ufeff').strip()
        if not text:
            return
        if _v2_looks_like_clash(text):
            walk(text, depth)
            return
        decoded = _v2_try_base64(text)
        if decoded is not None and _v2_looks_like_clash(decoded):
            walk(decoded, depth)
            return
        for candidate in (decoded, text):
            if candidate and re.search(r'^\s*(?:vless|vmess|trojan|hysteria2?|ss)://', candidate,
                                       re.IGNORECASE | re.MULTILINE):
                add_link_lines(candidate)
                return

    def walk(text: str, depth: int) -> None:
        try:
            doc = _v2_yaml_load(text)
        except Exception as e:
            log(f"⚠️ Clash v2: ошибка разбора YAML: {e}")
            return
        add_items(doc.get('proxies'))
        providers = doc.get('proxy-providers')
        if not isinstance(providers, dict):
            return
        if depth >= max_depth:
            log("⚠️ Clash v2: слишком глубокая вложенность proxy-providers, пропущено")
            return
        for pname, prov in providers.items():
            if should_stop():
                return
            label = _v2_label(pname, 40)
            if not isinstance(prov, dict):
                log(f"⚠️ Clash v2: провайдер '{label}' пропущен — неверный формат")
                continue
            ptype = str(prov.get('type') or 'http').strip().lower()
            if ptype == 'inline':
                add_items(prov.get('payload'))
                continue
            url = str(prov.get('url') or '').strip()
            if ptype != 'http' or not url:
                log(f"⚠️ Clash v2: провайдер '{label}' (type={ptype}) пропущен — нужен type: http с url или inline")
                continue
            url_key = _v2_url_key(url)
            if url_key in seen_urls:
                log(f"🔁 Clash v2: провайдер '{label}' уже загружен, пропущен (защита от циклов)")
                continue
            seen_urls.add(url_key)
            try:
                log(f"📦 Clash v2: загрузка провайдера '{label}'")
                body = fetch(url)
            except Exception as e:
                log(f"❌ Clash v2: провайдер '{label}': {e}")
                continue
            before = len(keys)
            consume_body(body, depth + 1)
            log(f"✅ Clash v2: провайдер '{label}': {len(keys) - before} ключей")

    try:
        walk(str(data or ''), 0)
    except Exception as e:  # последняя линия обороны
        log(f"❌ Clash v2: непредвиденная ошибка: {e}")
    log(_v2_format_stats(stats))
    return keys, stats


def parse_clash_subscription_v2(data: str,
                                log: Optional[Callable[[str], None]] = None,
                                should_stop: Optional[Callable[[], bool]] = None,
                                max_depth: int = 2,
                                fetch: Optional[Callable[[str], str]] = None) -> List[str]:
    """Разбирает «грязную» Clash-подписку (YAML) и возвращает только валидные share-ссылки
    (vless / vmess / trojan / hysteria / hysteria2).

    Обрабатываются секции `proxies` и `proxy-providers` (type: http / inline) с ограничением
    глубины `max_depth` и защитой от циклов по URL. Shadowsocks пропускается (счётчик skipped_eol).
    Ошибка одного прокси не прерывает разбор. Итоговая статистика пишется в log() одной строкой.

    Args:
        data: текст подписки (YAML).
        log: callback для логов (str) — print не используется.
        should_stop: callback прерывания; True — остановить разбор.
        max_depth: максимальная вложенность proxy-providers.
        fetch: необязательная функция загрузки провайдера (по умолчанию _v2_fetch_provider).
    """
    keys, _stats = _v2_parse_with_stats(data, log=log, should_stop=should_stop,
                                        max_depth=max_depth, fetch=fetch)
    return keys


# ===== SECTION 2: Mini-YAML V2 =====
_V2_BLOCK_SCALARS = ('|', '>', '|-', '>-', '|+', '>+')
_V2_KEY_PLAIN_RE = re.compile(r':(?:\s|$)')
_V2_KEY_GLUED_RE = re.compile(r'^([A-Za-z_][\w.\-]*):(?![/:\s])(.+)$')


def _v2_scan_comment(line: str, ignored: set) -> Tuple[int, int]:
    """Ищет начало комментария. Возвращает (позиция_обрезки, позиция_незакрытой_кавычки или -1)."""
    quote = ''
    qpos = -1
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if quote:
            if quote == '"' and ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == quote:
                if quote == "'" and i + 1 < n and line[i + 1] == "'":
                    i += 2
                    continue
                quote = ''
        elif ch in ('"', "'") and i not in ignored and (i == 0 or line[i - 1] in ' \t,[{:'):
            quote = ch
            qpos = i
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            return i, -1
        i += 1
    return n, (qpos if quote else -1)


def _v2_yaml_strip_comment(line: str) -> str:
    """Убирает комментарий `# ...` (только если `#` стоит в начале или после пробела и вне кавычек).
    `#` внутри значения (`tcp#2`, `a#b`) сохраняется. Незакрытая «одинокая» кавычка не ломает разбор."""
    ignored: set = set()
    for _ in range(8):
        cut, unclosed = _v2_scan_comment(line, ignored)
        if unclosed < 0:
            return line[:cut].rstrip()
        ignored.add(unclosed)
    return line.rstrip()


def _v2_yaml_scalar(s: str):
    """Преобразует скаляр YAML: строки в кавычках, true/false, null/~, целые (без ведущих нулей)."""
    s = s.strip()
    if not s:
        return None
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            return json.loads(s, strict=False)
        except ValueError:
            return s[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    low = s.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', '~'):
        return None
    if re.fullmatch(r'-?(?:0|[1-9]\d*)', s):
        return int(s)
    return s


def _v2_yaml_flow_token(s: str, p: int, stops: str):
    """Читает один токен inline-коллекции начиная с позиции p. Возвращает (значение, новая_позиция)."""
    n = len(s)
    while p < n and s[p] in ' \t':
        p += 1
    if p < n and s[p] in ('"', "'"):
        q = s[p]
        j = p + 1
        while j < n:
            if q == '"' and s[j] == '\\':
                j += 2
                continue
            if s[j] == q:
                if q == "'" and j + 1 < n and s[j + 1] == "'":
                    j += 2
                    continue
                break
            j += 1
        if j >= n:  # незакрытая кавычка — берём остаток как есть
            return s[p:].strip(), n
        return _v2_yaml_scalar(s[p:j + 1]), j + 1
    j = p
    while j < n and s[j] not in stops:
        j += 1
    return _v2_yaml_scalar(s[p:j]), j


def _v2_yaml_flow(s: str, p: int = 0, stops: str = ',]}'):
    """Разбирает inline `{...}` / `[...]` (вложенные тоже). Возвращает (значение, новая_позиция).
    Устойчив к незакрытым скобкам и значениям вида `[VIP] US`."""
    n = len(s)

    def ws(pos: int) -> int:
        while pos < n and s[pos] in ' \t':
            pos += 1
        return pos

    p = ws(p)
    if p < n and s[p] in '{[':
        is_map = s[p] == '{'
        close = '}' if is_map else ']'
        p += 1
        res: Any = {} if is_map else []
        while True:
            p = ws(p)
            if p >= n:
                break
            ch = s[p]
            if ch == close:
                p += 1
                break
            if ch == ',':
                p += 1
                continue
            start = p
            if is_map:
                if ch == ']':
                    p += 1
                    continue
                key, p = _v2_yaml_flow_token(s, p, ':,}')
                p = ws(p)
                if p < n and s[p] == ':':
                    vstart = p + 1
                    val, p = _v2_yaml_flow(s, vstart, ',}')
                    if isinstance(val, (dict, list)):
                        q = ws(p)
                        if q < n and s[q] not in ',}':  # «[VIP] US» — это строка, а не список
                            val, p = _v2_yaml_flow_token(s, ws(vstart), ',}')
                    if key is not None:
                        res[str(key)] = val
            else:
                if ch == '}':
                    p += 1
                    continue
                val, p = _v2_yaml_flow(s, p)
                res.append(val)
            if p <= start:
                p = start + 1
        return res, p
    return _v2_yaml_flow_token(s, p, stops)


def _v2_yaml_value(text: str):
    """Значение после `key:` или `- `: inline-коллекция или скаляр."""
    text = text.strip()
    if text[:1] in ('{', '['):
        val, p = _v2_yaml_flow(text)
        if not text[p:].strip():
            return val
    return _v2_yaml_scalar(text)


def _v2_yaml_split_key(text: str):
    """Делит строку `key: value` на (key, value) или возвращает None.
    Учитывает кавычки в ключе, `:` внутри значений/URL (`sni: https://t.me/x`) и `#` внутри значений."""
    if not text or text[0] in '{[':
        return None
    n = len(text)
    if text[0] in ('"', "'"):
        q = text[0]
        j = 1
        while j < n:
            if q == '"' and text[j] == '\\':
                j += 2
                continue
            if text[j] == q:
                if q == "'" and j + 1 < n and text[j + 1] == "'":
                    j += 2
                    continue
                break
            j += 1
        if j >= n:
            return None
        k = j + 1
        while k < n and text[k] in ' \t':
            k += 1
        if k < n and text[k] == ':':
            return _v2_yaml_scalar(text[:j + 1]), text[k + 1:].strip()
        return None
    m = _V2_KEY_PLAIN_RE.search(text)
    if m:
        key = text[:m.start()].strip()
        if not key:
            return None
        return key, text[m.end():].strip()
    m = _V2_KEY_GLUED_RE.match(text)  # `sni:"1"` — двоеточие без пробела
    if m:
        return m.group(1), m.group(2).strip()
    return None


def _v2_yaml_is_item(text: str) -> bool:
    """Элемент списка: `-` или `- ...`."""
    return text == '-' or text.startswith('- ')


def _v2_flow_depth(text: str) -> int:
    """Баланс скобок inline-коллекции вне кавычек (>0 — не закрыта)."""
    depth = 0
    quote = ''
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if quote:
            if quote == '"' and ch == '\\':
                i += 2
                continue
            if ch == quote:
                quote = ''
        elif ch in ('"', "'") and (i == 0 or text[i - 1] in ' \t,[{:'):
            quote = ch
        elif ch in '{[':
            depth += 1
        elif ch in '}]':
            depth -= 1
        i += 1
    return depth


def _v2_yaml_collect_flow(rest: str, lines: list, i: int, limit: int = 200):
    """Склеивает многострочную inline-коллекцию. Возвращает (текст, индекс_следующей_строки)."""
    if rest[:1] not in ('{', '[') or _v2_flow_depth(rest) <= 0:
        return rest, i
    parts = [rest]
    taken = 0
    while i < len(lines) and taken < limit:
        parts.append(lines[i][1])
        i += 1
        taken += 1
        if _v2_flow_depth(' '.join(parts)) <= 0:
            break
    return ' '.join(parts), i


def _v2_yaml_block(lines: list, i: int, indent: int, floor: int = -1):
    """Разбирает блок (словарь или список) начиная со строки i с отступом indent.
    lines — список [отступ, текст]. Возвращает (значение, индекс_следующей_строки).
    Толерантен к «битым» отступам: лишние глубокие строки пропускаются, а строки с отступом
    между floor и indent считаются продолжением текущего словаря."""
    n = len(lines)
    if i >= n:
        return None, i
    if _v2_yaml_is_item(lines[i][1]):
        res_list: list = []
        while i < n:
            ind, text = lines[i]
            if ind < indent:
                break
            if ind > indent:
                i += 1
                continue
            if not _v2_yaml_is_item(text):
                break
            body = text[1:]
            stripped = body.lstrip(' ')
            if not stripped:
                if i + 1 < n and lines[i + 1][0] > indent:
                    val, i = _v2_yaml_block(lines, i + 1, lines[i + 1][0], indent)
                else:
                    val, i = None, i + 1
                res_list.append(val)
                continue
            inner = indent + 1 + (len(body) - len(stripped))
            kv = _v2_yaml_split_key(stripped)
            if _v2_yaml_is_item(stripped) or kv is not None:
                map_indent = inner
                if kv is not None and kv[1] != '' and i + 1 < n:
                    nind, ntext = lines[i + 1]
                    if (nind > indent and nind != inner and not _v2_yaml_is_item(ntext)
                            and _v2_yaml_split_key(ntext) is not None):
                        map_indent = nind  # соседние ключи сдвинуты — подстраиваемся
                elif kv is not None and i + 1 < n:
                    nind, ntext = lines[i + 1]
                    if (indent < nind < inner and not _v2_yaml_is_item(ntext)
                            and _v2_yaml_split_key(ntext) is not None):
                        map_indent = nind
                lines[i] = [map_indent, stripped]
                val, i = _v2_yaml_block(lines, i, map_indent, indent)
            else:
                rest, i = _v2_yaml_collect_flow(stripped, lines, i + 1)
                val = _v2_yaml_value(rest)
            res_list.append(val)
        return res_list, i

    res: dict = {}
    while i < n:
        ind, text = lines[i]
        if ind < indent and not (ind > floor and not _v2_yaml_is_item(text)
                                 and _v2_yaml_split_key(text) is not None):
            break
        if ind > indent:
            i += 1
            continue
        if _v2_yaml_is_item(text):
            break
        kv = _v2_yaml_split_key(text)
        i += 1
        if kv is None:
            continue
        key, rest = kv
        key = '' if key is None else str(key)
        cur = ind
        if rest == '':
            if i < n and lines[i][0] > cur:
                val, i = _v2_yaml_block(lines, i, lines[i][0], cur)
            elif i < n and lines[i][0] == cur and _v2_yaml_is_item(lines[i][1]):
                val, i = _v2_yaml_block(lines, i, cur, floor)
            else:
                val = None
        elif rest in _V2_BLOCK_SCALARS:
            chunk = []
            while i < n and lines[i][0] > cur:
                chunk.append(lines[i][1])
                i += 1
            val = ('\n' if rest.startswith('|') else ' ').join(chunk)
        else:
            rest, i = _v2_yaml_collect_flow(rest, lines, i)
            val = _v2_yaml_value(rest)
        if key:
            res[key] = val
    return res, i


def _v2_yaml_prepare(text: str) -> list:
    """Нормализует текст: BOM, переводы строк, табы → 2 пробела, комментарии, пустые строки, `---`/`...`."""
    text = text.lstrip('\ufeff')
    lines: list = []
    for raw in re.split(r'\r\n|\r|\n', text):
        line = _v2_yaml_strip_comment(raw.replace('\t', '  '))
        stripped = line.strip()
        if not stripped or stripped in ('---', '...'):
            continue
        lines.append([len(line) - len(line.lstrip(' ')), stripped])
    if lines:
        base = min(item[0] for item in lines)
        if base:
            for item in lines:
                item[0] -= base
    return lines


def _v2_yaml_load(text: str, wanted=('proxies', 'proxy-providers')) -> dict:
    """Минимальный устойчивый разбор Clash-конфига: возвращает только секции из wanted,
    остальное (proxy-groups, rules, dns ...) игнорируется. Голый список прокси
    (`- {name: ..}` без ключа) считается секцией `proxies`."""
    lines = _v2_yaml_prepare(text)
    result: dict = {}
    if not lines:
        return result
    n = len(lines)
    i = 0
    while i < n:
        ind, txt = lines[i]
        kv = _v2_yaml_split_key(txt) if (ind == 0 and not _v2_yaml_is_item(txt)) else None
        if kv is None:
            i += 1
            continue
        key, rest = kv
        key = '' if key is None else str(key)
        j = i + 1
        while j < n and (lines[j][0] > 0 or _v2_yaml_is_item(lines[j][1])):
            j += 1
        if key in wanted:
            value: Any = None
            try:
                if rest:
                    if rest[:1] in ('{', '[') and _v2_flow_depth(rest) > 0:
                        rest = rest + ' ' + ' '.join(t for _, t in lines[i + 1:j])
                    value = _v2_yaml_value(rest)
                elif j > i + 1:
                    section = lines[i + 1:j]
                    value, _ = _v2_yaml_block(section, 0, section[0][0])
            except Exception:
                value = None
            if value is not None:
                if key in result and isinstance(result[key], list) and isinstance(value, list):
                    result[key].extend(value)
                elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key].update(value)
                else:
                    result[key] = value
        i = j
    if not any(k in result for k in wanted) and _v2_yaml_is_item(lines[0][1]):
        try:
            value, _ = _v2_yaml_block(lines, 0, lines[0][0])
        except Exception:
            value = None
        if isinstance(value, list) and 'proxies' in wanted:
            result['proxies'] = value
    return result


# ===== SECTION 3: Normalizers =====
_V2_NET_MAP: Dict[str, str] = {
    '': 'tcp', 'tcp': 'tcp', 'raw': 'tcp', 'none': 'tcp',
    'ws': 'ws', 'websocket': 'ws',
    'grpc': 'grpc', 'gun': 'grpc',
    'h2': 'h2', 'h2c': 'h2', 'http': 'h2',
}
_V2_UNSUPPORTED_NETWORKS = frozenset({'xhttp', 'splithttp', 'httpupgrade', 'kcp', 'mkcp', 'quic'})
_V2_FINGERPRINTS = frozenset({'chrome', 'firefox', 'ios', 'qq', 'edge', 'safari', 'random'})
_V2_BAD_SNI_WORDS = frozenset({'', '0', '1', 'off', 'on', 'none', 'null', 'false', 'true', 'no', 'yes',
                               'auto', 'default', 'nil', '-', '~'})
_V2_HOST_RE = re.compile(
    r'^(?=.{4,253}$)(?:[a-z0-9_](?:[a-z0-9_\-]{0,61}[a-z0-9_])?\.)+[a-z][a-z0-9\-]{1,62}$')


def _v2_net_token(net: Any) -> str:
    """Выделяет ведущий токен транспорта из «мусорного» значения (`tcp#2🐊@x`, `tcp%23..`, `tcp?type=tcp`)."""
    s = str(net if net is not None else '').strip().strip('"\'').lower()
    if not s:
        return ''
    s = urllib.parse.unquote(s)
    m = re.match(r'[a-z0-9_\-]+', s)
    return m.group(0) if m else ''


def _v2_normalize_network(net: str) -> str:
    """Приводит `network` к одному из: tcp / ws / grpc / h2 (по умолчанию tcp).
    `tcp#...`, `tcp%23...`, `tcp?type=tcp`, `raw`, `none` → tcp."""
    return _V2_NET_MAP.get(_v2_net_token(net), 'tcp')


def _v2_clean_host(value: Any) -> str:
    """Возвращает валидное DNS-имя для SNI или '' (отбрасывает "1", "off", URL, IP, эмодзи, мусор)."""
    if value is None or isinstance(value, (bool, dict, list)):
        return ''
    s = str(value).strip().strip('"\'')
    if not s:
        return ''
    s = urllib.parse.unquote(s).strip()
    if '://' in s or re.search(r'[\s/@\\]', s):
        return ''
    s = re.split(r'[#?&]', s, maxsplit=1)[0].strip().strip('.').lower()
    if s in _V2_BAD_SNI_WORDS or not s.isascii():
        return ''
    return s if _V2_HOST_RE.match(s) else ''


def _v2_normalize_sni(sni: str, server: str, servername: str) -> str:
    """Выбирает валидный SNI: sni → servername → server. Мусор ("1", "off", пустые, URL-encoded,
    эмодзи, ссылки) отбрасывается. Если подходящего значения нет — пустая строка."""
    for candidate in (sni, servername, server):
        host = _v2_clean_host(candidate)
        if host:
            return host
    return ''


def _v2_normalize_fp(fp: str) -> str:
    """Допустимые fingerprint: chrome/firefox/ios/qq/edge/safari/random; иначе chrome."""
    token = _v2_net_token(fp)
    return token if token in _V2_FINGERPRINTS else 'chrome'


def _v2_quote_fragment(name: str) -> str:
    """URL-кодирование имени для `#fragment` (без управляющих символов, до 200 символов)."""
    clean = re.sub(r'[\x00-\x1f\x7f]+', ' ', str(name if name is not None else '')).strip()
    return urllib.parse.quote(clean[:200], safe='')


# ===== SECTION 4: Converters =====
def _v2_lower_keys(d: Any) -> Any:
    """Рекурсивно приводит ключи словарей к нижнему регистру и `_` → `-` (устойчивость к `Server`, `ws_opts`)."""
    if not isinstance(d, dict):
        return d
    return {str(k).strip().lower().replace('_', '-'): _v2_lower_keys(v) for k, v in d.items()}


def _v2_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _v2_str(v: Any) -> str:
    if v is None or isinstance(v, (bool, dict, list)):
        return ''
    return str(v).strip()


def _v2_truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v or '').strip().lower() in ('1', 'true', 'yes', 'on', 'tls')


def _v2_first(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        v = v[0] if v else ''
    return _v2_str(v)


def _v2_proxy_type(p: dict) -> str:
    """Тип прокси в нижнем регистре."""
    return _v2_str(_v2_lower_keys(p).get('type')).lower()


def _v2_alpn(v: Any) -> str:
    if isinstance(v, (list, tuple)):
        return ','.join(_v2_str(x) for x in v if _v2_str(x))
    return _v2_str(v)


def _v2_query(params: Dict[str, Any]) -> str:
    return '&'.join(f"{k}={urllib.parse.quote(str(v), safe=',/')}"
                    for k, v in params.items() if v not in (None, '', False))


def _v2_server(p: dict) -> str:
    server = _v2_str(p.get('server')).strip('[]')
    if not server or re.search(r'[\s/@#?]', server) or not server.isascii():
        raise ValueError("некорректный server")
    return server


def _v2_host(server: str) -> str:
    return f"[{server}]" if ':' in server else server


def _v2_port(p: dict) -> int:
    raw = p.get('port')
    if raw is None or raw == '':
        raw = p.get('ports')
    m = re.match(r'\s*(\d{1,5})', '' if isinstance(raw, bool) else str(raw))
    if not m or not (1 <= int(m.group(1)) <= 65535):
        raise ValueError("некорректный port")
    return int(m.group(1))


def _v2_network(p: dict) -> str:
    """Нормализованный транспорт прокси; неподдерживаемые (xhttp, kcp, quic ...) → ValueError."""
    token = _v2_net_token(p.get('network'))
    if token in _V2_UNSUPPORTED_NETWORKS:
        raise ValueError(f"транспорт '{token}' не поддерживается")
    return _V2_NET_MAP.get(token, 'tcp')


def _v2_transport(p: dict, net: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {'type': net}
    if net == 'ws':
        ws = _v2_dict(p.get('ws-opts') or p.get('ws-opt'))
        headers = _v2_dict(ws.get('headers') or p.get('ws-headers'))
        out['path'] = _v2_str(ws.get('path') or p.get('ws-path')) or '/'
        out['host'] = _v2_str(headers.get('host'))
    elif net == 'grpc':
        grpc = _v2_dict(p.get('grpc-opts'))
        out['serviceName'] = _v2_str(grpc.get('grpc-service-name') or grpc.get('service-name'))
    elif net == 'h2':
        h2 = _v2_dict(p.get('h2-opts') or p.get('http-opts'))
        out['host'] = _v2_first(h2.get('host'))
        out['path'] = _v2_first(h2.get('path')) or '/'
    return out


def _v2_name(p: dict, ptype: str, server: str) -> str:
    return _v2_str(p.get('name')) or f"{ptype}-{server}"


def _v2_clash_vless_to_link(p: dict) -> Optional[str]:
    """Clash vless → `vless://uuid@host:port?...#name`. Невалидные данные → ValueError."""
    if not isinstance(p, dict):
        return None
    p = _v2_lower_keys(p)
    uid = _v2_str(p.get('uuid') or p.get('id'))
    if not uid:
        raise ValueError("нет uuid")
    server = _v2_server(p)
    port = _v2_port(p)
    net = _v2_network(p)
    reality = _v2_dict(p.get('reality-opts'))
    pbk = _v2_str(reality.get('public-key'))
    security = 'reality' if pbk else ('tls' if _v2_truthy(p.get('tls')) else 'none')
    flow = _v2_str(p.get('flow'))
    if not flow.lower().startswith('xtls-rprx-'):
        flow = ''
    params: Dict[str, Any] = {'encryption': 'none', 'security': security}
    if security != 'none':
        params['sni'] = _v2_normalize_sni(_v2_str(p.get('sni')), server, _v2_str(p.get('servername')))
        params['fp'] = _v2_normalize_fp(_v2_str(p.get('client-fingerprint') or p.get('fingerprint')))
    params['flow'] = flow
    if security == 'reality':
        params['pbk'] = pbk
        params['sid'] = _v2_str(reality.get('short-id'))
    if security != 'none':
        params['alpn'] = _v2_alpn(p.get('alpn'))
        params['allowInsecure'] = '1' if _v2_truthy(p.get('skip-cert-verify')) else ''
    params.update(_v2_transport(p, net))
    tag = _v2_quote_fragment(_v2_name(p, 'vless', server))
    return f"vless://{urllib.parse.quote(uid, safe='')}@{_v2_host(server)}:{port}?{_v2_query(params)}#{tag}"


def _v2_clash_vmess_to_link(p: dict) -> Optional[str]:
    """Clash vmess → `vmess://base64(json)`. Невалидные данные → ValueError."""
    if not isinstance(p, dict):
        return None
    p = _v2_lower_keys(p)
    uid = _v2_str(p.get('uuid') or p.get('id'))
    if not uid:
        raise ValueError("нет uuid")
    server = _v2_server(p)
    port = _v2_port(p)
    net = _v2_network(p)
    tr = _v2_transport(p, net)
    tls = _v2_truthy(p.get('tls'))
    cipher = _v2_str(p.get('cipher')).lower()
    if cipher not in ('auto', 'aes-128-gcm', 'chacha20-poly1305', 'none', 'zero'):
        cipher = 'auto'
    try:
        aid = int(_v2_str(p.get('alterid') if p.get('alterid') is not None else p.get('alter-id')) or 0)
    except ValueError:
        aid = 0
    obj: Dict[str, Any] = {
        'v': '2', 'ps': _v2_name(p, 'vmess', server), 'add': server, 'port': str(port),
        'id': uid, 'aid': str(aid), 'scy': cipher, 'net': net, 'type': 'none',
        'host': tr.get('host') or '',
        'path': tr.get('path') or tr.get('serviceName') or '',
        'tls': 'tls' if tls else '',
    }
    if tls:
        sni = _v2_normalize_sni(_v2_str(p.get('sni')), server, _v2_str(p.get('servername')))
        if sni:
            obj['sni'] = sni
        obj['fp'] = _v2_normalize_fp(_v2_str(p.get('client-fingerprint') or p.get('fingerprint')))
        alpn = _v2_alpn(p.get('alpn'))
        if alpn:
            obj['alpn'] = alpn
        if _v2_truthy(p.get('skip-cert-verify')):
            obj['allowInsecure'] = True
    b64 = base64.b64encode(json.dumps(obj, ensure_ascii=False).encode('utf-8')).decode()
    return f"vmess://{b64}"


def _v2_clash_trojan_to_link(p: dict) -> Optional[str]:
    """Clash trojan → `trojan://password@host:port?...#name`. Невалидные данные → ValueError."""
    if not isinstance(p, dict):
        return None
    p = _v2_lower_keys(p)
    password = _v2_str(p.get('password'))
    if not password:
        raise ValueError("нет password")
    server = _v2_server(p)
    port = _v2_port(p)
    net = _v2_network(p)
    fp_src = _v2_str(p.get('client-fingerprint') or p.get('fingerprint'))
    params: Dict[str, Any] = {
        'security': 'tls',
        'sni': _v2_normalize_sni(_v2_str(p.get('sni')), server, _v2_str(p.get('servername'))),
        'fp': _v2_normalize_fp(fp_src) if fp_src else '',
        'alpn': _v2_alpn(p.get('alpn')),
        'allowInsecure': '1' if _v2_truthy(p.get('skip-cert-verify')) else '',
    }
    params.update(_v2_transport(p, net))
    tag = _v2_quote_fragment(_v2_name(p, 'trojan', server))
    return f"trojan://{urllib.parse.quote(password, safe='')}@{_v2_host(server)}:{port}?{_v2_query(params)}#{tag}"


def _v2_mbps(v: Any) -> str:
    m = re.match(r'\s*(\d+)', '' if v is None or isinstance(v, bool) else str(v))
    return m.group(1) if m else ''


def _v2_clash_hysteria_to_link(p: dict) -> Optional[str]:
    """Clash hysteria (v1) → `hysteria://host:port?auth=..&peer=..&up=..&down=..#name`."""
    if not isinstance(p, dict):
        return None
    p = _v2_lower_keys(p)
    auth = _v2_str(p.get('auth-str') or p.get('auth') or p.get('password'))
    if not auth:
        raise ValueError("нет auth-str")
    server = _v2_server(p)
    port = _v2_port(p)
    sni = _v2_normalize_sni(_v2_str(p.get('sni')), server, _v2_str(p.get('servername')))
    params: Dict[str, Any] = {
        'auth': auth, 'peer': sni,
        'obfs': _v2_str(p.get('obfs')), 'obfs-password': _v2_str(p.get('obfs-password')),
        'up': _v2_mbps(p.get('up')), 'down': _v2_mbps(p.get('down')),
        'insecure': '1' if _v2_truthy(p.get('skip-cert-verify')) else '',
    }
    tag = _v2_quote_fragment(_v2_name(p, 'hysteria', server))
    return f"hysteria://{_v2_host(server)}:{port}?{_v2_query(params)}#{tag}"


def _v2_clash_hysteria2_to_link(p: dict) -> Optional[str]:
    """Clash hysteria2 → `hysteria2://password@host:port?sni=..&peer=..#name`.
    Клиент берёт auth из userinfo, а SNI — из `peer`/`sni` (по умолчанию — хост)."""
    if not isinstance(p, dict):
        return None
    p = _v2_lower_keys(p)
    password = _v2_str(p.get('password') or p.get('auth') or p.get('auth-str'))
    if not password:
        raise ValueError("нет password")
    server = _v2_server(p)
    port = _v2_port(p)
    sni = _v2_normalize_sni(_v2_str(p.get('sni')), server, _v2_str(p.get('servername')))
    params: Dict[str, Any] = {
        'sni': sni, 'peer': sni,
        'obfs': _v2_str(p.get('obfs')), 'obfs-password': _v2_str(p.get('obfs-password')),
        'insecure': '1' if _v2_truthy(p.get('skip-cert-verify')) else '',
    }
    tag = _v2_quote_fragment(_v2_name(p, 'hysteria2', server))
    userinfo = urllib.parse.quote(password, safe="-._~!$&'()*+,;=")
    return f"hysteria2://{userinfo}@{_v2_host(server)}:{port}?{_v2_query(params)}#{tag}"


def _v2_clash_proxy_to_link(p: dict) -> Optional[str]:
    """Диспетчер Clash proxy → share-ссылка (vless / vmess / trojan / hysteria / hysteria2).
    Для ss / shadowsocks и неизвестных типов возвращает None (это НЕ ошибка).
    Для некорректных данных конвертеры бросают ValueError с причиной."""
    if not isinstance(p, dict):
        return None
    ptype = _v2_proxy_type(p)
    if ptype in _V2_EOL_TYPES:
        return None
    kind = _V2_SUPPORTED_TYPES.get(ptype)
    if kind == 'vless':
        return _v2_clash_vless_to_link(p)
    if kind == 'vmess':
        return _v2_clash_vmess_to_link(p)
    if kind == 'trojan':
        return _v2_clash_trojan_to_link(p)
    if kind == 'hysteria':
        return _v2_clash_hysteria_to_link(p)
    if kind == 'hysteria2':
        return _v2_clash_hysteria2_to_link(p)
    return None


# ===== SECTION 5: Provider fetch =====
def _v2_user_agent() -> str:
    """User-Agent проекта (get_current_useragent), с запасным значением, если функция недоступна."""
    try:
        ua = get_current_useragent()
        if ua:
            return str(ua)
    except Exception:
        pass
    return f"BobcatProxy/3.0 ({platform.system()})"


def _v2_fetch_provider(url: str, timeout: int = 30) -> str:
    """Загружает внешний proxy-provider через urllib (SSL-фикс как в проекте: CERT_NONE).
    DoH не используется (упрощённо). Размер ответа ограничен 10 МБ."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError(f"некорректный URL провайдера: {url[:80]}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request(url, headers={'User-Agent': _v2_user_agent(), 'Accept': '*/*'})
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read(_V2_MAX_BODY_BYTES + 1)
    if len(raw) > _V2_MAX_BODY_BYTES:
        raise ValueError("ответ провайдера слишком большой (>10 МБ)")
    return raw.decode('utf-8-sig', errors='replace')


# ===== SECTION 6: Integration into SubscriptionUpdateWorker =====
CLASH_PARSER_MODES = ("v2", "v1")
CLASH_PARSER_DEFAULT_MODE = "v2"


def get_clash_parser_mode() -> str:
    """Режим парсера Clash из ui_settings: "v2" (по умолчанию) или "v1"."""
    try:
        mode = str(get_ui_settings().get("clash_parser_mode", CLASH_PARSER_DEFAULT_MODE)).strip().lower()
    except Exception:
        return CLASH_PARSER_DEFAULT_MODE
    return mode if mode in CLASH_PARSER_MODES else CLASH_PARSER_DEFAULT_MODE


def set_clash_parser_mode(mode: str) -> None:
    """Сохраняет режим парсера Clash ("v1" | "v2") в ui_settings."""
    mode = str(mode).strip().lower()
    if mode not in CLASH_PARSER_MODES:
        mode = CLASH_PARSER_DEFAULT_MODE
    save_ui_settings({"clash_parser_mode": mode})


# ===== SECTION 8: ClashParserSettingsDialog =====
class ClashParserSettingsDialog(QDialog):
    """Диалог выбора парсера Clash-подписок: v2 (устойчивый, по умолчанию) или v1 (прежний)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(fix_emojis("🧩 Парсер Clash"))
        self.setMinimumSize(480, 330)
        self.setFont(QFont("Arial"))
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel(fix_emojis("Парсер Clash-подписок"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 10px;")
        layout.addWidget(title)

        desc = QLabel(fix_emojis(
            "Определяет, как разбираются подписки в формате Clash (YAML).\n"
            "Устаревшие типы прокси (ss) в обоих режимах пропускаются."))
        desc.setStyleSheet("color: #888; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        group = QGroupBox(fix_emojis("Режим"))
        group_layout = QVBoxLayout(group)
        self.radio_v2 = QRadioButton(fix_emojis("✨ v2 — устойчивый к «грязным» подписках (рекомендуется)"))
        self.radio_v1 = QRadioButton(fix_emojis("🕰️ v1 — прежний парсер"))
        group_layout.addWidget(self.radio_v2)
        group_layout.addWidget(self.radio_v1)
        layout.addWidget(group)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.radio_v2.toggled.connect(self._update_status)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(fix_emojis("💾 Сохранить"))
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _load_settings(self) -> None:
        mode = get_clash_parser_mode()
        self.radio_v2.setChecked(mode == "v2")
        self.radio_v1.setChecked(mode == "v1")
        self._update_status()

    def selected_mode(self) -> str:
        """Выбранный режим: "v2" или "v1"."""
        return "v2" if self.radio_v2.isChecked() else "v1"

    def _update_status(self, *_args) -> None:
        if self.selected_mode() == "v2":
            text = "✅ v2: собственный мини-YAML парсер, нормализация sni/network/fp, статистика в логе."
        else:
            text = "ℹ️ v1: прежний парсер без дополнительной нормализации полей."
        self.status_label.setText(fix_emojis(text))

    def _save_settings(self) -> None:
        set_clash_parser_mode(self.selected_mode())
        self.accept()


#==================================================================================================
# МЕНЕДЖЕР ПОДПИСОК
#==================================================================================================
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

    def add_subscription(self, url: str, interval: int = DEFAULT_UPDATE_INTERVAL, send_hwid: bool = True) -> dict:
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
            "key_count": 0,
            "send_hwid": send_hwid
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

    # НОВОЕ: Обновление статусов ключей после проверки
    def update_keys_check_status(self, working_keys: list, checked_keys: list):
        """Обновляет статусы ключей после проверки серверов."""
        working_ids = {k.get('id') for k in working_keys if 'id' in k}
        checked_ids = {k.get('id') for k in checked_keys if 'id' in k}

        changed = False
        for k in self.keys:
            kid = k.get('id')
            if kid in checked_ids:
                new_status = kid in working_ids
                # Обновляем только если статус изменился или его еще не было
                if k.get('is_working') != new_status or 'last_checked' not in k:
                    k['is_working'] = new_status
                    k['last_checked'] = datetime.now().isoformat()
                    changed = True

        if changed:
            self._save_keys()

#==================================================================================================
# СИСТЕМНЫЙ ПРОКСИ
#==================================================================================================
def set_unix_proxy_gnome(enable: bool, host: str = "127.0.0.1", port: int = 25443):
    """Системный прокси через gsettings (GNOME и совместимые). Linux / FreeBSD."""
    system = platform.system()
    # FreeBSD: без GNOME gsettings нет — автонастройка системного прокси не поддерживается
    # (запись в ~/.profile не применилась бы к текущей сессии, поэтому не делаем этого)
    if not shutil.which('gsettings'):
        if system == 'FreeBSD':
            print(fix_emojis("ℹ️ FreeBSD: gsettings не найден — автонастройка системного прокси "
                             "без GNOME не поддерживается. Укажите SOCKS5 "
                             f"{host}:{port} вручную в браузере/приложении."))
        else:
            print(fix_emojis("ℹ️ gsettings не найден — автонастройка системного прокси недоступна."))
        return False
    try:
        mode = "manual" if enable else "none"
        r = subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', mode],
                           check=False, capture_output=True, timeout=5)
        if system == 'FreeBSD' and r.returncode != 0:
            # FreeBSD: gsettings есть, но схемы GNOME не установлены
            print(fix_emojis("ℹ️ FreeBSD: схема org.gnome.system.proxy недоступна — "
                             "автонастройка системного прокси не поддерживается."))
            return False
        if enable:
            for proto in ['socks', 'http', 'https']:
                subprocess.run(['gsettings', 'set', f'org.gnome.system.proxy.{proto}', 'host', host],
                               check=False, capture_output=True, timeout=5)
                subprocess.run(['gsettings', 'set', f'org.gnome.system.proxy.{proto}', 'port', str(port)],
                               check=False, capture_output=True, timeout=5)
        return True
    except Exception:
        return False

# Алиас для обратной совместимости (старое имя)
set_linux_proxy_gnome = set_unix_proxy_gnome

def set_linux_proxy(enable: bool, host: str = "127.0.0.1", port: int = 25443) -> bool:
    return set_unix_proxy_gnome(enable, host, port)

def set_system_proxy(enable: bool, host: str = "127.0.0.1 ", port: int = 25443):
    system = platform.system()
    if system == 'Windows':
        try:
            import winreg
            import ctypes
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings "
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, "ProxyEnable ", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "ProxyServer ", 0, winreg.REG_SZ, f"socks={host}:{port} ")
                else:
                    winreg.SetValueEx(key, "ProxyEnable ", 0, winreg.REG_DWORD, 0)
        except Exception as e:
            print(f"Ошибка прокси: {e} ")
            return False
        try:
            ctypes.windll.wininet.InternetSetOptionW(None, 39, None, 0)
            ctypes.windll.wininet.InternetSetOptionW(None, 37, None, 0)
        except Exception:
            pass
        return True
    else:
        # FreeBSD: не Windows-ветка — идёт в unix-реализацию (gsettings, иначе False + сообщение)
        return set_linux_proxy(enable, host, port)

#==================================================================================================
# МОНИТОР ЗАДЕРЖКИ
#==================================================================================================
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

#==================================================================================================
# WORKER ОБНОВЛЕНИЯ ПОДПИСОК
#==================================================================================================
class SubscriptionUpdateWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, int, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, sub_manager: SubscriptionManager, parent_window=None):
        super().__init__()
        self.sub_manager = sub_manager
        self.parent_window = parent_window
        self.running = True
        self.daemon = True

    def _fetch_url_with_ssl_fix(self, url: str, send_hwid: bool = True) -> str:
        try:
            headers = {
                'User-Agent': get_current_useragent()
            }
            if send_hwid:
                metadata = get_hwid_metadata()
                headers['x-hwid'] = metadata['hwid']
                headers['x-device-os'] = metadata['device_os']
                headers['x-ver-os'] = metadata['ver_os']
                headers['x-device-model'] = metadata['device_model']

            use_proxy = load_update_via_proxy_settings()
            proxy_running = is_proxy_running(self.parent_window)

            if use_proxy and proxy_running:
                proxy_handler = urllib.request.ProxyHandler({
                    'http': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}',
                    'https': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}'
                })
                opener = urllib.request.build_opener(proxy_handler)
                self.log_signal.emit(fix_emojis(f"🔌 Обновление через VPN: {url[:50]}..."))
                req = urllib.request.Request(url, headers=headers)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with opener.open(req, timeout=30, context=ctx) as response:
                    return response.read().decode('utf-8')

            if use_proxy and not proxy_running:
                self.log_signal.emit(fix_emojis("⚠️ VPN выключен, обновление напрямую"))

            if doh_enabled_for_subscriptions():
                settings = load_doh_settings()
                self.log_signal.emit(fix_emojis(f"🌐 DoH: {url[:50]}..."))
                req = urllib.request.Request(url, headers=headers)
                with DoHContext(timeout=settings.get("timeout", 10)) as doh_opener:
                    if doh_opener is not None:
                        with doh_opener.open(req, timeout=30) as response:
                            return response.read().decode('utf-8')
                    self.log_signal.emit(fix_emojis("⚠️ DoH не активен, прямое соединение"))

            req = urllib.request.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with URL_OPENER.open(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            try:
                import requests
                headers = {'User-Agent': get_current_useragent()}
                if send_hwid:
                    metadata = get_hwid_metadata()
                    headers['x-hwid'] = metadata['hwid']
                    headers['x-device-os'] = metadata['device_os']
                    headers['x-ver-os'] = metadata['ver_os']
                    headers['x-device-model'] = metadata['device_model']
                use_proxy = load_update_via_proxy_settings()
                proxy_running = is_proxy_running(self.parent_window)
                proxies = {}
                if use_proxy and proxy_running:
                    proxies = {
                        'http': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}',
                        'https': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}'
                    }
                response = requests.get(url, timeout=30, verify=False, headers=headers, proxies=proxies)
                response.raise_for_status()
                return response.text
            except ImportError:
                raise e

    def _parse_clash(self, data: str, depth: int = 0) -> List[str]:
        return parse_clash_subscription(
            data,
            fetch=lambda url: self._fetch_url_with_ssl_fix(url, False),
            parse_nested=lambda body: self._parse_subscription_data(body, depth + 1)[0],
            log=lambda msg: self.log_signal.emit(fix_emojis(msg)),
            depth=depth,
            should_stop=lambda: not self.running,
        )

    def _parse_clash_v2(self, data: str) -> List[str]:
        """Разбор Clash-подписки парсером v2: провайдеры грузятся тем же загрузчиком (VPN / DoH),
        лог идёт в log_signal, остановка — по флагу self.running."""
        return parse_clash_subscription_v2(
            data,
            log=lambda msg: self.log_signal.emit(fix_emojis(msg)),
            should_stop=lambda: not self.running,
            max_depth=2,
            fetch=lambda url: self._fetch_url_with_ssl_fix(url, False),
        )

    def _parse_subscription_data(self, data: str, _depth: int = 0) -> Tuple[List[str], bool]:
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
                        if item.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://')):
                            valid_keys.append(item)
                        elif isinstance(item, dict) and "outbounds" in item:
                            valid_keys.append(json.dumps(item, ensure_ascii=False))
                if valid_keys:
                    return valid_keys, True
            elif isinstance(json_data, dict):
                for value in json_data.values():
                    if isinstance(value, str) and value.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://')):
                        valid_keys.append(value.strip())
                if valid_keys:
                    return valid_keys, True
            return valid_keys, False
        except json.JSONDecodeError:
            pass
        if looks_like_clash(data):
            if get_clash_parser_mode() == "v2":
                return self._parse_clash_v2(data), True
            return self._parse_clash(data, _depth), True
        try:
            padded = data + '=' * (-len(data) % 4)
            decoded = base64.b64decode(padded).decode('utf-8')
            if looks_like_clash(decoded):
                if get_clash_parser_mode() == "v2":
                    return self._parse_clash_v2(decoded), True
                return self._parse_clash(decoded, _depth), True
            lines = [l.strip() for l in decoded.splitlines() if l.strip()]
            valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://'))]
            if valid_keys:
                return valid_keys, True
        except Exception:
            pass
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://'))]
        if valid_keys:
            return valid_keys, True
        return valid_keys, False

    def _update_single_subscription(self, sub: dict) -> Tuple[bool, str]:
        url = sub["url"]
        send_hwid = sub.get("send_hwid", True)
        try:
            data = self._fetch_url_with_ssl_fix(url, send_hwid)
            if send_hwid:
                hwid = get_hwid()[:8]
                self.log_signal.emit(fix_emojis(f"🔑 Подписка '{sub.get('name', '')}': HWID отправлен ({hwid}...)"))
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

    def stop(self):
        self.running = False

#==================================================================================================
# XRAY WORKER
#==================================================================================================
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
            if system_is_freebsd():
                # FreeBSD: ZIP-сборок нет, подсказываем pkg
                self.log_signal.emit(fix_emojis(FREEBSD_XRAY_HINT))
            else:
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
            # FreeBSD: попадает сюда (не в Windows-ветку) — отдельная сессия, как на Linux
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

#==================================================================================================
# ДИАЛОГ НАСТРОЕК МАРШРУТИЗАЦИИ
#==================================================================================================
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
            radio = QRadioButton(fix_emojis(f"{mode_info['name ']}"))
            radio.setToolTip(fix_emojis(mode_info['desc ']))
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
        settings = load_json_file(TUNNEL_SETTINGS_FILE, {})
        current_mode = settings.get("mode", "ru_direct ")
        if current_mode not in TUNNEL_MODES:
            current_mode = "ru_direct "
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
        file_path = mode.get("file ")
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
        total = len([m for m in TUNNEL_MODES.values() if m.get("file ") is not None])
        for i, (mode_key, mode_info) in enumerate(TUNNEL_MODES.items(), 1):
            if mode_info.get("file ") is None:
                continue
            self.progress_label.setText(fix_emojis(f"📥 [{i}/{total}] {mode_info['name ']}..."))
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
        file_path = mode.get("file ")
        if file_path is not None and not os.path.exists(file_path):
            reply = QMessageBox.question(
                self, fix_emojis("Файл не найден"),
                fix_emojis("Файл для режима '" + mode['name '] + "' отсутствует.\nСкачать сейчас?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.progress_label.setText(fix_emojis(f"⏬ Загрузка {os.path.basename(file_path)}..."))
                QApplication.processEvents()
                if not download_file(mode["url "], file_path):
                    QMessageBox.critical(self, fix_emojis("Ошибка"), fix_emojis("Не удалось скачать файл!"))
                    return
            else:
                return
        settings = {
            "mode": selected_mode,
            "mode_name": mode["name "],
            "updated": datetime.now().isoformat()
        }
        save_json_file(TUNNEL_SETTINGS_FILE, settings)
        if self.parent_window and hasattr(self.parent_window, 'update_tunnel_mode'):
            self.parent_window.update_tunnel_mode(selected_mode)
        QMessageBox.information(self, fix_emojis("Успех"), fix_emojis(f"Режим применён: {mode['name ']}"))
        self.accept()

#==================================================================================================
# ДИАЛОГ УПРАВЛЕНИЯ ПОДПИСКАМИ
#==================================================================================================
class SubscriptionDialog(QDialog):
    def __init__(self, sub_manager: SubscriptionManager, parent=None):
        super().__init__(parent)
        self.sub_manager = sub_manager
        self.setWindowTitle(fix_emojis("Управление подписками"))
        self.setMinimumSize(550, 450)
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
        self.hwid_check = QCheckBox(fix_emojis("🔑 Передавать HWID при обновлении"))
        self.hwid_check.setChecked(True)
        self.hwid_check.setToolTip(fix_emojis("При обновлении подписки будут переданы заголовки x-hwid, x-device-os и др."))
        form_layout.addRow("URL:", self.url_input)
        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Интервал:", self.interval_spin)
        form_layout.addRow(self.hwid_check)
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
            hwid_status = "🔑" if sub.get("send_hwid", True) else "🚫"
            text = f"{status}{sub.get('name', 'Без названия')}\n"
            text += f"🔗 {sub['url'][:40]}...\n"
            text += f"📊 Ключей: {sub.get('key_count', 0)} | 🕐 Обновлено: {last_str} | {hwid_status} HWID"
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
        send_hwid = self.hwid_check.isChecked()
        new_sub = self.sub_manager.add_subscription(url, interval, send_hwid)
        if name != new_sub["name"]:
            self.sub_manager.update_subscription(new_sub["id"], name=name)
        self._load_subscriptions()
        self.url_input.clear()
        self.name_input.clear()
        QMessageBox.information(
            self,
            fix_emojis("Успех"),
            fix_emojis(f"Подписка добавлена!\n🔑 Передача HWID: {'включена' if send_hwid else 'выключена'}")
        )

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
        hwid_check = QCheckBox(fix_emojis("🔑 Передавать HWID"))
        hwid_check.setChecked(sub.get("send_hwid", True))
        hwid_check.setToolTip(fix_emojis("При обновлении подписки будут переданы заголовки x-hwid"))
        layout.addRow(fix_emojis("Интервал обновления:"), interval_spin)
        layout.addRow(enabled_check)
        layout.addRow(hwid_check)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(
            lambda: self._save_edit(sub_id, interval_spin.value(),
                                    enabled_check.isChecked(), hwid_check.isChecked(), dialog)
        )
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        dialog.exec()

    def _save_edit(self, sub_id: str, interval_min: int, enabled: bool, send_hwid: bool, dialog: QDialog):
        self.sub_manager.update_subscription(
            sub_id,
            update_interval=interval_min * 60,
            enabled=enabled,
            send_hwid=send_hwid
        )
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

#==================================================================================================
# КЛАСС ДЛЯ ПРОВЕРКИ СЕРВЕРОВ
#==================================================================================================
class ServerChecker(QThread):
    """
    Проверка серверов через API самого Xray.

    Вместо запуска отдельного процесса Xray на каждый сервер и скачивания
    тестового файла через SOCKS5, серверы проверяются пачками:
      1. Все серверы пачки добавляются как outbound'ы (chk0, chk1, ...) в ОДИН
         конфиг Xray.
      2. Встроенный observatory сам и параллельно пробует каждый outbound
         (probeUrl), не требуя ни inbound'ов, ни маршрутизации.
      3. Результаты (alive / delay / last_error_reason) читаются из API Xray —
         HTTP-эндпоинта metrics (/debug/vars, ключ "observatory").
    """
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    # передает (working, checked)
    finished_signal = pyqtSignal(list, list)
    partial_signal = pyqtSignal(list)

    OUTBOUND_PREFIX = "chk"       # теги проверяемых outbound'ов (observatory.subjectSelector)
    SYSTEM_PROTOCOLS = ("freedom", "blackhole", "dns", "loopback")

    def __init__(self, keys: list, proxy_host: str = "127.0.0.1", proxy_port: int = 25443,
                 batch_size: int = 50):
        super().__init__()
        self.keys = keys
        # proxy_port оставлен для совместимости вызова; порт API выбирается свободный автоматически
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.batch_size = max(1, int(batch_size))
        self.running = True
        self.daemon = True
        self.test_url = HTTP_SERVER_TEST
        self.timeout = 10            # сколько ждем результаты проб в пачке (сек, +5 запас)
        self.startup_timeout = 10    # сколько ждем запуска Xray и его API (сек)
        self.working_servers = []
        self.checked_servers = []
        self.current_index = 0
        self._fatal_error = None

    # ------------------------------------------------------------------ основной цикл
    def run(self):
        self.working_servers = []
        self.checked_servers = []
        self._fatal_error = None
        total = len(self.keys)
        self.progress_signal.emit(0, total)
        for start in range(0, total, self.batch_size):
            if not self.running or self._fatal_error:
                break
            self.current_index = start
            batch = self.keys[start:start + self.batch_size]
            self._check_batch(batch, start)
            self.progress_signal.emit(min(start + len(batch), total), total)

        if self._fatal_error:
            self.log_signal.emit(fix_emojis(f"❌ {self._fatal_error}"))
            self.finished_signal.emit(self.working_servers, self.checked_servers)
            return
        if not self.running:
            self.partial_signal.emit(self.working_servers)
            self.log_signal.emit(fix_emojis(
                f"⏸️ Проверка прервана. Найдено рабочих серверов: "
                f"{len(self.working_servers)}/{len(self.checked_servers)}"))
            return
        self.log_signal.emit(fix_emojis(
            f"📊 Проверка завершена. Рабочих серверов: {len(self.working_servers)}/{total}"))
        self.finished_signal.emit(self.working_servers, self.checked_servers)

    def stop(self):
        self.running = False

    # ------------------------------------------------------------------ пачка серверов
    def _check_batch(self, batch: list, offset: int):
        entries = []
        for i, key_data in enumerate(batch):
            idx = offset + i
            tag = f"{self.OUTBOUND_PREFIX}{idx}"
            outbounds, reason = self._build_outbounds(key_data.get("key", ""), tag)
            entries.append({
                "key_data": key_data, "index": idx, "tag": tag, "outbounds": outbounds,
                "working": False, "delay": None,
                "checked": outbounds is None,            # не разобранный ключ — сразу "проверен"
                "details": [f"❌ {reason}"] if outbounds is None else [],
            })

        ready = [e for e in entries if e["outbounds"] is not None]
        if ready:
            self._probe_entries(ready)

        for e in entries:
            if not e["checked"]:      # проверка прервана до результата — не считаем проверенным
                continue
            self.checked_servers.append(e["key_data"])
            label = self._get_server_label(e["key_data"], e["index"])
            if e["working"]:
                self.working_servers.append(e["key_data"])
                delay = f" ({e['delay']} мс)" if e["delay"] else ""
                self.log_signal.emit(fix_emojis(f"✅ Сервер рабочий: {label}{delay}"))
            else:
                self.log_signal.emit(fix_emojis(f"❌ Сервер не отвечает: {label}"))
                for detail in e["details"][:3]:
                    self.log_signal.emit(fix_emojis(f"  🔍 {detail}"))

    def _probe_entries(self, entries: list):
        """Запускает Xray с этими серверами и заполняет результаты в entries."""
        if not self.running or self._fatal_error:
            return
        outbounds = [ob for e in entries for ob in e["outbounds"]]
        tags = [e["tag"] for e in entries]
        statuses, error, fatal = self._run_observatory(outbounds, tags)

        if fatal:
            self._fatal_error = error
            return
        if statuses is None:
            # Xray не запустился. Если в пачке несколько серверов — делим пополам,
            # чтобы изолировать сервер с битой конфигурацией.
            if len(entries) > 1:
                mid = len(entries) // 2
                self._probe_entries(entries[:mid])
                self._probe_entries(entries[mid:])
            elif self.running:
                entries[0]["checked"] = True
                entries[0]["details"].append(f"❌ {error}")
            return

        interrupted = not self.running
        wait = self.timeout + 5
        for e in entries:
            st = statuses.get(e["tag"])
            if st is not None and self._status_is_final(st):
                e["checked"] = True
                if st.get("alive") is True:
                    e["working"] = True
                    e["delay"] = st.get("delay")
                    e["details"].append("✅ Observatory (Xray API): сервер ответил")
                else:
                    reason = st.get("last_error_reason") or st.get("lastErrorReason") or "нет ответа"
                    e["details"].append(f"❌ Observatory (Xray API): {str(reason)[:120]}")
            elif not interrupted:
                e["checked"] = True
                e["details"].append(f"❌ Нет результата от Xray API за {wait} сек")

    # ------------------------------------------------------------------ запуск Xray и чтение API
    def _run_observatory(self, outbounds: list, tags: list):
        """
        Возвращает (statuses, error, fatal):
          statuses — {tag: status} из API Xray или None, если Xray не удалось запустить;
          error    — текст ошибки; fatal — True, если проверка невозможна вообще.
        """
        xray_path = find_xray_binary()
        if not xray_path or not os.path.exists(xray_path):
            return None, f"Xray не найден по пути: {xray_path}", True

        process = None
        config_path = os.path.join(DATA_DIR, f"checker_config_{uuid.uuid4().hex[:8]}.json")
        stderr_lines = []
        try:
            api_port = self._free_port()
            config = self._build_batch_config(outbounds, api_port)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, text=True, bufsize=1)
            if platform.system() == 'Windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                popen_kwargs.update(startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                # FreeBSD: попадает сюда (не в Windows-ветку)
                popen_kwargs.update(start_new_session=True)
            process = subprocess.Popen([xray_path, "run", "-c", config_path], **popen_kwargs)

            def read_stderr():
                try:
                    for line in process.stderr:
                        stderr_lines.append(line.rstrip())
                        del stderr_lines[:-20]
                except Exception:
                    pass
            threading.Thread(target=read_stderr, daemon=True).start()

            # 1) ждем, пока поднимется API Xray
            started = False
            deadline = time.time() + self.startup_timeout
            while time.time() < deadline and self.running:
                if self._fetch_vars(api_port) is not None:
                    started = True
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            if not started:
                if not self.running:
                    return {}, None, False
                tail = " | ".join(l for l in stderr_lines[-3:] if l)[:200]
                if process.poll() is not None:
                    return None, f"Xray завершился при запуске: {tail or 'код ' + str(process.returncode)}", False
                return None, "Таймаут ожидания запуска API Xray", False

            # 2) опрашиваем observatory, пока все серверы не получат результат
            best = {}
            deadline = time.time() + self.timeout + 5
            while True:
                data = self._fetch_vars(api_port)
                if data is not None:
                    for tag, st in self._parse_observation(data).items():
                        prev = best.get(tag)
                        if prev is None or not (prev.get("alive") is True):
                            best[tag] = st      # живой статус не затираем
                if all(t in best and self._status_is_final(best[t]) for t in tags):
                    break
                if not self.running or time.time() >= deadline:
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.3)
            return best, None, False
        except Exception as e:
            return None, f"Ошибка запуска проверки: {str(e)[:120]}", False
        finally:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
            if os.path.exists(config_path):
                try:
                    os.remove(config_path)
                except Exception:
                    pass

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.proxy_host, 0))
            return s.getsockname()[1]

    def _build_batch_config(self, outbounds: list, api_port: int) -> dict:
        return {
            "log": {"loglevel": "warning"},
            "dns": {"servers": ["1.1.1.1", "8.8.8.8"]},
            # API Xray: expvar-эндпоинт http://host:port/debug/vars (содержит "observatory")
            "metrics": {"tag": "metrics", "listen": f"{self.proxy_host}:{api_port}"},
            "observatory": {
                "subjectSelector": [self.OUTBOUND_PREFIX],
                "probeUrl": self.test_url,
                "probeInterval": "10s",
                "enableConcurrency": True,
            },
            # direct первым — это outbound по умолчанию (DNS-запросы самого Xray идут напрямую,
            # а не через проверяемый сервер)
            "outbounds": [{"protocol": "freedom", "tag": "direct"}] + outbounds,
        }

    def _fetch_vars(self, api_port: int) -> Optional[dict]:
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # без системных прокси
            with opener.open(f"http://{self.proxy_host}:{api_port}/debug/vars", timeout=2) as resp:
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    @staticmethod
    def _parse_observation(data: dict) -> dict:
        """Приводит ключ "observatory" из /debug/vars к виду {outbound_tag: status}."""
        obs = data.get("observatory")
        if isinstance(obs, dict) and isinstance(obs.get("status"), list):
            items = [(None, v) for v in obs["status"]]
        elif isinstance(obs, dict):
            items = list(obs.items())
        elif isinstance(obs, list):
            items = [(None, v) for v in obs]
        else:
            return {}
        result = {}
        for key, st in items:
            if not isinstance(st, dict):
                continue
            tag = st.get("outbound_tag") or st.get("outboundTag") or key
            if tag:
                result[tag] = st
        return result

    @staticmethod
    def _status_is_final(st: dict) -> bool:
        """Проба для этого outbound'а уже выполнена (успешно или с ошибкой)."""
        return bool(st.get("alive") or st.get("last_try_time") or st.get("last_seen_time")
                    or st.get("lastTryTime") or st.get("lastSeenTime")
                    or st.get("last_error_reason") or st.get("lastErrorReason"))

    # ------------------------------------------------------------------ подпись сервера в логе
    def _get_server_label(self, key_data: dict, index: int) -> str:
        key = key_data.get("key", "")
        if key.startswith('{') and key.endswith('}'):
            try:
                config = json.loads(key)
                outbounds = config.get("outbounds", [])
                for ob in outbounds:
                    if ob.get("tag") == "proxy":
                        settings = ob.get("settings", {})
                        if "vnext" in settings and settings["vnext"]:
                            addr = settings["vnext"][0].get("address", "???")
                            return f"{addr}"
                        elif "servers" in settings and settings["servers"]:
                            addr = settings["servers"][0].get("address", "???")
                            return f"{addr}"
            except:
                pass
            return f"JSON #{index+1}"
        if '://' in key:
            proto, rest = key.split('://', 1)
            if '@' in rest:
                host_part = rest.split('@')[-1].split('?')[0].split('#')[0]
                if ':' in host_part:
                    host = host_part.split(':')[0]
                else:
                    host = host_part
                return f"{proto.upper()}:{host}"
            else:
                return f"{proto.upper()}"
        return f"Сервер #{index+1}"

    # ------------------------------------------------------------------ ключ -> outbound
    def _build_outbounds(self, key_string: str, tag: str):
        """Возвращает ([outbound, ...], None) или (None, причина). Главный outbound имеет тег `tag`."""
        key_string = (key_string or "").strip()
        try:
            if key_string.startswith('{'):
                return self._outbounds_from_json_config(json.loads(key_string), tag), None
            if key_string.startswith("vless://"):
                outbound = self._build_vless_outbound(key_string)
            elif key_string.startswith("vmess://"):
                outbound = self._build_vmess_outbound(key_string)
            elif key_string.startswith("trojan://"):
                outbound = self._build_trojan_outbound(key_string)
            # SS-removed: ветка ss:// удалена
            elif key_string.startswith(("hysteria://", "hysteria2://")):
                outbound = self._build_hysteria_outbound(key_string)
            else:
                return None, "Неподдерживаемый формат ключа"
            outbound["tag"] = tag
            return [outbound], None
        except ValueError as e:
            return None, str(e) or "Некорректный ключ"
        except Exception as e:
            return None, f"Не удалось разобрать ключ: {str(e)[:80]}"

    def _outbounds_from_json_config(self, config: dict, tag: str) -> list:
        clone = lambda x: json.loads(json.dumps(x))
        outbounds = config.get("outbounds") if isinstance(config, dict) else None
        if not isinstance(outbounds, list) or not outbounds:
            raise ValueError("В JSON-конфиге нет outbounds")
        by_tag = {ob["tag"]: ob for ob in outbounds if isinstance(ob, dict) and ob.get("tag")}
        main = by_tag.get("proxy")
        if main is None:
            main = next((ob for ob in outbounds
                         if isinstance(ob, dict) and ob.get("protocol") not in self.SYSTEM_PROTOCOLS), None)
        if main is None:
            raise ValueError("В JSON-конфиге не найден прокси-outbound")
        main = clone(main)
        main["tag"] = tag
        result, mapping, queue = [main], {}, [main]
        # outbound'ы-зависимости (цепочки proxySettings / dialerProxy) копируем с новыми тегами
        while queue:
            cur = queue.pop()
            sockopt = (cur.get("streamSettings") or {}).get("sockopt")
            for holder, field in ((cur.get("proxySettings"), "tag"), (sockopt, "dialerProxy")):
                if not isinstance(holder, dict) or not holder.get(field):
                    continue
                ref = holder[field]
                if ref not in by_tag:
                    continue
                if ref not in mapping:
                    mapping[ref] = f"dep{tag}_{len(mapping) + 1}"
                    dep = clone(by_tag[ref])
                    dep["tag"] = mapping[ref]
                    result.append(dep)
                    queue.append(dep)
                holder[field] = mapping[ref]
        return result

    def _build_vless_outbound(self, key_string: str) -> dict:
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
        allow_insecure = get('allowInsecure', '0')
        if allow_insecure == '1' or allow_insecure.lower() == 'true':
            raise ValueError("Небезопасный ключ (allowInsecure) — пропущен")
        uuid_addr = addr_part.split('@')
        if len(uuid_addr) != 2:
            raise ValueError("Некорректный формат VLESS-ключа")
        user_id = uuid_addr[0]
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
            raise ValueError("Ключ без шифрования (security=none) — пропущен")
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
        settings = {"vnext": [{"address": address, "port": port, "users": [{
            "id": user_id, "encryption": "none", "flow": flow if flow else None}]}]}
        return {"protocol": "vless", "settings": settings, "streamSettings": stream}

    def _build_vmess_outbound(self, key_string: str) -> dict:
        b64 = key_string[8:].strip()
        b64 += '=' * (-len(b64) % 4)
        vmess = json.loads(base64.b64decode(b64).decode('utf-8'))
        if vmess.get('allowInsecure', False):
            raise ValueError("Небезопасный ключ (allowInsecure) — пропущен")
        address = vmess.get('add', '')
        port = int(vmess.get('port', 443))
        user_id = vmess.get('id', '')
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
        settings = {"vnext": [{"address": address, "port": port, "users": [{
            "id": user_id, "alterId": aid, "security": "auto"}]}]}
        return {"protocol": "vmess", "settings": settings, "streamSettings": stream}

    def _build_trojan_outbound(self, key_string: str) -> dict:
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
        if get('allowInsecure', '0') == '1':
            raise ValueError("Небезопасный ключ (allowInsecure) — пропущен")
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
        settings = {"servers": [{"address": address, "port": port, "password": password}]}
        return {"protocol": "trojan", "settings": settings, "streamSettings": stream}

    # SS-removed: построитель SS-outbound для проверки серверов удалён

    def _build_hysteria_outbound(self, key_string: str) -> dict:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(key_string)
        if not parsed.hostname or not parsed.port:
            raise ValueError("Некорректный формат Hysteria-ключа")
        host = parsed.hostname
        port = parsed.port
        params = parse_qs(parsed.query)
        get = lambda n, d='': params.get(n, [d])[0]
        if get('insecure', '0') == '1':
            raise ValueError("Небезопасный ключ (insecure) — пропущен")
        auth = get('auth', '')
        peer = get('peer', '') or host
        up = get('up', '10')
        down = get('down', '50')
        obfs = get('obfs', '')
        obfs_password = get('obfs-password', '')
        stream = {"network": "udp", "security": "tls",
                  "tlsSettings": {"allowInsecure": False, "serverName": peer}}
        if obfs:
            stream["hysteriaSettings"] = {"obfs": obfs, "obfsPassword": obfs_password}
        settings = {"servers": [{"address": host, "port": port, "auth": auth, "up": up, "down": down}]}
        protocol = "hysteria2" if key_string.startswith("hysteria2://") else "hysteria"
        return {"protocol": protocol, "settings": settings, "streamSettings": stream}

#==================================================================================================
# ДИАЛОГ РЕЗУЛЬТАТОВ ПРОВЕРКИ СЕРВЕРОВ
#==================================================================================================
class CheckResultDialog(QDialog):
    def __init__(self, working_servers: list, parent=None, partial: bool = False):
        super().__init__(parent)
        self.working_servers = working_servers
        self.partial = partial
        self.setWindowTitle(fix_emojis("📊 Результаты проверки серверов"))
        self.setMinimumSize(550, 400)
        self.setFont(QFont("Arial"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        status_text = "⏸️ Частичный результат" if self.partial else "✅ Проверка завершена"
        title = QLabel(fix_emojis(f"{status_text} - Рабочих серверов: {len(self.working_servers)}"))
        title.setStyleSheet("font-weight: bold; font-size: 12pt; color: #51cf66;")
        layout.addWidget(title)

        sorted_servers = self._sort_servers(self.working_servers)
        list_widget = QListWidget()
        list_widget.setStyleSheet("font-size: 10pt;")
        if sorted_servers:
            for i, key_data in enumerate(sorted_servers):
                key = key_data.get("key", "")
                display = self._format_server_display(key, i)
                list_widget.addItem(fix_emojis(f"✅ {display}"))
        else:
            list_widget.addItem(fix_emojis("❌ Рабочих серверов не найдено"))
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton(fix_emojis("Закрыть"))
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(120)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _sort_servers(self, servers: list) -> list:
        def sort_key(key_data):
            key = key_data.get("key", "")
            parsed = parse_key_for_display(key)
            protocol_order = {"VLESS ": 0, "VMESS ": 1, "TROJAN ": 2, "HYSTERIA ": 3, "HYSTERIA2 ": 4}
            proto = parsed.get("protocol ", "ZZZ ")
            proto_priority = protocol_order.get(proto, 99)
            addr = parsed.get("address ", "")
            return (proto_priority, addr, proto)
        return sorted(servers, key=sort_key)

    def _format_server_display(self, key: str, index: int) -> str:
        if key.startswith('{') and key.endswith('}'):
            try:
                config = json.loads(key)
                outbounds = config.get("outbounds", [])
                for ob in outbounds:
                    if ob.get("tag") == "proxy":
                        settings = ob.get("settings", {})
                        if "vnext" in settings and settings["vnext"]:
                            addr = settings["vnext"][0].get("address", "???")
                            return f"JSON: {addr}"
                        elif "servers" in settings and settings["servers"]:
                            addr = settings["servers"][0].get("address", "???")
                            return f"JSON: {addr}"
            except:
                pass
            return f"JSON #{index+1}"
        if '://' in key:
            proto, rest = key.split('://', 1)
            if '@' in rest:
                host_part = rest.split('@')[-1].split('?')[0].split('#')[0]
                if ':' in host_part:
                    host = host_part.split(':')[0]
                else:
                    host = host_part
                return f"{proto.upper()}: {host}"
            return f"{proto.upper()}"
        return f"Сервер #{index+1}"

#==================================================================================================
# ОСНОВНОЙ КЛАСС
#==================================================================================================
class XrayClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(fix_emojis("Bobcat Proxy 3.0 pre3 - Прокси отключен"))
        self.setFont(QFont("Arial"))
        self.setMinimumSize(950, 700)

        self.current_theme = get_system_theme()
        self._setup_icon(self.current_theme)
        self.sub_manager = SubscriptionManager(KEYS_DB_PATH, SUBS_DB_PATH)
        self.xray_thread = None
        self.latency_monitor = None
        self.sub_update_worker = None
        self.update_checker = None
        self.download_worker = None
        self.server_checker = None
        self.system_proxy_enabled = False
        self.current_source_filter = "manual"
        self.current_tunnel_mode = self._read_tunnel_mode_from_disk()
        self.current_update_channel = self._get_update_channel()
        self.log_styles = {
            "dark": "background-color: #1e1e1e; color: #00ff00;",
            "light": "background-color: #ffffff; color: #000000;",
        }
        self.init_ui()
        self._refresh_version_display()
        self.theme_monitor = ThemeMonitor(self)
        self.theme_monitor.theme_changed.connect(self.on_theme_changed)
        self.theme_monitor.start()

        self._version_sync_timer = QTimer(self)
        self._version_sync_timer.timeout.connect(self._refresh_version_display)
        self._version_sync_timer.start(30000)

        self.log_buffer = []
        self.log_timer = None
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
        except Exception:
            pass
        print(fix_emojis(f"📁 Логи будут в: {LOGS_DIR}"))
        self.log_text.append(fix_emojis(f"📁 Путь к логам: {LOGS_DIR}"))
        self.log_text.append(fix_emojis(f"🔧 Xray-core версия: {XRAY_VERSION}"))
        self.log_text.append(fix_emojis(f"📡 Канал обновлений: {UPDATE_CHANNELS[self.current_update_channel]['name ']}"))

        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows ")
            if preset_key == "custom ":
                ua_info = "Свой User-Agent"
            else:
                ua_info = USERAGENT_PRESETS.get(preset_key, {}).get("name ", "Неизвестно")
            self.log_text.append(fix_emojis(f"🌐 User-Agent: {ua_info}"))
        else:
            self.log_text.append(fix_emojis("🌐 User-Agent: Стандартный"))

        update_via_proxy = load_update_via_proxy_settings()
        self.log_text.append(fix_emojis(f"🔌 Обновление подписок через VPN: {'включено' if update_via_proxy else 'выключено'}"))

        doh_settings = load_doh_settings()
        if doh_settings.get("enabled"):
            provider = doh_settings.get("provider", "cloudflare ")
            if provider == "custom ":
                pname = "Свой DoH-сервер"
            else:
                pname = DOH_PROVIDERS.get(provider, {}).get("name ", provider)
            self.log_text.append(fix_emojis(f"🌐 DNS over HTTPS: {pname}"))
        else:
            self.log_text.append(fix_emojis("🌐 DNS over HTTPS: выключен"))

        hwid_metadata = get_hwid_metadata()
        self.log_text.append(fix_emojis(f"🔑 HWID: {hwid_metadata['hwid']}"))
        self.log_text.append(fix_emojis(f"📱 Device OS: {hwid_metadata['device_os']}"))
        self.log_text.append(fix_emojis(f"📦 OS Version: {hwid_metadata['ver_os']}"))
        self.log_text.append(fix_emojis(f"💻 Device Model: {hwid_metadata['device_model']}"))

        self.refresh_keys_list()
        self.refresh_subs_list()
        self._apply_auto_select_last_key()
        self.start_subscription_updates()
        self.update_status(False)
        self._load_tunnel_settings()
        QTimer.singleShot(2000, self.auto_check_updates)
        self.log_text.setStyleSheet(self.log_styles.get(self.current_theme, self.log_styles["light"]))

    def _refresh_version_display(self):
        global XRAY_PATH, XRAY_VERSION
        XRAY_PATH = find_xray_binary()
        version = get_current_xray_version()
        if XRAY_PATH and version:
            XRAY_VERSION = version
            version_text = f"Xray-core: v{version}"
        elif XRAY_PATH:
            XRAY_VERSION = "неизвестно"
            version_text = "Xray-core: версия неизвестна"
        else:
            XRAY_VERSION = "не установлен"
            version_text = "Xray-core: не установлен"
        channel_name = UPDATE_CHANNELS.get(
            self._get_update_channel(), {}
        ).get("name ", "—")
        full_text = f"{version_text} | Канал: {channel_name}"
        if hasattr(self, 'version_label'):
            self.version_label.setText(fix_emojis(full_text))
        is_active = bool(self.xray_thread and self.xray_thread.isRunning())
        state = "ВКЛЮЧЕН" if is_active else "Прокси отключен"
        self.setWindowTitle(fix_emojis(f"Bobcat Proxy 3.0 pre3 - {state}"))
        return XRAY_VERSION

    def _setup_icon(self, theme: str):
        set_window_icon(self, theme)

    def on_theme_changed(self, new_theme: str):
        self.current_theme = new_theme
        self._setup_icon(new_theme)
        self.log_text.setStyleSheet(self.log_styles.get(new_theme, self.log_styles["light"]))
        print(f"🎨 Тема системы: {new_theme}")

    def _get_update_channel(self) -> str:
        settings = load_json_file(os.path.join(DATA_DIR, "update_settings.json"), {})
        channel = str(settings.get("channel", DEFAULT_UPDATE_CHANNEL)).strip()
        return channel if channel in UPDATE_CHANNELS else DEFAULT_UPDATE_CHANNEL

    def _get_key_display_mode(self) -> str:
        settings = get_ui_settings()
        return settings.get("key_display_mode ", DEFAULT_KEY_DISPLAY_MODE)

    def _set_key_display_mode(self, mode: str):
        save_ui_settings({"key_display_mode ": mode})

    def _get_log_mode(self) -> str:
        settings = get_ui_settings()
        return settings.get("log_mode ", DEFAULT_LOG_MODE)

    def _get_xray_loglevel(self) -> str:
        log_mode = self._get_log_mode()
        return "debug" if log_mode == "debug" else "warning"

    def _set_log_mode(self, mode: str):
        if mode in LOG_MODES:
            save_ui_settings({"log_mode ": mode})
            mode_name = LOG_MODES[mode]
            self.log_text.append(fix_emojis(f"📝 Режим логирования изменён на: {mode_name}"))
            if self.xray_thread and self.xray_thread.isRunning():
                self.log_text.append(fix_emojis("⚠️ Для применения нового loglevel перезапустите прокси"))

    def _toggle_window_frame(self):
        settings = get_ui_settings()
        new_state = not settings.get("hide_window_frame ", False)
        save_ui_settings({"hide_window_frame ": new_state})
        apply_window_frame_setting(self)
        state_text = "скрыта" if new_state else "показана"
        self.append_log(fix_emojis(f"🪟 Рамка окна: {state_text}"))

    def _change_emoji_mode(self, mode: str):
        if mode not in ("auto", "off"):
            return
        save_ui_settings({"emoji_mode ": mode})
        state = "отключены" if mode == "off" else "авто"
        self.append_log(f"Режим эмодзи изменён на: {state}")
        QMessageBox.information(
            self,
            "Режим эмодзи",
            "Изменения применятся после перезапуска программы."
        )

    def _toggle_auto_select_last_key(self):
        settings = get_ui_settings()
        new_state = not settings.get("auto_select_last_key ", False)
        save_ui_settings({"auto_select_last_key ": new_state})
        state_text = "включён" if new_state else "выключен"
        self.append_log(fix_emojis(f"🔑 Авто-выбор последнего ручного ключа: {state_text}"))
        if new_state:
            self._apply_auto_select_last_key()

    def _apply_auto_select_last_key(self):
        settings = get_ui_settings()
        if not settings.get("auto_select_last_key ", False):
            return
        manual_keys = self.sub_manager.get_keys_by_source("manual")
        if not manual_keys:
            return
        last_index = len(manual_keys) - 1
        if hasattr(self, 'keys_tabs'):
            for i in range(self.keys_tabs.count()):
                if "Ручные" in self.keys_tabs.tabText(i):
                    self.keys_tabs.setCurrentIndex(i)
                    break
        if self.key_selector_manual.count() > 0:
            self.key_selector_manual.setCurrentIndex(last_index)
        all_keys = self.sub_manager.keys
        for i, k in enumerate(all_keys):
            if k.get("id") == manual_keys[last_index].get("id"):
                self.key_selector_all.setCurrentIndex(i)
                break
        self.current_tab = "filtered"
        self.current_source_filter = "manual"
        self.append_log(fix_emojis(
            f"🔑 Автовыбор: последний ручной ключ "
            f"(#{last_index + 1} из {len(manual_keys)})"
        ))

    # ИЗМЕНЕНО: добавлены иконки статусов 🟢/🔴/⚪
    def _format_key_display(self, key_data: dict, index: int) -> str:
        key = key_data["key"]
        source_icon = "📡" if key_data.get("source") == "subscription" else "✋"

        # НОВОЕ: Иконка статуса
        if key_data.get("is_working") is True:
            status_icon = "🟢 "
        elif "is_working" in key_data and key_data["is_working"] is False:
            status_icon = "🔴 "
        else:
            status_icon = "⚪ "

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
            return f"{status_icon}{source_icon}{index+1}. {name}"
        elif mode == "detailed":
            parsed = parse_key_for_display(key)
            addr_short = parsed["address "]
            if len(addr_short) > 20:
                addr_short = addr_short[:17] + "..."
            name = f"{parsed['protocol ']} | {addr_short} | {parsed['transport ']}"
            return f"{status_icon}{source_icon}{index+1}. {name}"
        else:
            parsed = parse_key_for_display(key)
            hashtag = parsed.get("hashtag ", "").strip()
            if hashtag:
                if len(hashtag) > 30:
                    hashtag = hashtag[:27] + "..."
                name = f"🏷️ {hashtag}"
            else:
                proto = parsed.get("protocol ", "??? ")
                addr = parsed.get("address ", "??? ")
                if len(addr) > 15:
                    addr = addr[:12] + "..."
                name = f"🔗 {proto} | {addr}"
            return f"{status_icon}{source_icon}{index+1}. {name}"

    def _change_key_display_mode(self, mode: str):
        if mode in KEY_DISPLAY_MODES:
            self._set_key_display_mode(mode)
            self.refresh_keys_list()
            self.log_text.append(fix_emojis(f"🔑 Формат отображения: {KEY_DISPLAY_MODES[mode]}"))

    def _change_log_mode(self, mode: str):
        if mode in LOG_MODES:
            self._set_log_mode(mode)

    # FreeBSD: предложение установить Xray-core через pkg вместо ZIP
    def _offer_pkg_install_xray(self):
        worker = getattr(self, '_pkg_worker', None)
        if worker is not None and worker.isRunning():
            return
        reply = QMessageBox.question(
            self, fix_emojis("Xray-core не найден"),
            fix_emojis("Xray-core не установлен.\n\n"
                       "Для FreeBSD официальных сборок Xray-core нет.\n"
                       "Установить через pkg (pkg install -y xray-core)?\n\n"
                       "Нужен root либо sudo/doas без запроса пароля."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.append_log(fix_emojis("📥 Установка Xray-core через pkg..."))
        self._pkg_worker = PkgInstallWorker()
        self._pkg_worker.status.connect(self.append_log)
        self._pkg_worker.done.connect(self._on_pkg_install_done)
        self._pkg_worker.start()

    def _on_pkg_install_done(self, success: bool, message: str):
        if success:
            self.append_log(fix_emojis(f"✅ {message}"))
            self._refresh_version_display()
            QMessageBox.information(self, fix_emojis("Установка Xray-core"), fix_emojis(message))
        else:
            self.append_log(fix_emojis(f"❌ {message}"))
            QMessageBox.warning(self, fix_emojis("Установка Xray-core"), fix_emojis(message))

    def auto_check_updates(self):
        # FreeBSD: ZIP-обновления нет. Xray не найден -> предлагаем pkg; найден -> только подсказка в лог
        if platform.system() == 'FreeBSD':
            if not find_xray_binary():
                self.append_log(fix_emojis("🔄 Xray-core не найден. На FreeBSD он ставится через pkg."))
                self._offer_pkg_install_xray()
            else:
                self.append_log(fix_emojis("ℹ️ FreeBSD: автообновление Xray-core недоступно, "
                                           "обновляйте через pkg upgrade xray-core"))
            return
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
            self._refresh_version_display()

    def on_update_error(self, error: str, silent: bool):
        self.append_log(fix_emojis(f"❌ {error}"))
        # FreeBSD: Xray не найден -> предлагаем pkg install вместо ZIP
        if platform.system() == 'FreeBSD' and not find_xray_binary():
            self._offer_pkg_install_xray()
            return
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
            self._refresh_version_display()
            QMessageBox.information(self, fix_emojis("Обновление Xray-core"), fix_emojis(message))
        else:
            QMessageBox.warning(self, fix_emojis("Ошибка обновления"), fix_emojis(message))

    def _read_tunnel_mode_from_disk(self) -> str:
        settings = load_json_file(TUNNEL_SETTINGS_FILE, {})
        mode = settings.get("mode", "ru_direct ")
        if mode not in TUNNEL_MODES:
            mode = "ru_direct "
        return mode

    def _load_tunnel_settings(self):
        self.current_tunnel_mode = self._read_tunnel_mode_from_disk()
        self._update_tunnel_mode_label()
        self.log_text.append(fix_emojis(f"🔧 Режим туннелирования: {TUNNEL_MODES.get(self.current_tunnel_mode, {}).get('name ', 'Неизвестно')}"))

    def update_tunnel_mode(self, mode_key: str):
        if mode_key in TUNNEL_MODES:
            self.current_tunnel_mode = mode_key
            self._update_tunnel_mode_label()
            save_json_file(TUNNEL_SETTINGS_FILE, {
                "mode": mode_key,
                "mode_name": TUNNEL_MODES[mode_key]["name "],
                "updated": datetime.now().isoformat()
            })
            self.log_text.append(fix_emojis(f"🔄 Режим изменён: {TUNNEL_MODES[mode_key]['name ']}"))
            if self.xray_thread and self.xray_thread.isRunning():
                self.log_text.append(fix_emojis("⚠️ Перезапустите прокси для применения новых настроек маршрутизации"))

    def _save_logs_to_file(self):
        if not self.log_buffer:
            return
        now = datetime.now()
        filename = f"xraylog_{now.day:02d}_{now.month:02d}_{now.year}_{now.hour:02d}_{now.minute:02d}.txt"
        filepath = os.path.join(LOGS_DIR, filename)
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            with open(filepath, 'a', encoding='utf-8') as f:
                for entry in self.log_buffer:
                    clean_text = re.sub(r'<[^>]+>', '', entry) if '<' in entry else entry
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {clean_text}\n")
            self.log_buffer.clear()
        except Exception as e:
            print(f"❌ Ошибка записи лога: {e}")

    def append_log(self, text):
        try:
            text = fix_emojis(str(text))
            self.log_buffer.append(text)
            if self.log_timer is None:
                self.log_timer = QTimer()
                self.log_timer.timeout.connect(self._save_logs_to_file)
                self.log_timer.start(60000)
            if "ПРЕДУПРЕЖДЕНИЕ" in text or "❌" in text or "ERROR" in text.upper():
                txt = f"<span style='color:#ff6b6b;font-weight:bold'>{text}</span>"
            elif "✅" in text or "🟢" in text:
                txt = f"<span style='color:#51cf66'>{text}</span>"
            elif "⚠️" in text or "🔴" in text or "CRITICAL" in text:
                txt = f"<span style='color:#ffa94d'>{text}</span>"
            elif "🔄" in text or "📡" in text or "⏳" in text or "📦" in text or "📥" in text:
                txt = f"<span style='color:#00bcd4'>{text}</span>"
            else:
                txt = f"<span style='color:#888888'>{text}</span>"
            self.log_text.append(txt)
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        except AttributeError:
            print(f"[LOG] {text}")

    def cleanup_all(self):
        if self.log_timer and self.log_timer.isActive():
            self.log_timer.stop()
            self._save_logs_to_file()
        if hasattr(self, '_version_sync_timer') and self._version_sync_timer.isActive():
            self._version_sync_timer.stop()
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
        if hasattr(self, 'theme_monitor') and self.theme_monitor.isRunning():
            self.theme_monitor.stop()
            self.theme_monitor.wait(1000)
        if hasattr(self, 'server_checker') and self.server_checker and self.server_checker.isRunning():
            self.server_checker.stop()
            self.server_checker.wait(1000)

    def send_hwid_to_server(self, server_url: str, silent: bool = False) -> bool:
        metadata = get_hwid_metadata()
        hwid = metadata['hwid']
        if not silent:
            self.append_log(fix_emojis(f"🔑 Отправка HWID на сервер: {hwid}"))
        try:
            data = {
                "hwid": hwid,
                "client": "BobcatProxy",
                "version": "3.0",
                "timestamp": datetime.now().isoformat()
            }
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                server_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': get_current_useragent(),
                    'x-hwid': hwid,
                    'x-device-os': metadata['device_os'],
                    'x-ver-os': metadata['ver_os'],
                    'x-device-model': metadata['device_model']
                },
                method='POST'
            )
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                response_data = response.read().decode('utf-8')
                if not silent:
                    self.append_log(fix_emojis(f"✅ HWID отправлен успешно (код: {response.getcode()})"))
                    self.append_log(fix_emojis(f"📝 Ответ сервера: {response_data[:200]}..."))
                return True
        except Exception as e:
            if not silent:
                self.append_log(fix_emojis(f"❌ Ошибка отправки HWID: {str(e)}"))
            return False

    def show_hwid_info(self):
        metadata = get_hwid_metadata()
        hwid = metadata['hwid']
        msg = (
            f"🔑 Hardware ID (HWID):\n\n"
            f"HWID (UUID): {hwid}\n"
            f"Device OS: {metadata['device_os']}\n"
            f"OS Version: {metadata['ver_os']}\n"
            f"Device Model: {metadata['device_model']}\n\n"
            f"ℹ️ HWID генерируется автоматически:\n"
            f"• Формат: UUID (8-4-4-4-12)\n"
            f"• Алгоритм: SHA-256 с солью 'bobcat_hwid_'\n"
            f"• Основа: уникальные характеристики устройства\n\n"
            f"📌 Используется для идентификации клиента на сервере\n"
            f"и отправляется в заголовках x-hwid при обновлении подписок."
        )
        QMessageBox.information(self, fix_emojis("Информация о HWID"), fix_emojis(msg))

    def copy_hwid_to_clipboard(self):
        hwid = get_cached_hwid_full()
        clipboard = QApplication.clipboard()
        clipboard.setText(hwid)
        self.append_log(fix_emojis(f"📋 HWID скопирован в буфер обмена: {hwid}"))
        QMessageBox.information(
            self,
            fix_emojis("HWID скопирован"),
            fix_emojis(f"HWID скопирован в буфер обмена:\n{hwid}")
        )

    def _show_hwid_send_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(fix_emojis("🔑 Отправка HWID на сервер"))
        dialog.setMinimumSize(450, 250)
        dialog.setFont(QFont("Arial"))
        layout = QVBoxLayout(dialog)
        info = QLabel(fix_emojis("Введите URL сервера для отправки HWID:"))
        info.setStyleSheet("font-weight: bold;")
        layout.addWidget(info)
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://example.com/api/hwid")
        layout.addWidget(url_input)
        hwid_metadata = get_hwid_metadata()
        hwid_label = QLabel(fix_emojis(f"HWID: {hwid_metadata['hwid']}\n"
                                       f"Device OS: {hwid_metadata['device_os']}\n"
                                       f"Device Model: {hwid_metadata['device_model']}"))
        hwid_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        hwid_label.setWordWrap(True)
        layout.addWidget(hwid_label)
        btn_layout = QHBoxLayout()
        send_btn = QPushButton(fix_emojis("📤 Отправить"))
        cancel_btn = QPushButton("Отмена")

        def on_send():
            url = url_input.text().strip()
            if not url.startswith(('http://', 'https://')):
                QMessageBox.warning(dialog, fix_emojis("Ошибка"), fix_emojis("Введите корректный URL!"))
                return
            send_btn.setEnabled(False)
            send_btn.setText(fix_emojis("⏳ Отправка..."))
            QApplication.processEvents()
            success = self.send_hwid_to_server(url)
            send_btn.setEnabled(True)
            send_btn.setText(fix_emojis("📤 Отправить"))
            if success:
                QMessageBox.information(dialog, fix_emojis("Успех"), fix_emojis("HWID успешно отправлен на сервер!"))
                dialog.accept()

        send_btn.clicked.connect(on_send)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(send_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        examples_label = QLabel(fix_emojis("Примеры: https://your-server.com/api/hwid"))
        examples_label.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(examples_label)
        dialog.exec()

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
        self.btn_check_servers = QPushButton(fix_emojis("🔍 Проверить серверы"))
        self.btn_check_servers.clicked.connect(self.check_servers)
        self.btn_check_servers.setToolTip(fix_emojis("Проверить все серверы через Xray API (observatory)"))
        self.chk_system_proxy = QCheckBox(fix_emojis("Системный прокси"))
        self.chk_system_proxy.setChecked(False)
        top_bar_layout.addWidget(self.btn_settings)
        top_bar_layout.addWidget(self.btn_subs_manager)
        top_bar_layout.addWidget(self.btn_check_updates)
        top_bar_layout.addWidget(self.btn_check_servers)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.chk_system_proxy)
        left_layout.addLayout(top_bar_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedHeight(20)
        left_layout.addWidget(self.progress_bar)

        version_text = f"Xray-core: v{XRAY_VERSION} | Канал: {UPDATE_CHANNELS[self.current_update_channel]['name ']}"
        self.version_label = QLabel(version_text)
        self.version_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")

        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows ")
            if preset_key == "custom ":
                ua_text = "🌐 UA: Свой"
            else:
                ua_text = f"🌐 UA: {USERAGENT_PRESETS.get(preset_key, {}).get('name ', 'Chrome')}"
        else:
            ua_text = "🌐 UA: Стандартный"
        self.ua_label = QLabel(fix_emojis(ua_text))
        self.ua_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")
        self.ua_label.setToolTip(get_current_useragent())

        version_ua_layout = QHBoxLayout()
        version_ua_layout.setContentsMargins(0, 0, 0, 0)
        version_ua_layout.setSpacing(8)
        version_ua_layout.addWidget(self.version_label)
        version_ua_layout.addWidget(self.ua_label)
        version_ua_layout.addStretch()
        left_layout.addLayout(version_ua_layout)

        update_via_proxy = load_update_via_proxy_settings()
        self.proxy_update_label = QLabel(fix_emojis(f"🔌 Подписки через VPN: {'ВКЛ' if update_via_proxy else 'ВЫКЛ'}"))
        self.proxy_update_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")
        self.proxy_update_label.setToolTip(fix_emojis("Обновление подписок через VPN: включено" if update_via_proxy else "Обновление подписок через VPN: выключено"))

        doh_settings = load_doh_settings()
        doh_active = doh_settings.get("enabled", False)
        doh_text = "🌐 DoH: " + ("ВКЛ" if doh_active else "ВЫКЛ")
        self.doh_label = QLabel(fix_emojis(doh_text))
        self.doh_label.setStyleSheet("color: #888; font-size: 8pt; padding: 2px;")
        if doh_active:
            provider = doh_settings.get("provider", "cloudflare ")
            if provider == "custom ":
                pname = "Свой"
            else:
                pname = DOH_PROVIDERS.get(provider, {}).get("name ", provider)
            self.doh_label.setToolTip(fix_emojis(f"DoH включён: {pname}"))
        else:
            self.doh_label.setToolTip(fix_emojis("DoH отключён"))

        proxy_doh_layout = QHBoxLayout()
        proxy_doh_layout.setContentsMargins(0, 0, 0, 0)
        proxy_doh_layout.setSpacing(8)
        proxy_doh_layout.addWidget(self.proxy_update_label)
        proxy_doh_layout.addWidget(self.doh_label)
        proxy_doh_layout.addStretch()
        left_layout.addLayout(proxy_doh_layout)

        self.keys_tabs = QTabWidget()

        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        self.key_selector_all = QComboBox()
        self.key_selector_all.setEditable(False)
        self.key_selector_all.currentIndexChanged.connect(self._on_key_selected)
        all_layout.addWidget(self.key_selector_all)
        self.keys_tabs.addTab(all_tab, fix_emojis("📋 Все"))

        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        self.key_selector_manual = QComboBox()
        self.key_selector_manual.setEditable(False)
        self.key_selector_manual.currentIndexChanged.connect(
            lambda: self._on_key_selected_tab("manual"))
        manual_layout.addWidget(self.key_selector_manual)
        self.keys_tabs.addTab(manual_tab, fix_emojis("✋ Ручные"))

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
        self.keys_tabs.addTab(sub_tab, fix_emojis("📡 Подписки"))

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

        # НОВОЕ: Панель фильтрации и сортировки
        filter_sort_layout = QHBoxLayout()
        self.chk_only_working = QCheckBox(fix_emojis("🟢 Только рабочие"))
        self.chk_only_working.setToolTip(fix_emojis("Показывать в списке только серверы, прошедшие проверку"))
        self.chk_only_working.stateChanged.connect(self.refresh_keys_list)
        filter_sort_layout.addWidget(self.chk_only_working)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem(fix_emojis("Без сортировки"), "none")
        self.sort_combo.addItem(fix_emojis("⬇️ Рабочие сверху"), "working_first")
        self.sort_combo.setToolTip(fix_emojis("Сортировка списка серверов"))
        self.sort_combo.currentIndexChanged.connect(self.refresh_keys_list)
        filter_sort_layout.addWidget(self.sort_combo)
        filter_sort_layout.addStretch()
        keys_layout.addLayout(filter_sort_layout)

        keys_layout.addWidget(self.keys_tabs)

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
        if not hasattr(self, 'tunnel_mode_label'):
            return
        mode_info = TUNNEL_MODES.get(self.current_tunnel_mode, {})
        self.tunnel_mode_label.setText(fix_emojis(f"🔗 {mode_info.get('name ', 'Режим не выбран')}"))

    def _update_ua_label(self):
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows ")
            if preset_key == "custom ":
                ua_text = "🌐 UA: Свой"
            else:
                ua_text = f"🌐 UA: {USERAGENT_PRESETS.get(preset_key, {}).get('name ', 'Chrome')}"
        else:
            ua_text = "🌐 UA: Стандартный"
        self.ua_label.setText(fix_emojis(ua_text))
        self.ua_label.setToolTip(get_current_useragent())
        global URL_OPENER
        URL_OPENER = create_opener_with_ssl_fix()

    def _update_proxy_update_label(self):
        enabled = load_update_via_proxy_settings()
        self.proxy_update_label.setText(fix_emojis(f"🔌 Подписки через VPN: {'✅' if enabled else '❌'}"))
        self.proxy_update_label.setToolTip(fix_emojis("Обновление подписок через VPN: включено" if enabled else "Обновление подписок через VPN: выключено"))

    def _update_doh_label(self):
        settings = load_doh_settings()
        enabled = settings.get("enabled", False)
        self.doh_label.setText(fix_emojis(f"🌐 DoH: {'✅' if enabled else '❌'}"))
        if enabled:
            provider = settings.get("provider", "cloudflare ")
            if provider == "custom ":
                pname = "Свой"
            else:
                pname = DOH_PROVIDERS.get(provider, {}).get("name ", provider)
            self.doh_label.setToolTip(fix_emojis(f"DoH включён: {pname}"))
        else:
            self.doh_label.setToolTip(fix_emojis("DoH отключён"))

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

        emoji_menu = QMenu(fix_emojis("😀 Режим эмодзи"), self)
        current_emoji_mode = get_ui_settings().get("emoji_mode ", "auto ")
        emoji_modes = {
            "auto": "Авто (как поддерживает система)",
            "off": "Отключить эмодзи"
        }
        for mode_key, mode_name in emoji_modes.items():
            action = QAction(fix_emojis(mode_name), self)
            action.setCheckable(True)
            action.setChecked(mode_key == current_emoji_mode)
            action.triggered.connect(lambda checked, m=mode_key: self._change_emoji_mode(m))
            emoji_menu.addAction(action)
        menu.addMenu(emoji_menu)

        settings = get_ui_settings()
        auto_select_action = QAction(fix_emojis("🔑 Авто-выбор последнего ручного ключа"), self)
        auto_select_action.setCheckable(True)
        auto_select_action.setChecked(settings.get("auto_select_last_key ", False))
        auto_select_action.triggered.connect(self._toggle_auto_select_last_key)
        menu.addAction(auto_select_action)
        menu.addSeparator()

        ua_action = QAction(fix_emojis("🌐 Настройка User-Agent"), self)
        ua_action.triggered.connect(self.show_useragent_settings)
        menu.addAction(ua_action)

        clash_action = QAction(fix_emojis("🧩 Парсер Clash"), self)
        clash_action.triggered.connect(self.show_clash_parser_settings)
        menu.addAction(clash_action)
        menu.addSeparator()

        tunnel_action = QAction(fix_emojis("🔐 Маршрутизация"), self)
        tunnel_action.triggered.connect(self.show_tunneling_settings)
        menu.addAction(tunnel_action)
        menu.addSeparator()

        update_proxy_action = QAction(fix_emojis("🔌 Обновление подписок через VPN"), self)
        update_proxy_action.triggered.connect(self.show_update_via_proxy_settings)
        menu.addAction(update_proxy_action)

        doh_action = QAction(fix_emojis("🌐 DNS over HTTPS (DoH)"), self)
        doh_action.triggered.connect(self.show_doh_settings)
        menu.addAction(doh_action)
        menu.addSeparator()

        frame_action = QAction(fix_emojis("🪟 Скрыть рамку окна"), self)
        frame_action.setCheckable(True)
        frame_action.setChecked(settings.get("hide_window_frame ", False))
        frame_action.triggered.connect(self._toggle_window_frame)
        menu.addAction(frame_action)
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

        hwid_menu = QMenu(fix_emojis("🔑 HWID"), self)
        show_hwid_action = QAction(fix_emojis("📋 Показать HWID"), self)
        show_hwid_action.triggered.connect(self.show_hwid_info)
        hwid_menu.addAction(show_hwid_action)
        copy_hwid_action = QAction(fix_emojis("📋 Копировать HWID"), self)
        copy_hwid_action.triggered.connect(self.copy_hwid_to_clipboard)
        hwid_menu.addAction(copy_hwid_action)
        send_hwid_action = QAction(fix_emojis("📤 Отправить HWID на сервер"), self)
        send_hwid_action.triggered.connect(self._show_hwid_send_dialog)
        hwid_menu.addAction(send_hwid_action)
        menu.addMenu(hwid_menu)
        menu.addSeparator()

        about_action = QAction(fix_emojis("ℹ️ О программе"), self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        menu.exec(self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft()))

    def show_clash_parser_settings(self):
        """Открывает диалог выбора парсера Clash и пишет выбранный режим в лог."""
        dialog = ClashParserSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.append_log(fix_emojis(f"🧩 Парсер Clash: {get_clash_parser_mode()}"))

    def show_useragent_settings(self):
        dialog = UserAgentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_ua_label()
            ua = get_current_useragent()
            self.append_log(fix_emojis(f"🌐 User-Agent изменён: {ua[:60]}..."))
            global URL_OPENER
            URL_OPENER = create_opener_with_ssl_fix()

    def show_update_via_proxy_settings(self):
        dialog = UpdateViaProxyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_proxy_update_label()
            enabled = load_update_via_proxy_settings()
            self.append_log(fix_emojis(f"🔌 Обновление подписок через VPN: {'включено' if enabled else 'выключено'}"))

    def show_doh_settings(self):
        dialog = DoHSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_doh_label()
            settings = load_doh_settings()
            if settings.get("enabled"):
                provider = settings.get("provider", "cloudflare ")
                if provider == "custom ":
                    pname = "Свой DoH-сервер"
                else:
                    pname = DOH_PROVIDERS.get(provider, {}).get("name ", provider)
                self.append_log(fix_emojis(f"🌐 DoH включён: {pname}"))
            else:
                self.append_log(fix_emojis("🌐 DoH отключён"))

    def show_update_settings(self):
        dialog = UpdateSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_update_channel = self._get_update_channel()
            channel_name = UPDATE_CHANNELS[self.current_update_channel]['name ']
            self.append_log(fix_emojis(f"📡 Канал обновлений изменён: {channel_name}"))
            self._refresh_version_display()

    def show_tunneling_settings(self):
        dialog = TunnelingSettingsDialog(self)
        dialog.exec()

    def update_geo_files(self):
        self.log_text.append(fix_emojis("🔄 Обновление GeoIP/GeoSite..."))
        success = ensure_geoip_file(DATA_DIR)
        for mode_key in TUNNEL_MODES:
            if TUNNEL_MODES[mode_key].get("file ") is not None:
                if ensure_geosite_file(mode_key, DATA_DIR):
                    success = True
        if success:
            self.log_text.append(fix_emojis("✅ Файлы обновлены"))
        else:
            self.log_text.append(fix_emojis("❌ Ошибка обновления файлов"))

    def show_about(self):
        ua_settings = load_useragent_settings()
        if ua_settings.get("enabled", True):
            preset_key = ua_settings.get("preset", "chrome_windows ")
            if preset_key == "custom ":
                ua_info = "Свой User-Agent"
            else:
                ua_info = USERAGENT_PRESETS.get(preset_key, {}).get("name ", "Неизвестно")
        else:
            ua_info = "Стандартный"
        hwid_metadata = get_hwid_metadata()
        update_via_proxy = load_update_via_proxy_settings()
        doh_settings = load_doh_settings()
        doh_status = "включён" if doh_settings.get("enabled") else "выключен"
        QMessageBox.information(
            self, fix_emojis("О программе"),
            fix_emojis(f"Bobcat Proxy 3.0 pre3  \n\n"
                       f"Клиент для Xray-core с поддержкой:\n"
                       f"• VLESS/VMess/Trojan\n"
                       f"• Hysteria / Hysteria2\n"
                       f"• Автообновление подписок\n"
                       f"• Обновление подписок через VPN (настраивается)\n"
                       f"• DNS over HTTPS для обхода DNS-блокировок\n"
                       f"• Гибкая маршрутизация (включая режим 'Всё в VPN')\n"
                       f"• Автоматическое обновление Xray-core\n"
                       f"• Выбор канала обновлений (стабильный/пре-релиз)\n"
                       f"• Настройка User-Agent\n"
                       f"• Проверка работоспособности серверов с детальной диагностикой\n"
                       f"• Сохранение статусов работоспособности серверов\n"
                       f"• Сортировка и фильтрация списка серверов\n"
                       f"• Кроссплатформенность (Linux/Windows/FreeBSD)\n"
                       f"• Поддержка HWID\n"
                       f"• Опциональное скрытие рамки окна (для TWM)\n"
                       f"• Режимы эмодзи (авто/полное отключение)\n"
                       f"• Авто-выбор последнего ручного ключа (опционально)\n\n"
                       f"Xray-core версия: {XRAY_VERSION}\n"
                       f"Канал обновлений: {UPDATE_CHANNELS[self.current_update_channel]['name ']}\n"
                       f"User-Agent: {ua_info}\n"
                       f"Обновление подписок через VPN: {'включено' if update_via_proxy else 'выключено'}\n"
                       f"DNS over HTTPS (DoH): {doh_status}\n"
                       f"HWID: {hwid_metadata['hwid']}\n"
                       f"Device OS: {hwid_metadata['device_os']}\n"
                       f"OS Version: {hwid_metadata['ver_os']}\n"
                       f"Device Model: {hwid_metadata['device_model']}\n\n"
                       f"https://github.com/XTLS/Xray-core\n"
                       f"Сообщить о багах: BugreportBobcatProxy@protonmail.com\n\n")
        )

    def _on_key_selected(self, index: int):
        self.current_tab = "all"
        self.current_key_index = index
        self._update_status_info()

    def _on_key_selected_tab(self, source: str):
        self.current_tab = "filtered"
        self.current_source_filter = source
        self._update_status_info()

    # ИЗМЕНЕНО: теперь использует _get_selected_key_data
    def _update_status_info(self):
        key_data = self._get_selected_key_data()
        if key_data:
            source = "✋ Ручной" if key_data.get("source") == "manual" else "📡 Подписка"
            status_str = ""
            if key_data.get("is_working") is True:
                status_str = " | 🟢 Рабочий"
            elif "is_working" in key_data and key_data["is_working"] is False:
                status_str = " | 🔴 Нерабочий"
            self.status_info.setText(fix_emojis(f"{source}{status_str} | Добавлен: {key_data.get('added', '?')[:16]}"))
        else:
            self.status_info.setText("")

    def _get_current_keys_list(self) -> list:
        if self.current_tab == "all":
            return self.sub_manager.keys
        elif self.current_tab == "filtered":
            return self.sub_manager.get_keys_by_source(self.current_source_filter)
        return self.sub_manager.keys

    # НОВОЕ: безопасное получение выбранного ключа по ID
    def _get_selected_key_data(self) -> Optional[dict]:
        """Безопасно получает данные выбранного ключа по его ID, игнорируя сортировку/фильтр."""
        if self.current_tab == "all":
            combo = self.key_selector_all
        elif self.current_source_filter == "manual":
            combo = self.key_selector_manual
        else:
            combo = self.key_selector_sub

        key_id = combo.currentData(Qt.ItemDataRole.UserRole)
        if not key_id:
            return None
        for k in self.sub_manager.keys:
            if k.get("id") == key_id:
                return k
        return None

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

    # ИЗМЕНЕНО: с фильтрацией, сортировкой и сохранением выбора через UserRole
    def refresh_keys_list(self):
        # 1. Сохраняем ID текущих выбранных ключей
        sel_all = self.key_selector_all.currentData(Qt.ItemDataRole.UserRole)
        sel_man = self.key_selector_manual.currentData(Qt.ItemDataRole.UserRole)
        sel_sub = self.key_selector_sub.currentData(Qt.ItemDataRole.UserRole)

        self.key_selector_all.clear()
        self.key_selector_manual.clear()
        self.key_selector_sub.clear()

        all_keys = list(self.sub_manager.keys)
        manual_keys = self.sub_manager.get_keys_by_source("manual")
        sub_keys = self.sub_manager.get_keys_by_source("subscription")

        # 2. Применяем фильтр
        only_working = self.chk_only_working.isChecked()
        if only_working:
            all_keys = [k for k in all_keys if k.get('is_working') is True]
            manual_keys = [k for k in manual_keys if k.get('is_working') is True]
            sub_keys = [k for k in sub_keys if k.get('is_working') is True]

        # 3. Применяем сортировку (стабильная, рабочие сверху)
        sort_mode = self.sort_combo.currentData()
        if sort_mode == "working_first":
            all_keys = sorted(all_keys, key=lambda k: not k.get('is_working', False))
            manual_keys = sorted(manual_keys, key=lambda k: not k.get('is_working', False))
            sub_keys = sorted(sub_keys, key=lambda k: not k.get('is_working', False))

        # 4. Вспомогательная функция для заполнения комбобоксов
        def populate_combo(combo, keys_list, add_sub_name=False):
            for i, key_data in enumerate(keys_list):
                display_text = fix_emojis(self._format_key_display(key_data, i))
                if add_sub_name:
                    sub_name = self._get_sub_name_by_url(key_data.get('sub_url'))
                    display_text = f"[{sub_name}] {display_text.split('. ', 1)[-1]}"
                combo.addItem(display_text)
                combo.setItemData(i, key_data["id"], Qt.ItemDataRole.UserRole)
                tooltip = key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"]
                combo.setItemData(i, tooltip, Qt.ItemDataRole.ToolTipRole)

        populate_combo(self.key_selector_all, all_keys)
        populate_combo(self.key_selector_manual, manual_keys)
        populate_combo(self.key_selector_sub, sub_keys, add_sub_name=True)

        # 5. Восстанавливаем выбор пользователя
        def restore_selection(combo, saved_id):
            if saved_id:
                for i in range(combo.count()):
                    if combo.itemData(i, Qt.ItemDataRole.UserRole) == saved_id:
                        combo.setCurrentIndex(i)
                        return
            if combo.count() > 0:
                combo.setCurrentIndex(0)

        restore_selection(self.key_selector_all, sel_all)
        restore_selection(self.key_selector_manual, sel_man)
        restore_selection(self.key_selector_sub, sel_sub)

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

        # Применяем фильтр и сортировку
        only_working = self.chk_only_working.isChecked()
        if only_working:
            keys = [k for k in keys if k.get('is_working') is True]
        sort_mode = self.sort_combo.currentData()
        if sort_mode == "working_first":
            keys = sorted(keys, key=lambda k: not k.get('is_working', False))

        self.key_selector_sub.clear()
        for i, key_data in enumerate(keys):
            display_text = fix_emojis(self._format_key_display(key_data, i))
            sub_name = self._get_sub_name_by_url(key_data.get('sub_url'))
            full_text = f"[{sub_name}] {display_text.split('. ', 1)[-1]}"
            self.key_selector_sub.addItem(full_text)
            self.key_selector_sub.setItemData(i, key_data["id"], Qt.ItemDataRole.UserRole)
            tooltip = key_data["key"][:500] + "..." if len(key_data["key"]) > 500 else key_data["key"]
            self.key_selector_sub.setItemData(i, tooltip, Qt.ItemDataRole.ToolTipRole)

    def refresh_subs_list(self):
        active = len([s for s in self.sub_manager.subscriptions if s.get("enabled")])
        if active > 0:
            self.log_text.append(fix_emojis(f"📡 Активно подписок: {active}"))

    # ИЗМЕНЕНО: использует _get_selected_key_data
    def delete_selected_key(self):
        key_data = self._get_selected_key_data()
        if not key_data:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Нет выбранного ключа!"))
            return
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

    def _parse_clash(self, data: str, depth: int = 0) -> List[str]:
        fetcher = SubscriptionUpdateWorker(self.sub_manager, self)
        return parse_clash_subscription(
            data,
            fetch=lambda url: fetcher._fetch_url_with_ssl_fix(url, False),
            parse_nested=lambda body: self._parse_subscription_data(body, depth + 1),
            log=lambda msg: self.log_text.append(fix_emojis(msg)),
            depth=depth,
        )

    def _parse_clash_v2(self, data: str) -> List[str]:
        """Разбор Clash-подписки парсером v2. Лог — в self.log_text; у XrayClient нет флага self.running,
        поэтому should_stop всегда False."""
        fetcher = SubscriptionUpdateWorker(self.sub_manager, self)
        return parse_clash_subscription_v2(
            data,
            log=lambda msg: self.log_text.append(fix_emojis(msg)),
            should_stop=lambda: False,
            max_depth=2,
            fetch=lambda url: fetcher._fetch_url_with_ssl_fix(url, False),
        )

    def _parse_subscription_data(self, data: str, _depth: int = 0) -> List[str]:
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
                        if item.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://')):
                            valid_keys.append(item)
                        elif isinstance(item, dict) and "outbounds" in item:
                            valid_keys.append(json.dumps(item, ensure_ascii=False))
            elif isinstance(json_data, dict):
                for value in json_data.values():
                    if isinstance(value, str) and value.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://')):
                        valid_keys.append(value.strip())
            if valid_keys:
                return valid_keys
        except json.JSONDecodeError:
            pass
        if looks_like_clash(data):
            if get_clash_parser_mode() == "v2":
                return self._parse_clash_v2(data)
            return self._parse_clash(data, _depth)
        try:
            padded = data + '=' * (-len(data) % 4)
            decoded = base64.b64decode(padded).decode('utf-8')
            if looks_like_clash(decoded):
                if get_clash_parser_mode() == "v2":
                    return self._parse_clash_v2(decoded)
                return self._parse_clash(decoded, _depth)
            lines = [l.strip() for l in decoded.splitlines() if l.strip()]
            valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://'))]
            if valid_keys:
                return valid_keys
        except Exception:
            pass
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        valid_keys = [l for l in lines if l.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://'))]
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
            self._apply_auto_select_last_key()
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
                    self._apply_auto_select_last_key()
                    return
                else:
                    self.log_text.append(fix_emojis("❌ Неверный JSON: отсутствуют outbounds/inbounds"))
                    return
            except json.JSONDecodeError:
                self.log_text.append(fix_emojis("❌ Ошибка парсинга JSON"))
                return
        # SS-removed: ss:// не добавляется, одна строка в лог, без QMessageBox
        if text.lower().startswith('ss://'):
            self.log_text.append(fix_emojis("ℹ️ Shadowsocks не поддерживается и пропущен."))
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
            if text.startswith(('vmess://', 'vless://', 'trojan://', 'hysteria://', 'hysteria2://')):
                if self.sub_manager.add_manual_key(text):
                    self.log_text.append(fix_emojis("✅ Ключ добавлен"))
                else:
                    self.log_text.append(fix_emojis("⚠️ Ключ уже в списке"))
            else:
                self.log_text.append(fix_emojis("❌ Неверный формат ключа"))
        self.sub_manager._save_keys()
        self.refresh_keys_list()
        self.key_input.clear()
        self._apply_auto_select_last_key()

    def import_subscription_once(self):
        url = self.sub_url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Введите корректный URL!"))
            return
        self.log_text.append(fix_emojis("📥 Импорт подписки..."))
        try:
            metadata = get_hwid_metadata()
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': get_current_useragent(),
                    'x-hwid': metadata['hwid'],
                    'x-device-os': metadata['device_os'],
                    'x-ver-os': metadata['ver_os'],
                    'x-device-model': metadata['device_model']
                }
            )
            if doh_enabled_for_subscriptions():
                self.log_text.append(fix_emojis("🌐 Импорт через DoH"))
                with DoHContext(timeout=load_doh_settings().get("timeout", 10)) as doh_opener:
                    if doh_opener is not None:
                        with doh_opener.open(req, timeout=30) as response:
                            data = response.read().decode('utf-8')
                    else:
                        with URL_OPENER.open(req, timeout=30) as response:
                            data = response.read().decode('utf-8')
            else:
                with URL_OPENER.open(req, timeout=30) as response:
                    data = response.read().decode('utf-8')
            # SS-removed: один раз за импорт сообщаем о пропуске ss://
            if _contains_ss_link(data):
                self.log_text.append(fix_emojis("ℹ️ Shadowsocks пропущен (не поддерживается)"))
            valid_keys = self._parse_subscription_data(data)
            count = 0
            for key_str in valid_keys:
                if self.sub_manager.add_manual_key(key_str):
                    count += 1
            self.log_text.append(fix_emojis(f"✅ Импортировано {count} ключей"))
            self.sub_manager._save_keys()
            self.refresh_keys_list()
            self._apply_auto_select_last_key()
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Ошибка импорта: {e}"))
        self.sub_url_input.clear()

    def update_subscription_now(self, sub: dict):
        if not sub:
            return
        send_hwid = sub.get("send_hwid", True)
        hwid_status = "🔑 с HWID" if send_hwid else "🚫 без HWID"
        self.log_text.append(fix_emojis(f"🔄 Обновление: {sub.get('name', sub['url'])} {hwid_status}"))
        try:
            headers = {
                'User-Agent': get_current_useragent()
            }
            if send_hwid:
                metadata = get_hwid_metadata()
                headers['x-hwid'] = metadata['hwid']
                headers['x-device-os'] = metadata['device_os']
                headers['x-ver-os'] = metadata['ver_os']
                headers['x-device-model'] = metadata['device_model']
                self.log_text.append(fix_emojis(f"🔑 Отправлен HWID: {metadata['hwid'][:8]}..."))
            use_proxy = load_update_via_proxy_settings()
            proxy_running = is_proxy_running(self)
            if use_proxy and proxy_running:
                proxy_handler = urllib.request.ProxyHandler({
                    'http': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}',
                    'https': f'socks5h://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}'
                })
                opener = urllib.request.build_opener(proxy_handler)
                self.log_text.append(fix_emojis("🔌 Обновление через VPN"))
                req = urllib.request.Request(sub["url"], headers=headers)
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with opener.open(req, timeout=30, context=ctx) as response:
                    data = response.read().decode('utf-8')
            elif doh_enabled_for_subscriptions():
                self.log_text.append(fix_emojis("🌐 Обновление через DoH"))
                req = urllib.request.Request(sub["url"], headers=headers)
                with DoHContext(timeout=load_doh_settings().get("timeout", 10)) as doh_opener:
                    if doh_opener is not None:
                        with doh_opener.open(req, timeout=30) as response:
                            data = response.read().decode('utf-8')
                    else:
                        with URL_OPENER.open(req, timeout=30) as response:
                            data = response.read().decode('utf-8')
            else:
                opener = URL_OPENER
                if use_proxy and not proxy_running:
                    self.log_text.append(fix_emojis("⚠️ VPN выключен, обновление напрямую"))
                req = urllib.request.Request(sub["url"], headers=headers)
                with opener.open(req, timeout=30) as response:
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
        self.sub_update_worker = SubscriptionUpdateWorker(self.sub_manager, self)
        self.sub_update_worker.log_signal.connect(self.append_log)
        self.sub_update_worker.progress_signal.connect(
            lambda name, cur, total: self.log_text.append(fix_emojis(f"⏳ {name}: {cur}/{total}")))
        self.sub_update_worker.start()
        self.log_text.append(fix_emojis("📡 Автообновление подписок: АКТИВНО"))

    def _build_routing_rules(self, tunnel_mode: str) -> List[dict]:
        rules = []
        if tunnel_mode == "all_vpn ":
            rules.append({
                "type": "field",
                "outboundTag": "proxy",
                "network": "tcp,udp"
            })
        elif tunnel_mode == "ru_direct ":
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
        elif tunnel_mode == "blocked_tunnel ":
            domains = load_geosite_domains(RU_BLOCKED_PATH, "blocked_tunnel ")
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
        if key_string.startswith("hysteria://"):
            return self._parse_hysteria(key_string)
        if key_string.startswith("hysteria2://"):
            return self._parse_hysteria2(key_string)
        if key_string.startswith("vless://"):
            return self._parse_vless(key_string)
        elif key_string.startswith("vmess://"):
            return self._parse_vmess(key_string)
        elif key_string.startswith("trojan://"):
            return self._parse_trojan(key_string)
        # SS-removed: ветка ss:// удалена
        self.log_text.append(fix_emojis("❌ Неподдерживаемый формат"))
        return False

    def _parse_hysteria(self, key_string):
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(key_string)
            if not parsed.hostname or not parsed.port:
                raise ValueError("Invalid Hysteria URL: missing host or port")
            host = parsed.hostname
            port = parsed.port
            params = parse_qs(parsed.query)
            get = lambda n, d='': params.get(n, [d])[0]
            auth = get('auth', '')
            peer = get('peer', '') or host
            insecure = get('insecure', '0') == '1'
            up = get('up', '10')
            down = get('down', '50')
            obfs = get('obfs', '')
            obfs_password = get('obfs-password', '')
            if insecure:
                warning_msg = ("Из соображений безопасности, запуск конфига с insecure=true невозможен. "
                               "Использование insecure подвергает ваш трафик риску перехвата. "
                               "Обратитесь к VPN-провайдеру за безопасной конфигурацией.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            stream_settings = {
                "network": "udp",
                "security": "tls",
                "tlsSettings": {
                    "allowInsecure": False,
                    "serverName": peer,
                    "fingerprint": "chrome"
                }
            }
            if obfs:
                stream_settings["hysteriaSettings"] = {
                    "obfs": obfs,
                    "obfsPassword": obfs_password
                }
            outbound_settings = {
                "servers": [{
                    "address": host,
                    "port": port,
                    "auth": auth,
                    "up": up,
                    "down": down
                }]
            }
            return self._build_config(
                outbound_settings,
                stream_settings,
                f"{host}:{port} (Hysteria)",
                protocol="hysteria"
            )
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Hysteria ошибка: {e}"))
            return False

    def _parse_hysteria2(self, key_string):
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(key_string)
            if not parsed.hostname or not parsed.port:
                raise ValueError("Invalid Hysteria2 URL: missing host or port")
            host = parsed.hostname
            port = parsed.port
            params = parse_qs(parsed.query)
            get = lambda n, d='': params.get(n, [d])[0]
            auth = parsed.username or ''
            peer = get('peer', '') or host
            insecure = get('insecure', '0') == '1'
            up = get('up', '10')
            down = get('down', '50')
            obfs = get('obfs', '')
            obfs_password = get('obfs-password', '')
            sni = get('sni', peer)
            if insecure:
                warning_msg = ("Из соображений безопасности, запуск конфига с insecure=true невозможен. "
                               "Использование insecure подвергает ваш трафик риску перехвата.")
                self.log_text.append(fix_emojis(f"🔴 {warning_msg}"))
                return False
            stream_settings = {
                "network": "udp",
                "security": "tls",
                "tlsSettings": {
                    "allowInsecure": False,
                    "serverName": sni,
                    "fingerprint": "chrome"
                }
            }
            if obfs:
                stream_settings["hysteria2Settings"] = {
                    "obfs": obfs,
                    "obfsPassword": obfs_password
                }
            outbound_settings = {
                "servers": [{
                    "address": host,
                    "port": port,
                    "auth": auth,
                    "up": up,
                    "down": down
                }]
            }
            return self._build_config(
                outbound_settings,
                stream_settings,
                f"{host}:{port} (Hysteria2)",
                protocol="hysteria2"
            )
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Hysteria2 ошибка: {e}"))
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
                warning_msg = ("Запуск с параметром security=none невозможен . Такое соединение не скрывает что вы делаете в сети !!!")
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

    # SS-removed: разбор SS-ключа в конфиг клиента удалён

    def _build_config(self, outbound_settings, stream_settings, server_info, protocol="vless"):
        proto_map = {
            "trojan": "trojan",
            "hysteria": "hysteria",
            "hysteria2": "hysteria2"
        }
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
            mode_name = TUNNEL_MODES.get(self.current_tunnel_mode, {}).get('name ', 'Неизвестно')
            loglevel = self._get_xray_loglevel()
            self.log_text.append(fix_emojis(f"✅ Конфиг: {server_info} | 🔗 {mode_name} | 📋 loglevel: {loglevel}"))
            return True
        except Exception as e:
            self.log_text.append(fix_emojis(f"❌ Ошибка сохранения: {e}"))
            return False

    def check_servers(self):
        if hasattr(self, 'server_checker') and self.server_checker and self.server_checker.isRunning():
            reply = QMessageBox.question(
                self,
                fix_emojis("Остановить проверку?"),
                fix_emojis("Проверка серверов уже выполняется.\n\n"
                           "Остановить проверку и сохранить результаты уже проверенных серверов?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_server_check()
            return
        keys = self.sub_manager.keys
        if not keys:
            QMessageBox.warning(self, fix_emojis("Внимание"), fix_emojis("Нет серверов для проверки!"))
            return
        if not (self.xray_thread and self.xray_thread.isRunning()):
            reply = QMessageBox.question(
                self, fix_emojis("Прокси не запущен"),
                fix_emojis("Для проверки серверов необходимо запустить прокси.\n\n"
                           "Запустить прокси сейчас?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                current_idx = self.key_selector_all.currentIndex()
                if current_idx >= 0:
                    self.toggle_proxy()
                    QTimer.singleShot(3000, self._start_check_servers)
                else:
                    QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Выберите ключ для запуска прокси!"))
            return
        else:
            self._start_check_servers()

    def _stop_server_check(self):
        if hasattr(self, 'server_checker') and self.server_checker:
            try:
                self.server_checker.finished_signal.disconnect()
                self.server_checker.partial_signal.disconnect()
            except:
                pass
            self.server_checker.stop()
            self.server_checker.wait(2000)
            if hasattr(self.server_checker, 'working_servers') and self.server_checker.working_servers:
                dialog = CheckResultDialog(self.server_checker.working_servers, self, partial=True)
                dialog.exec()
                self.append_log(fix_emojis(f"⏸️ Проверка остановлена. Найдено рабочих серверов: {len(self.server_checker.working_servers)}"))
            else:
                QMessageBox.information(
                    self,
                    fix_emojis("Результаты проверки"),
                    fix_emojis("Проверка остановлена до обнаружения рабочих серверов.")
                )
                self.append_log(fix_emojis("⏸️ Проверка остановлена. Рабочих серверов не найдено."))
            self.btn_check_servers.setEnabled(True)
            self.btn_check_servers.setText(fix_emojis("🔍 Проверить серверы"))
            self.server_checker = None

    def _start_check_servers(self):
        keys = self.sub_manager.keys
        if not keys:
            return
        self.btn_check_servers.setEnabled(True)
        self.btn_check_servers.setText(fix_emojis("⏹️ Остановить проверку"))
        self.append_log(fix_emojis(f"🔍 Начинаю проверку {len(keys)} серверов через Xray API..."))
        self.server_checker = ServerChecker(keys)
        self.server_checker.log_signal.connect(self.append_log)
        self.server_checker.progress_signal.connect(self._on_check_progress)
        self.server_checker.finished_signal.connect(self._on_check_finished)
        self.server_checker.partial_signal.connect(self._on_check_partial)
        self.server_checker.start()

    def _on_check_progress(self, current: int, total: int):
        self.btn_check_servers.setText(fix_emojis(f"⏹️ Остановить ({current}/{total})"))

    def _on_check_partial(self, working_servers: list):
        self.btn_check_servers.setEnabled(True)
        self.btn_check_servers.setText(fix_emojis("🔍 Проверить серверы"))
        if working_servers:
            dialog = CheckResultDialog(working_servers, self, partial=True)
            dialog.exec()
            self.append_log(fix_emojis(f"⏸️ Проверка остановлена. Найдено рабочих серверов: {len(working_servers)}"))
        else:
            QMessageBox.information(
                self,
                fix_emojis("Результаты проверки"),
                fix_emojis("Проверка остановлена. Рабочих серверов не найдено.")
            )
            self.append_log(fix_emojis("⏸️ Проверка остановлена. Рабочих серверов не найдено."))
        self.server_checker = None

    # ИЗМЕНЕНО: теперь принимает (working, checked) и сохраняет статусы
    def _on_check_finished(self, working_servers: list, checked_servers: list):
        # НОВОЕ: Сохраняем статусы в БД
        self.sub_manager.update_keys_check_status(working_servers, checked_servers)

        self.btn_check_servers.setEnabled(True)
        self.btn_check_servers.setText(fix_emojis("🔍 Проверить серверы"))

        if working_servers:
            dialog = CheckResultDialog(working_servers, self, partial=False)
            dialog.exec()
            self.append_log(fix_emojis(f"📊 Проверка завершена. Рабочих серверов: {len(working_servers)}"))
        else:
            QMessageBox.information(
                self,
                fix_emojis("Результаты проверки"),
                fix_emojis("❌ Рабочих серверов не найдено!")
            )
            self.append_log(fix_emojis("❌ Рабочих серверов не найдено!"))

        self.server_checker = None
        # НОВОЕ: Обновляем список, чтобы отобразить новые статусы
        self.refresh_keys_list()

    # ИЗМЕНЕНО: использует _get_selected_key_data
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

            key_data = self._get_selected_key_data()
            if not key_data:
                QMessageBox.warning(self, fix_emojis("Ошибка"), fix_emojis("Выберите ключ!"))
                return
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
        text = fix_emojis(str(text))
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
            self.setWindowTitle(fix_emojis("Bobcat Proxy 3.0 pre3 - ВКЛЮЧЕН"))
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
            self.btn_check_servers.setEnabled(False)
        else:
            self.btn_power.setText(fix_emojis("ВКЛЮЧИТЬ"))
            self.btn_power.setStyleSheet("""
                QPushButton { background-color:#00F267;color:white;border-radius:75px;
                    font-size:20px;font-weight:bold;border:4px solid #27ae60; }
                QPushButton:hover { background-color:#27ae60; }""")
            self.setWindowTitle(fix_emojis("Bobcat Proxy 3.0 pre3 - Прокси отключен"))
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
            self.btn_check_servers.setEnabled(True)
            has = len(self.sub_manager.keys) > 0
            self.btn_delete_selected.setEnabled(has)
            self.btn_delete_all.setEnabled(has)

#==================================================================================================
# ЗАПУСК
#==================================================================================================
if __name__ == "__main__":
    if platform.system() != 'Windows':
        # FreeBSD: применимо (Wayland/X11 через xcb; если плагина wayland нет — Qt уйдёт на xcb)
        os.environ.setdefault('QT_QPA_PLATFORM', 'wayland;xcb')
        os.environ.setdefault('QT_STYLE_OVERRIDE', 'fusion')
    app = QApplication([])
    app.setFont(QFont("Arial", 10))
    try:
        _theme = get_system_theme()
        _app_icon = get_icon(_theme)
        if _app_icon:
            app.setWindowIcon(_app_icon)
    except Exception as _e:
        print(f"⚠️ Не удалось установить иконку приложения: {_e}")
    apply_emoji_fallbacks()
    window = XrayClient()
    apply_window_frame_setting(window)
    window.show()
    app.exec()
