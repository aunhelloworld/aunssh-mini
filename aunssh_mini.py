"""
AunSSH Mini Lite - Minimal SSH/SFTP file manager and editor.
Created by Aunhelloworld

Requirements: pip install PyQt6 paramiko
"""

import os
import sys
import json
import stat as _stat
from pathlib import Path
from typing import Optional

import paramiko

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRegularExpression, QSize, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon, QPixmap, QPainter, QKeySequence, QShortcut
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QPlainTextEdit,
    QSplitter, QLabel, QFileDialog, QMessageBox, QStatusBar, QInputDialog,
    QDialog, QDialogButtonBox, QMenu,
)

APP_VERSION = "1.0.0"
APP_NAME = "AunSSH Mini 1.0.0"
CONFIG_FILE = Path.home() / ".aunssh_mini_lite.json"
MONO = "JetBrains Mono, Cascadia Code, Fira Code, Consolas, Menlo, Monospace"


# ==============================================================================
# Simple config (only remembers last connection)
# ==============================================================================
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def save_config(data: dict):
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), "utf-8")
    except Exception:
        pass


# ==============================================================================
# Simple Syntax Highlighter
# ==============================================================================
_PY_KW = "False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split()
_JS_KW = "var let const function return if else for while do switch case break continue new delete typeof void null undefined true false this class extends import export default async await yield try catch finally throw".split()
_SH_KW = "if then else elif fi for in do done while case esac function return export source local readonly declare".split()


class SimpleHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lang="plain"):
        super().__init__(document)
        self.lang = lang
        self._build_rules()

    def _fmt(self, color, bold=False):
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(700)
        return f

    def _build_rules(self):
        self.rules = []
        kw_color = "#79c0ff"
        str_color = "#a5d6ff"
        cmt_color = "#6e7681"
        num_color = "#ff9f0a"

        if self.lang == "python":
            for k in _PY_KW:
                self.rules.append((QRegularExpression(r"\b" + k + r"\b"), self._fmt(kw_color, True)))
            self.rules += [
                (QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt(str_color)),
                (QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self._fmt(str_color)),
                (QRegularExpression(r"#[^\n]*"), self._fmt(cmt_color)),
                (QRegularExpression(r"\b\d+(\.\d+)?\b"), self._fmt(num_color)),
            ]
        elif self.lang == "javascript":
            for k in _JS_KW:
                self.rules.append((QRegularExpression(r"\b" + k + r"\b"), self._fmt(kw_color, True)))
            self.rules += [
                (QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt(str_color)),
                (QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self._fmt(str_color)),
                (QRegularExpression(r"//[^\n]*"), self._fmt(cmt_color)),
                (QRegularExpression(r"\b\d+(\.\d+)?\b"), self._fmt(num_color)),
            ]
        elif self.lang == "shell":
            for k in _SH_KW:
                self.rules.append((QRegularExpression(r"\b" + k + r"\b"), self._fmt(kw_color, True)))
            self.rules += [
                (QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt(str_color)),
                (QRegularExpression(r"'[^']*'"), self._fmt(str_color)),
                (QRegularExpression(r"#[^\n]*"), self._fmt(cmt_color)),
                (QRegularExpression(r"\b\d+(\.\d+)?\b"), self._fmt(num_color)),
            ]

    def highlightBlock(self, text):
        if len(text) > 2000:
            return
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ==============================================================================
# File Icon Helper
# ==============================================================================
def get_file_icon(name: str) -> QIcon:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    colors = {
        "py": "#3776ab", "js": "#f7df1e", "ts": "#3178c6", "json": "#cbcb41",
        "html": "#e34c26", "css": "#563d7c", "md": "#519aba", "sh": "#4eaa25",
        "yaml": "#cb171e", "yml": "#cb171e", "sql": "#e38c00", "go": "#00add8",
        "rs": "#dea584", "php": "#777bb4", "rb": "#cc342d", "conf": "#6c8ebf",
    }
    color = colors.get(ext, "#8a8a99")
    pm = QPixmap(QSize(16, 16))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, 16, 16, 3, 3)
    p.end()
    return QIcon(pm)


