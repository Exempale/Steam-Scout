import os
import json
import vdf
import requests
import random
import webbrowser
import uuid
import sys
import threading
import asyncio
import string
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QTreeWidget, QTreeWidgetItem, QMessageBox, QFrame, QProgressBar, QLineEdit
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent, QTimer
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import getmac

# Конфигурация Telegram
BOT_TOKEN = "7427966583:AAFpZZf_UK01nROKU5PhDUzpttHeZkhd9O4"
ADMIN_TELEGRAM_ID = "6074658394"
CREATOR_USERNAME = "@Exempale"
AUTH_FILE = os.path.join(os.path.expanduser('~'), 'steam_scout_auth.json')
KEYS_FILE = os.path.join(os.path.expanduser('~'), 'steam_scout_keys.json')

# Стили для приложения
STYLE = """
QMainWindow {
    background-color: #1B1D23;
}
QPushButton {
    font-size: 14px;
    color: #fff;
    background-color: #2A475E;
    border: none;
    padding: 10px;
}
QPushButton:hover {
    background-color: #354F6E;
}
QTreeWidget {
    color: #67C1F5;
    background-color: #1B1D23;
}
QLabel {
    color: #67C1F5;
    font-size: 14px;
}
QProgressBar {
    color: #67C1F5;
    background-color: #1B2838;
    border: 1px solid #67C1F5;
}
"""

def generate_key():
    """Генерирует случайный ключ активации."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def load_keys():
    """Загружает список действительных ключей."""
    if not os.path.exists(KEYS_FILE):
        return []
    try:
        with open(KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('keys', [])
    except Exception as e:
        print(f"Ошибка загрузки ключей: {e}")
        return []

def save_keys(keys):
    """Сохраняет список действительных ключей."""
    try:
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'keys': keys}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения ключей: {e}")

async def handle_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /key для генерации нового ключа."""
    user_id = str(update.message.from_user.id)
    print(f"Получена команда /key от пользователя {user_id}")
    
    if user_id != ADMIN_TELEGRAM_ID:
        print(f"Отказано в доступе пользователю {user_id}")
        await update.message.reply_text("У вас нет прав для генерации ключей.")
        return

    print("Генерация нового ключа...")
    new_key = generate_key()
    keys = load_keys()
    keys.append(new_key)
    save_keys(keys)
    
    print(f"Ключ сгенерирован: {new_key}")
    await update.message.reply_text(f"Новый ключ активации создан:\n`{new_key}`", parse_mode='Markdown')

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    user_id = str(update.message.from_user.id)
    print(f"Получена команда /start от пользователя {user_id}")
    
    if user_id == ADMIN_TELEGRAM_ID:
        print("Пользователь является администратором")
        await update.message.reply_text(
            "Привет! Вы авторизованы как администратор.\n"
            "Используйте /key для генерации ключа активации."
        )
    else:
        print(f"Обычный пользователь (id: {user_id})")
        await update.message.reply_text(
            "Привет! Для получения ключа активации обратитесь к создателю: " + CREATOR_USERNAME
        )

def get_mac_address():
    """Получает MAC-адрес компьютера."""
    return getmac.get_mac_address()