def get_folder_icon() -> QIcon:
    pm = QPixmap(QSize(16, 16))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setBrush(QColor("#89b4fa"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 2, 16, 14, 2, 2)
    p.end()
    return QIcon(pm)


# ==============================================================================
# SSH Session
# ==============================================================================
class SSHSession:
    def __init__(self, host: str, port: int, user: str, password: str = "", key_path: str = ""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.key_path = key_path
        self.ssh: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self) -> str:
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.key_path:
                self.ssh.connect(
                    hostname=self.host, port=self.port, username=self.user,
                    key_filename=self.key_path, timeout=10, banner_timeout=10
                )
            else:
                self.ssh.connect(
                    hostname=self.host, port=self.port, username=self.user,
                    password=self.password, timeout=10, banner_timeout=10
                )
            self._sftp = self.ssh.open_sftp()
            return ""
        except paramiko.AuthenticationException:
            return "Authentication failed - wrong username or password/key"
        except Exception as e:
            return str(e)

    def get_sftp(self) -> paramiko.SFTPClient:
        if not self._sftp or self._sftp.sock is None:
            self._sftp = self.ssh.open_sftp()
        return self._sftp

    def is_alive(self) -> bool:
        try:
            tr = self.ssh.get_transport()
            return tr is not None and tr.is_active()
        except Exception:
            return False

    def close(self):
        try:
            if self._sftp:
                self._sftp.close()
        except Exception:
            pass
        try:
            if self.ssh:
                self.ssh.close()
        except Exception:
            pass


# ==============================================================================
# Worker Threads
# ==============================================================================
class ConnectWorker(QThread):
    success = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, host, port, user, password="", key_path=""):
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.key_path = key_path

    def run(self):
        sess = SSHSession(self.host, self.port, self.user, self.password, self.key_path)
        err = sess.connect()
        if err:
            self.failed.emit(err)
        else:
            self.success.emit(sess)


class DirWorker(QThread):
    done = pyqtSignal(str, list)
    failed = pyqtSignal(str)

    def __init__(self, sess: SSHSession, path: str):
        super().__init__()
        self.sess = sess
        self.path = path

    def run(self):
        try:
            sftp = self.sess.get_sftp()
            items = []
            for a in sftp.listdir_attr(self.path):
                is_dir = _stat.S_ISDIR(a.st_mode)
                size = a.st_size or 0
                items.append((a.filename, is_dir, size))
            items.sort(key=lambda x: (not x[1], x[0].lower()))
            self.done.emit(self.path, items)
        except Exception as e:
            self.failed.emit(str(e))


class ReadFileWorker(QThread):
    done = pyqtSignal(str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, sess: SSHSession, path: str):
        super().__init__()
        self.sess = sess
        self.path = path

    def run(self):
        try:
            sftp = self.sess.get_sftp()
            st = sftp.stat(self.path)
            if (st.st_size or 0) > 8 * 1024 * 1024:
                self.failed.emit(self.path, "File too large (>8MB)")
                return
            with sftp.open(self.path, "r") as f:
                content = f.read().decode("utf-8", errors="replace")
            self.done.emit(self.path, content)
        except Exception as e:
            self.failed.emit(self.path, str(e))


class SaveFileWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, sess: SSHSession, path: str, content: str):
        super().__init__()
        self.sess = sess
        self.path = path
        self.content = content

    def run(self):
        try:
            sftp = self.sess.get_sftp()
            with sftp.open(self.path, "w") as f:
                f.write(self.content.encode("utf-8"))
            self.done.emit(self.path)
        except Exception as e:
            self.failed.emit(str(e))


# ==============================================================================
# Login Dialog
# ==============================================================================
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Connect")
        self.setFixedSize(420, 350)
        self.session: Optional[SSHSession] = None

        config = load_config()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Host:"))
        self.host_in = QLineEdit(config.get("host", ""))
        self.host_in.setPlaceholderText("192.168.1.1 or hostname")
        layout.addWidget(self.host_in)

        row = QHBoxLayout()
        row.addWidget(QLabel("Port:"))
        self.port_in = QLineEdit(str(config.get("port", 22)))
        self.port_in.setFixedWidth(60)
        row.addWidget(self.port_in)
        row.addSpacing(10)
        row.addWidget(QLabel("User:"))
        self.user_in = QLineEdit(config.get("user", "root"))
        row.addWidget(self.user_in, stretch=1)
        layout.addLayout(row)

        self.use_key = False
        self.auth_type_btn = QPushButton("Use Private Key")
        self.auth_type_btn.setCheckable(True)
        self.auth_type_btn.clicked.connect(self._toggle_auth)
        layout.addWidget(self.auth_type_btn)

        self.auth_label = QLabel("Password:")
        layout.addWidget(self.auth_label)

        auth_row = QHBoxLayout()
        self.auth_in = QLineEdit()
        self.auth_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_in.setPlaceholderText("Enter password")
        self.auth_in.returnPressed.connect(self._connect)
        auth_row.addWidget(self.auth_in, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setVisible(False)
        self.browse_btn.clicked.connect(self._browse_key)
        auth_row.addWidget(self.browse_btn)
        layout.addLayout(auth_row)

        self.remember_cb = QPushButton("Remember")
        self.remember_cb.setCheckable(True)
        self.remember_cb.setChecked(bool(config.get("remember", False)))
        layout.addWidget(self.remember_cb)

        layout.addSpacing(10)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("font-size: 14px; padding: 8px; font-weight: 700;")
        self.connect_btn.clicked.connect(self._connect)
        layout.addWidget(self.connect_btn)

    def _toggle_auth(self):
        self.use_key = not self.use_key
        if self.use_key:
            self.auth_label.setText("Private Key:")
            self.auth_in.setEchoMode(QLineEdit.EchoMode.Normal)
            self.auth_in.setPlaceholderText("Path to private key")
            self.browse_btn.setVisible(True)
            self.auth_type_btn.setText("Use Password")
        else:
            self.auth_label.setText("Password:")
            self.auth_in.setEchoMode(QLineEdit.EchoMode.Password)
            self.auth_in.setPlaceholderText("Enter password")
            self.browse_btn.setVisible(False)
            self.auth_type_btn.setText("Use Private Key")

    def _browse_key(self):
        start = os.path.expanduser("~/.ssh")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", start)
        if path:
            self.auth_in.setText(path)

    def _connect(self):
        host = self.host_in.text().strip()
        user = self.user_in.text().strip()
        if not host or not user:
            self.status_lbl.setText("Please enter Host and Username")
            return

        try:
            port = int(self.port_in.text())
        except ValueError:
            port = 22

        self.connect_btn.setEnabled(False)
        self.status_lbl.setText("Connecting...")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")

        password = ""
        key_path = ""
        if self.use_key:
            key_path = self.auth_in.text()
        else:
            password = self.auth_in.text()

        if self.remember_cb.isChecked():
            save_config({"host": host, "port": port, "user": user, "remember": True})
        else:
            save_config({})

        self.worker = ConnectWorker(host, port, user, password, key_path)
        self.worker.success.connect(self._on_connected)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_connected(self, sess: SSHSession):
        self.session = sess
        self.accept()

    def _on_failed(self, err: str):
        self.connect_btn.setEnabled(True)
        self.status_lbl.setText(f"Error: {err}")
        self.status_lbl.setStyleSheet("color: #f85149; font-size: 11px;")


# ==============================================================================
# Main Window - File Browser + Editor
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self, session: SSHSession):
        super().__init__()
        self.session = session
        self.current_path = "/"
        self.modified = False
        self._workers = []
        self.current_file = None
        self._highlighter = None
        self._loading_file = False
        self.news_manager = None

        self.setWindowTitle(f"{APP_NAME} - {session.user}@{session.host}")
        self.setMinimumSize(800, 500)
        self.resize(1100, 700)

        self._build()
        self._setup_news_banner()

        try:
            sftp = session.get_sftp()
            home = sftp.normalize(".")
        except Exception:
            home = "/"
        self._list_dir(home)

    def _setup_news_banner(self):
        """สร้างแถบแสดงข่าวขนาดเล็กที่ด้านบน"""
        # สร้าง container widget สำหรับข่าว
        news_container = QWidget()
        news_layout = QHBoxLayout(news_container)
        news_layout.setContentsMargins(0, 0, 0, 0)
        news_layout.setSpacing(4)

        self.news_label = QLabel()
        self.news_label.setStyleSheet("""
            QLabel {
                background-color: #1f2a3e;
                color: #79c0ff;
                padding: 4px 8px;
                font-size: 11px;
                border-radius: 4px;
            }
        """)
        self.news_label.setWordWrap(True)
        self.news_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.news_label.setOpenExternalLinks(True)
        self.news_label.hide()

        # ปุ่มปิดข่าว
        self.news_close_btn = QPushButton("✕")
        self.news_close_btn.setFixedSize(20, 20)
        self.news_close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f2a3e;
                border: none;
                color: #8b949e;
                border-radius: 4px;
                padding: 0px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #f85149;
            }
        """)
        self.news_close_btn.clicked.connect(self._hide_news)
        self.news_close_btn.hide()

        news_layout.addWidget(self.news_label, stretch=1)
        news_layout.addWidget(self.news_close_btn)

        # เพิ่มเข้าไปใน layout หลัก (ใต้ path bar)
        central_widget = self.centralWidget()
        if central_widget and central_widget.layout():
            layout = central_widget.layout()
            layout.insertWidget(1, news_container)

        # เก็บ reference ไว้ใช้ซ่อน/แสดง
        self.news_container = news_container
        self.news_container.hide()

        # เรียกดูข่าว
        QTimer.singleShot(500, self._fetch_news)

    def _fetch_news(self):
        """ดึงข่าวจาก URL แบบไม่ปิดกั้น UI"""
        self.news_manager = QNetworkAccessManager()
        self.news_manager.finished.connect(self._on_news_received)
        request = QNetworkRequest(QUrl("https://www.aunssh.com/news.json"))
        self.news_manager.get(request)

    def _on_news_received(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            try:
                news_data = json.loads(data.decode('utf-8'))
                text = news_data.get("text", "")
                link = news_data.get("link", "")

                if text:
                    if link:
                        display_text = f'📢 <a href="{link}" style="color:#79c0ff; text-decoration:none;">{text}</a>'
                    else:
                        display_text = f'📢 {text}'

                    self.news_label.setText(display_text)
                    self.news_label.show()
                    self.news_close_btn.show()
                    self.news_container.show()

                    # ซ่อนอัตโนมัติหลังจาก 15 วินาที
                    QTimer.singleShot(15000, self._hide_news)
            except Exception as e:
                print(f"Parse news error: {e}")
        else:
            # ไม่มีข่าวหรือเชื่อมต่อไม่ได้ ไม่ต้องแสดงอะไร
            pass

        reply.deleteLater()

    def _hide_news(self):
        """ซ่อนแถบข่าว"""
        self.news_container.hide()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(4)
        root.setContentsMargins(6, 6, 6, 6)

        # Path bar
        path_bar = QHBoxLayout()
        path_bar.setSpacing(4)

        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setFixedWidth(100)
        self.home_btn.setToolTip("Go to home directory")
        self.home_btn.clicked.connect(self._go_home)
        path_bar.addWidget(self.home_btn)

        self.up_btn = QPushButton("⬆ Up")
        self.up_btn.setFixedWidth(80)
        self.up_btn.setToolTip("Go to parent directory")
        self.up_btn.clicked.connect(self._go_up)
        path_bar.addWidget(self.up_btn)

        self.path_in = QLineEdit()
        self.path_in.setFont(QFont(MONO, 10))
        self.path_in.returnPressed.connect(self._go_path)
        path_bar.addWidget(self.path_in, stretch=1)

        go_btn = QPushButton("Go")
        go_btn.setFixedWidth(80)
        go_btn.clicked.connect(self._go_path)
        path_bar.addWidget(go_btn)

        root.addLayout(path_bar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list (left)
        self.file_list = QListWidget()
        self.file_list.setFont(QFont(MONO, 10))
        self.file_list.setIconSize(QSize(16, 16))
        self.file_list.itemDoubleClicked.connect(self._on_item_double_click)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._context_menu)
        splitter.addWidget(self.file_list)

        # Editor (right)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self.file_info_lbl = QLabel("No file selected")
        self.file_info_lbl.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        right_layout.addWidget(self.file_info_lbl)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont(MONO, 11))
        self.editor.setTabStopDistance(
            self.editor.fontMetrics().horizontalAdvance(" ") * 4
        )
        self.editor.setReadOnly(True)
        right_layout.addWidget(self.editor, stretch=1)

        self.editor.document().modificationChanged.connect(self._on_modification_changed)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.save_btn = QPushButton("💾 Save [Ctrl+S]")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_file)
        btn_row.addWidget(self.save_btn)

        self.close_btn = QPushButton("✖ Close")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self._close_file)
        btn_row.addWidget(self.close_btn)

        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 750])

        root.addWidget(splitter, stretch=1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("✅ Ready")

        QShortcut(QKeySequence("Ctrl+S"), self, self._save_file)
        QShortcut(QKeySequence("F5"), self, lambda: self._list_dir(self.current_path))

    def _track_worker(self, worker: QThread):
        self._workers.append(worker)
        worker.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)

    def _go_home(self):
        try:
            home = self.session.get_sftp().normalize(".")
        except Exception:
            home = "/"
        self._list_dir(home)

    def _go_up(self):
        parent = os.path.dirname(self.current_path.rstrip("/")) or "/"
        self._list_dir(parent)

    def _go_path(self):
        path = self.path_in.text().strip()
        if not path:
            return
        if not path.startswith("/"):
            path = self.current_path.rstrip("/") + "/" + path
        path = os.path.normpath(path).replace("\\", "/")

        if not self.session.is_alive():
            QMessageBox.critical(self, "Error", "Connection lost")
            return

        try:
            sftp = self.session.get_sftp()
            sftp.stat(path)
            self._list_dir(path)
        except FileNotFoundError:
            QMessageBox.warning(self, "Not Found", path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _list_dir(self, path: str):
        if not self.session.is_alive():
            self.status.showMessage("Connection lost - please reconnect")
            return

        self.current_path = path
        self.path_in.setText(path)
        self.status.showMessage(f"Loading {path}...")
        self.file_list.clear()

        worker = DirWorker(self.session, path)
        worker.done.connect(self._populate_list)
        worker.failed.connect(lambda e: self.status.showMessage(f"Error: {e}"))
        self._track_worker(worker)
        worker.start()

    def _populate_list(self, path: str, items: list):
        self.current_path = path
        self.path_in.setText(path)
        self.status.showMessage(f"{path}  ({len(items)} items)")
        self.file_list.clear()

        for name, is_dir, size in items:
            text = f"{name}{'/' if is_dir else ''}"
            item = QListWidgetItem(text)
            item.setIcon(get_folder_icon() if is_dir else get_file_icon(name))
            item.setData(Qt.ItemDataRole.UserRole, {
                "name": name,
                "is_dir": is_dir,
                "path": path.rstrip("/") + "/" + name,
                "size": size
            })
            if not is_dir:
                item.setToolTip(f"{name} - {self._fmt_size(size)}")
            self.file_list.addItem(item)

    def _fmt_size(self, size: int) -> str:
        s = float(size)
        for u in ["B", "KB", "MB", "GB"]:
            if s < 1024:
                return f"{s:.0f} {u}" if u == "B" else f"{s:.1f} {u}"
            s /= 1024
        return f"{s:.1f} TB"

    def _on_item_double_click(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data["is_dir"]:
            self._list_dir(data["path"])
        else:
            self._open_file(data["path"])

    def _open_file(self, path: str):
        if not self.session.is_alive():
            QMessageBox.critical(self, "Error", "Connection lost")
            return
        self.status.showMessage(f"Opening {path}...")
        worker = ReadFileWorker(self.session, path)
        worker.done.connect(self._on_file_loaded)
        worker.failed.connect(self._on_file_error)
        self._track_worker(worker)
        worker.start()

    def _on_file_loaded(self, path: str, content: str):
        self._loading_file = True

        self.current_file = path
        self.modified = False
        self.file_info_lbl.setText(f"Editing: {path}")
        self.editor.setReadOnly(False)

        self.editor.setPlainText(content)
        self.editor.document().setModified(False)

        self._loading_file = False

        self.save_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.status.showMessage(f"Opened: {path}")

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = (
            "python"     if ext in ("py", "pyw")             else
            "javascript" if ext in ("js", "ts", "jsx", "tsx") else
            "shell"      if ext in ("sh", "bash")             else
            "plain"
        )

        if self._highlighter:
            self._highlighter.setDocument(None)
        self._highlighter = SimpleHighlighter(self.editor.document(), lang)

    def _on_file_error(self, path: str, error: str):
        QMessageBox.warning(self, "Error", f"Cannot open {path}\n\n{error}")
        self.status.showMessage("Open failed")

    def _on_modification_changed(self, modified: bool):
        if self._loading_file:
            return

        self.modified = modified
        if self.current_file:
            prefix = "* " if modified else ""
            self.file_info_lbl.setText(f"{prefix}Editing: {self.current_file}")

    def _save_file(self):
        if not self.current_file or not self.modified:
            return

        content = self.editor.toPlainText()
        self.status.showMessage(f"Saving {self.current_file}...")

        worker = SaveFileWorker(self.session, self.current_file, content)
        worker.done.connect(self._on_saved)
        worker.failed.connect(lambda e: QMessageBox.critical(self, "Save Failed", str(e)))
        self._track_worker(worker)
        worker.start()

    def _on_saved(self, path: str):
        self.editor.document().setModified(False)

        filename = os.path.basename(path)
        self.status.showMessage(f"✅ Saved: {filename}")
        QTimer.singleShot(3000, lambda: self.status.showMessage(f"Ready - {self.current_path}"))

    def _close_file(self):
        if self.modified:
            ans = QMessageBox.question(
                self, "Close File",
                "This file has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        self._loading_file = True
        self.editor.clear()
        self.editor.document().setModified(False)
        self._loading_file = False

        self.editor.setReadOnly(True)
        self.save_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.file_info_lbl.setText("No file selected")
        self.current_file = None
        self.modified = False

        if self._highlighter:
            self._highlighter.setDocument(None)
            self._highlighter = None

    def _context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        menu = QMenu(self)

        menu.addAction("📄 New File", self._new_file)
        menu.addAction("📁 New Folder", self._new_folder)
        menu.addAction("🔄 Refresh", lambda: self._list_dir(self.current_path))

        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                menu.addSeparator()
                menu.addAction("✏ Rename...", lambda: self._rename(data["path"]))
                menu.addAction("🗑 Delete", lambda: self._delete(data["path"], data["is_dir"]))

        menu.exec(self.file_list.viewport().mapToGlobal(pos))

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if not ok or not name.strip():
            return
        path = self.current_path.rstrip("/") + "/" + name.strip()
        try:
            sftp = self.session.get_sftp()
            with sftp.open(path, "w") as f:
                f.write(b"")
            self._list_dir(self.current_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        try:
            sftp = self.session.get_sftp()
            sftp.mkdir(self.current_path.rstrip("/") + "/" + name.strip())
            self._list_dir(self.current_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _rename(self, old_path: str):
        name, ok = QInputDialog.getText(self, "Rename", "New name:",
                                        text=os.path.basename(old_path))
        if not ok or not name.strip():
            return
        new_path = os.path.dirname(old_path.rstrip("/")) + "/" + name.strip()
        try:
            sftp = self.session.get_sftp()
            sftp.rename(old_path, new_path)
            self._list_dir(self.current_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete(self, path: str, is_dir: bool):
        if QMessageBox.question(
            self, "Delete",
            f"Delete:\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            sftp = self.session.get_sftp()
            if is_dir:
                def rmrf(p):
                    for a in sftp.listdir_attr(p):
                        full = p.rstrip("/") + "/" + a.filename
                        if _stat.S_ISDIR(a.st_mode):
                            rmrf(full)
                        else:
                            sftp.remove(full)
                    sftp.rmdir(p)
                rmrf(path)
            else:
                sftp.remove(path)
            self._list_dir(self.current_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def closeEvent(self, event):
        if self.modified:
            ans = QMessageBox.question(
                self, "Exit",
                "There are unsaved changes. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.session.close()
        event.accept()


# ==============================================================================
# Dark Theme
# ==============================================================================
DARK_THEME = """
    QMainWindow, QWidget {
        background: #0d1117; color: #e6edf3;
        font-family: 'Segoe UI', 'Ubuntu', sans-serif; font-size: 12px;
    }
    QLineEdit, QPlainTextEdit, QListWidget {
        background: #161b22; color: #e6edf3;
        border: 1px solid #30363d; border-radius: 6px; padding: 4px 8px;
        selection-background-color: #388bfd; selection-color: #ffffff;
    }
    QLineEdit:focus, QPlainTextEdit:focus { border-color: #388bfd; }
    QPushButton {
        background: #21262d; color: #e6edf3; border: 1px solid #30363d;
        border-radius: 6px; padding: 5px 14px; min-height: 22px;
    }
    QPushButton:hover { background: #30363d; border-color: #8b949e; }
    QPushButton:pressed { background: #161b22; }
    QPushButton:disabled { color: #484f58; background: #0d1117; border-color: #21262d; }
    QPushButton:checked { background: #388bfd; border-color: #388bfd; }
    QLabel { color: #8b949e; }
    QListWidget::item:selected { background: #388bfd; color: #ffffff; border-radius: 4px; }
    QListWidget::item:hover { background: #21262d; border-radius: 4px; }
    QStatusBar { background: #161b22; color: #8b949e; border-top: 1px solid #30363d; }
    QSplitter::handle:horizontal { background: #21262d; width: 3px; }
    QSplitter::handle:horizontal:hover { background: #388bfd; }
    QScrollBar:vertical { background: #0d1117; width: 8px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; min-height: 20px; }
    QScrollBar::handle:vertical:hover { background: #484f58; }
    QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
    QDialog { background: #0d1117; }
    QMenu {
        background: #161b22; color: #e6edf3; border: 1px solid #30363d;
        border-radius: 8px; padding: 4px;
    }
    QMenu::item { padding: 5px 20px; border-radius: 4px; }
    QMenu::item:selected { background: #388bfd; color: #ffffff; }
    QMenu::separator { background: #30363d; height: 1px; margin: 3px 8px; }
"""


def create_text_icon(letter: str, size: int = 64):
    """สร้างไอคอนจากตัวอักษร"""
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # พื้นหลังสีน้ำเงินโค้งมน
    painter.setBrush(QColor("#388bfd"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size // 4, size // 4)

    # ตัวอักษร A สีขาว
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Arial", size // 2, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)

    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    app.setApplicationName(APP_NAME)

    # ตั้งไอคอนเป็นตัว A
    app.setWindowIcon(create_text_icon("A"))

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    window = MainWindow(login.session)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()