def check_auth():
    """Проверяет статус авторизации."""
    mac = get_mac_address()
    if not mac:
        return False
    
    if not os.path.exists(AUTH_FILE):
        return False
        
    try:
        with open(AUTH_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return mac in data.get('authorized_macs', [])
    except Exception as e:
        print(f"Ошибка проверки авторизации: {e}")
        return False

class AuthWindow(QMainWindow):
    """Окно авторизации."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация - Steam Scout")
        self.setMinimumSize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet(STYLE)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        
        # Инструкция
        label = QLabel(f"Для получения ключа активации напишите:\n{CREATOR_USERNAME}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; color: #67C1F5;")
        layout.addWidget(label)
        
        # Поле для ключа
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Введите ключ активации")
        self.code_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background: #2A475E;
                border: none;
                color: white;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.code_input)
        
        # Кнопка активации
        activate_btn = QPushButton("Активировать")
        activate_btn.clicked.connect(self.try_activate)
        layout.addWidget(activate_btn)
        
        central_widget.setLayout(layout)
        
    def try_activate(self):
        """Пытается активировать программу."""
        entered_key = self.code_input.text().strip()
        valid_keys = load_keys()
        
        if entered_key in valid_keys:
            mac = get_mac_address()
            if mac:
                try:
                    data = {'authorized_macs': []}
                    if os.path.exists(AUTH_FILE):
                        with open(AUTH_FILE, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    
                    if mac not in data.get('authorized_macs', []):
                        data['authorized_macs'] = data.get('authorized_macs', []) + [mac]
                        
                    with open(AUTH_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # Удаляем использованный ключ
                    valid_keys.remove(entered_key)
                    save_keys(valid_keys)
                    
                    QMessageBox.information(self, "Успех", "Программа успешно активирована!")
                    self.close()
                    window = SteamGameFinder()
                    window.show()
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении авторизации: {e}")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось получить MAC-адрес устройства")
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный ключ активации")


class SteamAPIHelper:
    def __init__(self, steam_path):
        self.steam_path = steam_path
        self.default_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

    def is_valid_appid(self, appid):
        """Проверяет, является ли appid валидным (только цифры)."""
        return appid.isdigit()

    def get_game_info(self, appid):
        """Пытается получить информацию об игре локально, затем через API."""
        if not self.is_valid_appid(appid):
            print(f"Пропущен невалидный appid: {appid}")
            return None
        game_info = self.get_local_game_info(appid)
        if game_info and game_info.get('name') != 'Неизвестно':
            return game_info
        return self.get_web_game_info(appid)

    def get_local_game_info(self, appid):
        """Извлекает информацию из appmanifest_*.acf в библиотечных папках."""
        libraryfolders_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(libraryfolders_path):
            print(f"Файл libraryfolders.vdf не найден по пути: {libraryfolders_path}")
            return None

        try:
            with open(libraryfolders_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
                library_folders = data.get('libraryfolders', {})
                if not isinstance(library_folders, dict):
                    print(f"Некорректный формат libraryfolders.vdf: ожидался словарь, получено {type(library_folders)}")
                    return None
                for lib in library_folders.values():
                    if not isinstance(lib, dict) or 'path' not in lib:
                        print(f"Некорректная структура библиотеки в libraryfolders.vdf: {lib}")
                        continue
                    appmanifest_path = os.path.join(lib['path'], 'steamapps', f'appmanifest_{appid}.acf')
                    if os.path.exists(appmanifest_path):
                        try:
                            with open(appmanifest_path, 'r', encoding='utf-8') as f_app:
                                app_data = vdf.load(f_app)
                                app_state = app_data.get('AppState', {})
                                if not app_state:
                                    print(f"AppState отсутствует в {appmanifest_path}")
                                    continue
                                name = app_state.get('name', 'Неизвестно')
                                icon_url = self.get_local_icon_url(appid)
                                return {
                                    'name': name,
                                    'icon_url': icon_url
                                }
                        except Exception as e:
                            print(f"Ошибка чтения {appmanifest_path}: {e}")
                            continue
        except Exception as e:
            print(f"Ошибка при чтении libraryfolders.vdf: {e}")
        return None

    def get_local_icon_url(self, appid):
        """Ищет локальную иконку в папке librarycache."""
        icon_paths = [
            os.path.join(self.steam_path, "appcache", "librarycache", f"{appid}_icon.jpg"),
            os.path.join(self.steam_path, "appcache", "librarycache", f"{appid}_library_600x900.jpg")
        ]
        for path in icon_paths:
            if os.path.exists(path):
                return f"file:///{path}"
        return None

    def get_web_game_info(self, appid):
        """Получает информацию об игре через Steam API."""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and data.get(str(appid), {}).get('success'):
                game_data = data[str(appid)]['data']
                name = game_data.get('name', 'Неизвестно')
                icon_url = self.get_web_icon_url(game_data)
                return {
                    'name': name,
                    'icon_url': icon_url
                }
            else:
                print(f"API Steam не вернул данные для appid {appid}")
        except requests.RequestException as e:
            print(f"Ошибка запроса к API Steam для appid {appid}: {e}")
        return None

    def get_web_icon_url(self, game_data):
        """Извлекает URL иконки из данных API."""
        for field in ['header_image', 'capsule_image', 'capsule_imagev5']:
            if game_data.get(field):
                return game_data[field]
        return None


class IconUpdateEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, item, icon, icon_url):
        super().__init__(self.EVENT_TYPE)
        self.item = item
        self.icon = icon
        self.icon_url = icon_url


class ScanWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    scan_finished = pyqtSignal(bool, str)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._is_running = True
        self.error_messages = []

    def run(self):
        try:
            self.parent.game_data = []
            current_progress = 0

            self.scan_acf_files()
            current_progress += 20
            self.progress_updated.emit(current_progress, "Обработка файлов ACF завершена")

            if not self._is_running: return
            self.scan_manifest_files()
            current_progress += 20
            self.progress_updated.emit(current_progress, "Обработка манифестов завершена")

            if not self._is_running: return
            self.scan_lua_files()
            current_progress += 20
            self.progress_updated.emit(current_progress, "Обработка Lua скриптов завершена")

            if not self._is_running: return
            self.scan_stats_files()
            current_progress += 20
            self.progress_updated.emit(current_progress, "Обработка статистики завершена")

            if not self._is_running: return
            self.scan_screenshots()
            current_progress += 20
            self.progress_updated.emit(current_progress, "Обработка скриншотов завершена")

            if not self._is_running: return
            self.process_game_data()
            self.progress_updated.emit(100, "Завершение сканирования...")

            if self.error_messages:
                self.scan_finished.emit(False, "\n".join(self.error_messages))
            else:
                self.scan_finished.emit(True, "")
        except Exception as e:
            self.error_messages.append(f"Критическая ошибка при сканировании: {e}")
            self.scan_finished.emit(False, "\n".join(self.error_messages))

    def scan_acf_files(self):
        steamapps_path = os.path.join(self.parent.steam_path, "steamapps")
        if not os.path.exists(steamapps_path):
            self.error_messages.append(f"Папка steamapps не найдена: {steamapps_path}")
            return

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for file in os.listdir(steamapps_path):
                    if not self._is_running: return
                    if file.startswith("appmanifest_") and file.endswith(".acf"):
                        futures.append(executor.submit(self.process_acf_file, file))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки ACF файла: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при сканировании ACF файлов: {e}")

    def process_acf_file(self, file):
        try:
            steamapps_path = os.path.join(self.parent.steam_path, "steamapps")
            file_path = os.path.join(steamapps_path, file)
            if not os.access(file_path, os.R_OK):
                self.error_messages.append(f"Нет прав на чтение файла {file_path}")
                return
            with open(file_path, "r", encoding="utf-8") as f:
                data = vdf.load(f)
                app_state = data.get('AppState', {})
                if not app_state:
                    self.error_messages.append(f"AppState отсутствует в {file_path}")
                    return
                appid = app_state.get('appid', '0')
                if not self.parent.api_helper.is_valid_appid(appid):
                    print(f"Пропущен невалидный appid в ACF: {appid}")
                    return
                if not any(g['appid'] == appid for g in self.parent.game_data):
                    self.parent.game_data.append({
                        'appid': appid,
                        'name': app_state.get('name', 'Неизвестно'),
                        'source': 'ACF',
                        'last_played': app_state.get('LastPlayed', 0)
                    })
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки файла {file}: {e}")

    def scan_manifest_files(self):
        depotcache_path = os.path.join(self.parent.steam_path, "depotcache")
        if not os.path.exists(depotcache_path):
            self.error_messages.append(f"Папка depotcache не найдена: {depotcache_path}")
            return

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for file in os.listdir(depotcache_path):
                    if not self._is_running: return
                    if file.endswith(".manifest"):
                        futures.append(executor.submit(self.process_manifest_file, file))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки манифеста: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при сканировании манифестов: {e}")

    def process_manifest_file(self, file):
        try:
            appid = file.split('.')[0]
            if not self.parent.api_helper.is_valid_appid(appid):
                print(f"Пропущен невалидный appid в манифесте: {appid}")
                return
            if not any(g['appid'] == appid for g in self.parent.game_data):
                self.parent.game_data.append({
                    'appid': appid,
                    'source': 'Manifest'
                })
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки манифеста {file}: {e}")

    def scan_lua_files(self):
        stplugin_path = os.path.join(self.parent.steam_path, "config", "stplug-in")
        if not os.path.exists(stplugin_path):
            self.error_messages.append(f"Папка stplug-in не найдена: {stplugin_path}")
            return

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for file in os.listdir(stplugin_path):
                    if not self._is_running: return
                    if file.endswith(".lua"):
                        futures.append(executor.submit(self.process_lua_file, file))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки Lua файла: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при сканировании Lua файлов: {e}")

    def process_lua_file(self, file):
        try:
            appid = file.split('.')[0]
            if not self.parent.api_helper.is_valid_appid(appid):
                print(f"Пропущен невалидный appid в Lua: {appid}")
                return
            if not any(g['appid'] == appid for g in self.parent.game_data):
                self.parent.game_data.append({
                    'appid': appid,
                    'source': 'Lua'
                })
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки Lua файла {file}: {e}")

    def scan_stats_files(self):
        statsexport_path = os.path.join(self.parent.steam_path, "config", "StatsExport")
        if not os.path.exists(statsexport_path):
            self.error_messages.append(f"Папка StatsExport не найдена: {statsexport_path}")
            return

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for file in os.listdir(statsexport_path):
                    if not self._is_running: return
                    if file.endswith(".json"):
                        futures.append(executor.submit(self.process_stats_file, file))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки JSON файла: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при сканировании статистики: {e}")

    def process_stats_file(self, file):
        try:
            appid = file.split('.')[0]
            if not self.parent.api_helper.is_valid_appid(appid):
                print(f"Пропущен невалидный appid в Stats: {appid}")
                return
            if not any(g['appid'] == appid for g in self.parent.game_data):
                self.parent.game_data.append({
                    'appid': appid,
                    'source': 'Stats'
                })
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки JSON файла {file}: {e}")

    def scan_screenshots(self):
        userdata_path = os.path.join(self.parent.steam_path, "userdata")
        if not os.path.exists(userdata_path):
            self.error_messages.append(f"Папка userdata не найдена: {userdata_path}")
            return

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for user_id in os.listdir(userdata_path):
                    if not self._is_running: return
                    screenshots_path = os.path.join(userdata_path, user_id, "760", "remote")
                    if os.path.exists(screenshots_path):
                        for appid in os.listdir(screenshots_path):
                            if not self.parent.api_helper.is_valid_appid(appid):
                                print(f"Пропущен невалидный appid в Screenshots: {appid}")
                                continue
                            if appid.isdigit() and not any(g['appid'] == appid for g in self.parent.game_data):
                                futures.append(executor.submit(self.process_screenshot_file, appid))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки скриншота: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при сканировании скриншотов: {e}")

    def process_screenshot_file(self, appid):
        try:
            if not self.parent.api_helper.is_valid_appid(appid):
                print(f"Пропущен невалидный appid в Screenshots: {appid}")
                return
            self.parent.game_data.append({
                'appid': appid,
                'source': 'Screenshots'
            })
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки скриншота для appid {appid}: {e}")

    def process_game_data(self):
        cache_file = os.path.join(os.path.expanduser('~'), 'steam_games_cache.json')
        games_cache = {}
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    games_cache = json.load(f)
        except Exception as e:
            self.error_messages.append(f"Ошибка загрузки кэша: {e}")

        api = SteamAPIHelper(self.parent.steam_path)
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for game in self.parent.game_data:
                    if not self._is_running: return
                    futures.append(executor.submit(self.process_game, game, games_cache, api))

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.error_messages.append(f"Ошибка обработки игры: {e}")
        except Exception as e:
            self.error_messages.append(f"Ошибка при обработке данных игр: {e}")

        try:
            if not os.access(os.path.dirname(cache_file), os.W_OK):
                self.error_messages.append(f"Нет прав на запись в директорию для кэша: {os.path.dirname(cache_file)}")
                return
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(games_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.error_messages.append(f"Ошибка сохранения кэша: {e}")

    def process_game(self, game, games_cache, api):
        try:
            appid = game['appid']
            if appid in games_cache and games_cache[appid].get('name') != 'Неизвестно' and games_cache[appid].get(
                    'icon_url'):
                game.update(games_cache[appid])
            else:
                game_info = api.get_game_info(appid)
                if game_info and game_info.get('name') != 'Неизвестно' and game_info.get('icon_url'):
                    game.update(game_info)
                    games_cache[appid] = game_info
        except Exception as e:
            self.error_messages.append(f"Ошибка обработки игры с appid {appid}: {e}")

    def stop(self):
        self._is_running = False


class SteamGameFinder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steam Scout")
        self.setMinimumSize(1200, 800)
        self.steam_path = self.find_steam_path()
        self.game_data = []
        self.icon_cache = {}
        self.api_helper = SteamAPIHelper(self.steam_path)
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.init_ui()
        self.load_settings()

    def find_steam_path(self):
        paths = [
            "C:\\Program Files (x86)\\Steam",
            "D:\\Steam",
            os.path.expanduser("~\\AppData\\Local\\Steam")
        ]
        for path in paths:
            if os.path.exists(os.path.join(path, "steam.exe")):
                return path
        return "C:\\Program Files (x86)\\Steam"

    def init_ui(self):
        self.setStyleSheet(STYLE)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Header
        header = QLabel("🎮 Steam Scout")
        header.setStyleSheet("""
            font-size: 24px;
            color: #66C0F4;
            font-weight: bold;
            padding: 15px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # Control Panel
        control_frame = QFrame()
        control_layout = QHBoxLayout()

        self.scan_btn = QPushButton("🔍 Сканировать библиотеку")
        self.scan_btn.setStyleSheet("background-color: #2A475E;")
        self.scan_btn.clicked.connect(self.start_scan)

        self.random_btn = QPushButton("🎲 Случайная игра")
        self.random_btn.setStyleSheet("background-color: #1B2838;")
        self.random_btn.clicked.connect(self.pick_random_game)

        control_layout.addWidget(self.scan_btn)
        control_layout.addWidget(self.random_btn)
        control_frame.setLayout(control_layout)
        main_layout.addWidget(control_frame)

        # Game List
        self.games_list = QTreeWidget()
        self.games_list.setColumnCount(3)
        self.games_list.setHeaderLabels(["Мини-иконка", "Название", "ID игры"])
        self.games_list.setIconSize(QSize(48, 48))
        self.games_list.setColumnWidth(0, 60)
        self.games_list.setColumnWidth(1, 300)
        self.games_list.setColumnWidth(2, 150)
        main_layout.addWidget(self.games_list)

        # Toggle Button
        self.toggle_btn = QPushButton("Скрыть список")
        self.toggle_btn.clicked.connect(self.toggle_game_list)
        main_layout.addWidget(self.toggle_btn)

        # Status Bar
        self.status_label = QLabel("Готов к сканированию")
        self.status_label.setStyleSheet("color: #67C1F5; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        central_widget.setLayout(main_layout)

    def toggle_game_list(self):
        if self.games_list.isVisible():
            self.games_list.setVisible(False)
            self.toggle_btn.setText("Показать список")
        else:
            self.games_list.setVisible(True)
            self.toggle_btn.setText("Скрыть список")

    def start_scan(self):
        self.game_data = []
        self.games_list.clear()
        self.scan_worker = ScanWorker(self)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def update_progress(self, value, message):
        self.status_label.setText(f"{message} ({value}%)")

    def on_scan_finished(self, success, message):
        if success:
            self.display_games()
            self.status_label.setText(
                f"Сканирование завершено. Найдено {len(self.game_data)} игр, отображено {self.games_list.topLevelItemCount()}")
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сканирования:\n{message}")

    def display_games(self):
        self.games_list.clear()
        for game in self.game_data:
            if game.get('name') != 'Неизвестно' and game.get('icon_url'):
                self.add_game_item(game)

    def add_game_item(self, game):
        item = QTreeWidgetItem(self.games_list)
        name = game.get('name', 'Неизвестно')
        appid = game.get('appid', '0')
        item.setText(1, name)
        item.setText(2, f"AppID: {appid}")

        icon_url = game.get('icon_url')
        if icon_url:
            self.load_icon_async(appid, icon_url, item)
        else:
            print(f"Нет иконки для appid {appid}")

        tooltip = f"AppID: {appid}\nИсточник: {game.get('source', 'Неизвестно')}"
        last_played = game.get('last_played', 0)
        if isinstance(last_played, str):
            try:
                last_played = int(last_played)
            except ValueError:
                last_played = 0
        if last_played:
            last_played = datetime.fromtimestamp(last_played).strftime('%Y-%m-%d %H:%M')
            tooltip += f"\nПоследний запуск: {last_played}"

        item.setToolTip(1, tooltip)
        self.games_list.addTopLevelItem(item)

    def load_icon_async(self, appid, url, item):
        if appid in self.icon_cache:
            item.setIcon(0, self.icon_cache[appid])
            return
        self.thread_pool.submit(self.load_icon, appid, url, item)

    def load_icon(self, appid, url, item):
        try:
            pixmap = QPixmap()
            if url and url.startswith("file:///"):
                pixmap.load(url[8:])
            elif url:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                pixmap.loadFromData(response.content)
            if pixmap.isNull():
                print(f"Не удалось загрузить иконку для appid {appid}")
                return

            icon = QIcon(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio))
            self.icon_cache[appid] = icon
            QApplication.postEvent(self, IconUpdateEvent(item, icon, url))
        except Exception as e:
            print(f"Ошибка загрузки иконки для appid {appid}: {e}")
            return

    def get_resource_path(self, filename):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, filename)

    def pick_random_game(self):
        if not self.game_data:
            QMessageBox.warning(self, "Предупреждение", "Игры не найдены. Пожалуйста, отсканируйте библиотеку.")
            return
        valid_games = [game for game in self.game_data if game.get('name') != 'Неизвестно' and game.get('icon_url')]
        if not valid_games:
            QMessageBox.warning(self, "Предупреждение", "Нет игр с названием и иконкой.")
            return
        game = random.choice(valid_games)
        webbrowser.open(f"steam://nav/games/details/{game['appid']}")

    def load_settings(self):
        settings_file = os.path.join(os.path.expanduser('~'), 'steam_finder_settings.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.steam_path = settings.get('steam_path', self.steam_path)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        settings = {
            'steam_path': self.steam_path
        }
        settings_file = os.path.join(os.path.expanduser('~'), 'steam_finder_settings.json')
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def closeEvent(self, event):
        self.save_settings()
        self.thread_pool.shutdown()
        if hasattr(self, 'scan_worker') and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.scan_worker.wait()
        event.accept()

    def event(self, e):
        if isinstance(e, IconUpdateEvent):
            if e.icon and e.icon_url and e.icon_url != self.get_resource_path("icon.ico"):
                e.item.setIcon(0, e.icon)
            return True
        return super().event(e)


def main():
    app = QApplication([])
    app.setStyle('Fusion')

    # Запускаем Telegram бота в отдельном потоке
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            bot_app = Application.builder().token(BOT_TOKEN).build()
            bot_app.add_handler(CommandHandler("start", handle_start))
            bot_app.add_handler(CommandHandler("key", handle_key_command))
            
            print("Бот запускается...")
            bot_app.run_polling(allowed_updates=Update.ALL_TYPES)
            print("Бот запущен успешно!")
        except Exception as e:
            print(f"Ошибка в боте: {e}")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    if check_auth():
        window = SteamGameFinder()
    else:
        window = AuthWindow()

    window.show()
    app.exec()


if __name__ == "__main__":
    main()