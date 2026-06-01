"""
AunSSH Mini - Lightweight SSH/SFTP file manager, code editor and terminal IDE.
A fast, PuTTY-light alternative for editing files on remote servers without
installing heavy server-side extensions (unlike VSCode Remote).

Created by Aunhelloworld.  (rewritten / hardened build)

Requirements:
    pip install PyQt6 paramiko

Run:
    python aunssh_mini.py

Works on Linux, Windows and macOS.
"""

import os
import re
import sys
import json
import base64
import codecs
import socket
import datetime
import posixpath
import stat as _stat
from pathlib import Path
from typing import Optional, List, Dict

import paramiko

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QRegularExpression, QSize, QTimer, QUrl, QRect,
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon, QPixmap,
    QPainter, QKeySequence, QShortcut, QTextCursor, QTextDocument, QTextFormat,
    QFontMetricsF, QLinearGradient, QBrush,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QPlainTextEdit,
    QSplitter, QLabel, QFileDialog, QMessageBox, QStatusBar, QInputDialog,
    QDialog, QMenu, QTabWidget, QToolButton, QComboBox, QCheckBox, QTextEdit,
)

APP_VERSION = "1.0.6"
APP_NAME = f"AunSSH Mini {APP_VERSION}"
CONFIG_FILE = Path.home() / ".aunssh_mini.json"
MONO = "JetBrains Mono, Cascadia Code, Fira Code, Consolas, Menlo, DejaVu Sans Mono, monospace"
MONO_PRIMARY = "Consolas" if sys.platform.startswith("win") else "Monospace"
NEWS_URL = "https://www.aunssh.com/news.json"
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_HIGHLIGHTS = 4000


# ==============================================================================
# Config (profiles + remembered credentials)
# ==============================================================================
def _b64e(s: str) -> str:
    try:
        return base64.b64encode(s.encode("utf-8")).decode("ascii")
    except Exception:
        return ""


def _b64d(s: str) -> str:
    try:
        return base64.b64decode(s.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
            if not isinstance(data, dict):
                raise ValueError
            data.setdefault("profiles", [])
            data.setdefault("last", "")
            return data
        except Exception:
            pass
    return {"profiles": [], "last": ""}


def save_config(data: dict):
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), "utf-8")
    except Exception:
        pass


# ==============================================================================
# Remote path helpers  (always POSIX -- never use os.path on remote paths!)
# ==============================================================================
def remote_norm(path: str) -> str:
    path = (path or "/").replace("\\", "/")
    norm = posixpath.normpath(path)
    return norm if norm else "/"


def remote_join(base: str, name: str) -> str:
    return remote_norm(base.rstrip("/") + "/" + name)


def remote_parent(path: str) -> str:
    parent = posixpath.dirname(path.rstrip("/"))
    return parent if parent else "/"


# ==============================================================================
# App icon (drawn programmatically -- light, cross-platform, no huge blob)
# ==============================================================================
def build_app_icon() -> QIcon:
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 256, 256)
        grad.setColorAt(0.0, QColor("#388bfd"))
        grad.setColorAt(1.0, QColor("#0d419d"))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(18, 18, 220, 220, 46, 46)
        p.setPen(QColor("#e6edf3"))
        f = QFont(MONO_PRIMARY)
        f.setPixelSize(104)
        f.setBold(True)
        p.setFont(f)
        p.drawText(pm.rect().adjusted(0, -6, 0, -6),
                   Qt.AlignmentFlag.AlignCenter, ">_")
    finally:
        p.end()
    return QIcon(pm)


# ==============================================================================
# Syntax highlighting -- many languages
# ==============================================================================
C_KEYWORD = "#ff7b72"
C_BUILTIN = "#79c0ff"
C_TYPE = "#ffa657"
C_STRING = "#a5d6ff"
C_COMMENT = "#8b949e"
C_NUMBER = "#79c0ff"
C_FUNCTION = "#d2a8ff"
C_DECORATOR = "#ffa657"
C_TAG = "#7ee787"

EXT_LANG = {
    "py": "python", "pyw": "python", "pyi": "python",
    "js": "javascript", "mjs": "javascript", "cjs": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "java": "java",
    "c": "c", "h": "c",
    "cpp": "cpp", "cc": "cpp", "cxx": "cpp", "hpp": "cpp", "hh": "cpp", "hxx": "cpp", "ino": "cpp",
    "cs": "csharp",
    "go": "go",
    "rs": "rust",
    "php": "php", "phtml": "php",
    "rb": "ruby", "rake": "ruby", "gemspec": "ruby",
    "sh": "bash", "bash": "bash", "zsh": "bash", "ksh": "bash", "command": "bash",
    "sql": "sql",
    "lua": "lua",
    "kt": "kotlin", "kts": "kotlin",
    "swift": "swift",
    "css": "css", "scss": "css", "sass": "css", "less": "css",
    "html": "html", "htm": "html", "xhtml": "html", "vue": "html",
    "xml": "xml", "svg": "xml", "xaml": "xml", "plist": "xml",
    "json": "json", "json5": "json", "jsonc": "json",
    "yaml": "yaml", "yml": "yaml",
    "toml": "toml", "ini": "ini", "cfg": "ini", "conf": "ini",
    "md": "markdown", "markdown": "markdown", "mdx": "markdown",
    "pl": "perl", "pm": "perl",
    "r": "r",
    "dart": "dart",
    "scala": "scala",
}
NAME_LANG = {
    "dockerfile": "bash", "makefile": "bash", "cmakelists.txt": "bash",
    "vagrantfile": "ruby", "rakefile": "ruby", "gemfile": "ruby",
    ".bashrc": "bash", ".zshrc": "bash", ".profile": "bash",
    ".gitignore": "ini", ".env": "ini",
}

KEYWORDS = {
    "python": "and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield match case",
    "javascript": "abstract arguments async await break case catch class const continue debugger default delete do else enum export extends false finally for function get if implements import in instanceof interface let new null of package private protected public return set static super switch this throw true try typeof undefined var void while with yield",
    "typescript": "abstract any as asserts async await boolean break case catch class const continue debugger declare default delete do else enum export extends false finally for from function get if implements import in infer instanceof interface is keyof let module namespace never new null number object of package private protected public readonly return set static string super switch symbol this throw true try type typeof undefined unique unknown var void while with yield",
    "java": "abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient true false null try void volatile while var record sealed yield",
    "c": "auto break case char const continue default do double else enum extern float for goto if inline int long register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while",
    "cpp": "alignas alignof and auto bool break case catch char class const constexpr continue decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept nullptr operator or private protected public register reinterpret_cast return short signed sizeof static static_cast struct switch template this throw true try typedef typeid typename union unsigned using virtual void volatile while",
    "csharp": "abstract as base bool break byte case catch char checked class const continue decimal default delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit in int interface internal is lock long namespace new null object operator out override params private protected public readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using var virtual void volatile while async await yield",
    "go": "break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var true false nil iota",
    "rust": "as async await break const continue crate dyn else enum extern false fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait true type unsafe use where while",
    "php": "abstract and array as break callable case catch class clone const continue declare default do echo else elseif empty enddeclare endfor endforeach endif endswitch endwhile enum extends final finally fn for foreach function global goto if implements include include_once instanceof insteadof interface isset list match namespace new or print private protected public readonly require require_once return static switch throw trait try unset use var while yield true false null",
    "ruby": "alias and begin break case class def defined do else elsif end ensure false for if in module next nil not or redo rescue retry return self super then true undef unless until when while yield require require_relative attr_accessor attr_reader attr_writer",
    "bash": "if then else elif fi for in do done while until case esac function return select time local export readonly declare typeset unset shift break continue eval exec source alias set",
    "sql": "select from where insert update delete create alter drop table view index into values set join inner left right outer full cross on group by order having limit offset union all distinct as and or not null is in like between exists count sum avg min max primary key foreign references default unique check constraint database schema grant revoke begin commit rollback transaction case when then else end asc desc",
    "lua": "and break do else elseif end false for function goto if in local nil not or repeat return then true until while self",
    "kotlin": "abstract actual annotation as break by catch class companion const constructor continue crossinline data delegate do dynamic else enum expect external false final finally for fun get if import in infix init inline inner interface internal is lateinit lazy noinline null object open operator out override package private protected public reified return sealed set super suspend tailrec this throw true try typealias typeof val var vararg when where while",
    "swift": "associatedtype class deinit enum extension fileprivate func import init inout internal let open operator private protocol public rethrows static struct subscript typealias var break case continue default defer do else fallthrough for guard if in repeat return switch where while as Any catch false is nil self Self super throw throws true try",
    "dart": "abstract as assert async await break case catch class const continue covariant default deferred do dynamic else enum export extends extension external factory false final finally for get if implements import in interface is late library mixin new null on operator part required rethrow return set show static super switch sync this throw true try typedef var void while with yield",
    "scala": "abstract case catch class def do else extends false final finally for forSome if implicit import lazy match new null object override package private protected return sealed super this throw trait true try type val var while with yield",
    "json": "true false null",
    "yaml": "true false null yes no on off True False Null",
    "toml": "true false",
}
BUILTINS = {
    "python": "self cls print len range int float str bool list dict set tuple frozenset type input open isinstance issubclass enumerate zip map filter sum min max abs round all any sorted reversed super staticmethod classmethod property repr format hash id dir vars getattr setattr hasattr delattr next iter bytes bytearray complex divmod pow chr ord hex oct bin Exception ValueError TypeError KeyError IndexError RuntimeError StopIteration FileNotFoundError",
    "javascript": "console window document Math JSON Object Array String Number Boolean Promise Symbol Map Set WeakMap WeakSet Date RegExp Error TypeError RangeError parseInt parseFloat isNaN isFinite encodeURIComponent decodeURIComponent setTimeout setInterval clearTimeout clearInterval require module exports globalThis Infinity NaN",
    "typescript": "console window document Math JSON Object Array String Number Boolean Promise Symbol Map Set Date RegExp Error parseInt parseFloat isNaN setTimeout setInterval require module exports Record Partial Readonly Pick Omit",
}
LINE_COMMENT = {
    "python": "#", "bash": "#", "ruby": "#", "yaml": "#", "toml": "#",
    "ini": "#", "perl": "#", "r": "#",
    "javascript": "//", "typescript": "//", "c": "//", "cpp": "//",
    "java": "//", "csharp": "//", "go": "//", "rust": "//", "php": "//",
    "swift": "//", "kotlin": "//", "scala": "//", "dart": "//",
    "sql": "--", "lua": "--",
}
BLOCK_COMMENT = {
    "javascript": ("/*", "*/"), "typescript": ("/*", "*/"),
    "c": ("/*", "*/"), "cpp": ("/*", "*/"), "java": ("/*", "*/"),
    "csharp": ("/*", "*/"), "go": ("/*", "*/"), "rust": ("/*", "*/"),
    "php": ("/*", "*/"), "css": ("/*", "*/"),
    "swift": ("/*", "*/"), "kotlin": ("/*", "*/"), "scala": ("/*", "*/"),
    "sql": ("/*", "*/"), "dart": ("/*", "*/"),
    "html": ("<!--", "-->"), "xml": ("<!--", "-->"),
    "lua": ("--[[", "]]"),
}


class CodeHighlighter(QSyntaxHighlighter):
    """Multi-language highlighter with proper multi-line comment / string support."""

    def __init__(self, document, lang="text"):
        super().__init__(document)
        self.lang = lang
        self.rules = []
        self.multiline = []  # list of (start, end, state, fmt)
        self._build()

    @staticmethod
    def _fmt(color, bold=False, italic=False):
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            f.setFontWeight(QFont.Weight.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def _build(self):
        lang = self.lang
        f_kw = self._fmt(C_KEYWORD, bold=True)
        f_builtin = self._fmt(C_BUILTIN)
        f_str = self._fmt(C_STRING)
        f_cmt = self._fmt(C_COMMENT, italic=True)
        f_num = self._fmt(C_NUMBER)
        f_func = self._fmt(C_FUNCTION)
        f_deco = self._fmt(C_DECORATOR)
        f_tag = self._fmt(C_TAG, bold=True)
        rules = []

        if lang in ("html", "xml"):
            rules.append((QRegularExpression(r"</?[A-Za-z][\w:-]*"), f_tag))
            rules.append((QRegularExpression(r"\b[A-Za-z_:][\w:.-]*(?=\s*=)"), f_builtin))
            rules.append((QRegularExpression(r"&[A-Za-z#][\w]*;"), f_deco))
        elif lang == "css":
            rules.append((QRegularExpression(r"#[0-9a-fA-F]{3,8}\b"), f_num))
            rules.append((QRegularExpression(r"[.#]?-?[A-Za-z_][\w-]*(?=\s*\{)"), f_tag))
            rules.append((QRegularExpression(r"\b[a-z-]+(?=\s*:)"), f_builtin))
        elif lang == "markdown":
            rules.append((QRegularExpression(r"^\s{0,3}#{1,6}\s.*$"), self._fmt(C_KEYWORD, bold=True)))
            rules.append((QRegularExpression(r"`[^`]+`"), f_str))
            rules.append((QRegularExpression(r"\*\*[^*]+\*\*"), self._fmt(C_TYPE, bold=True)))
            rules.append((QRegularExpression(r"\[[^\]]*\]\([^)]*\)"), f_func))
            rules.append((QRegularExpression(r"^\s*[-*+]\s"), f_kw))
        else:
            rules.append((QRegularExpression(r"\b[A-Za-z_]\w*(?=\s*\()"), f_func))
            if lang in ("python", "java", "kotlin", "typescript", "javascript",
                        "csharp", "scala", "php"):
                rules.append((QRegularExpression(r"@[A-Za-z_]\w*"), f_deco))
            for kw in KEYWORDS.get(lang, "").split():
                rules.append((QRegularExpression(r"\b" + re.escape(kw) + r"\b"), f_kw))
            for b in BUILTINS.get(lang, "").split():
                rules.append((QRegularExpression(r"\b" + re.escape(b) + r"\b"), f_builtin))

        if lang != "markdown":
            rules.append((QRegularExpression(
                r"\b(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|"
                r"\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b"), f_num))

        lc = LINE_COMMENT.get(lang)
        if lc:
            rules.append((QRegularExpression(re.escape(lc) + r".*$"), f_cmt))

        if lang != "markdown":
            rules.append((QRegularExpression(r'"(?:[^"\\]|\\.)*"'), f_str))
            if lang not in ("html", "xml"):
                rules.append((QRegularExpression(r"'(?:[^'\\]|\\.)*'"), f_str))
            if lang in ("javascript", "typescript"):
                rules.append((QRegularExpression(r"`(?:[^`\\]|\\.)*`"), f_str))

        self.rules = rules

        if lang == "python":
            self.multiline = [
                ('"""', '"""', 2, f_str),
                ("'''", "'''", 3, f_str),
            ]
        else:
            bc = BLOCK_COMMENT.get(lang)
            if bc:
                self.multiline = [(bc[0], bc[1], 1, f_cmt)]

    def highlightBlock(self, text):
        n = len(text)
        if n > 6000:
            self.setCurrentBlockState(-1)
            return

        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                length = m.capturedLength()
                if length > 0:
                    self.setFormat(m.capturedStart(), length, fmt)

        self.setCurrentBlockState(-1)
        if not self.multiline:
            return

        prev = self.previousBlockState()
        active = None
        region_start = 0
        search_from = 0
        for r in self.multiline:
            if prev == r[2]:
                active = r
                break

        pos = 0
        while True:
            if active is None:
                best_i, best_r = -1, None
                for r in self.multiline:
                    idx = text.find(r[0], pos)
                    if idx != -1 and (best_i == -1 or idx < best_i):
                        best_i, best_r = idx, r
                if best_r is None:
                    break
                active = best_r
                region_start = best_i
                search_from = best_i + len(best_r[0])
                pos = search_from
            else:
                start_d, end_d, state, fmt = active
                end_idx = text.find(end_d, search_from)
                if end_idx == -1:
                    self.setFormat(region_start, n - region_start, fmt)
                    self.setCurrentBlockState(state)
                    return
                self.setFormat(region_start, end_idx + len(end_d) - region_start, fmt)
                pos = end_idx + len(end_d)
                active = None
            if pos >= n:
                break


def detect_language(path: str) -> str:
    base = os.path.basename(path).lower()
    if base in NAME_LANG:
        return NAME_LANG[base]
    if base.startswith("dockerfile"):
        return "bash"
    ext = base.rsplit(".", 1)[-1] if "." in base else ""
    return EXT_LANG.get(ext, "text")


# ==============================================================================
# File icon cache
# ==============================================================================
_ICON_CACHE: Dict[str, QIcon] = {}


def get_file_icon(name: str) -> QIcon:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in _ICON_CACHE:
        return _ICON_CACHE[ext]
    colors = {
        "py": "#3776ab", "js": "#f7df1e", "ts": "#3178c6", "tsx": "#3178c6",
        "json": "#cbcb41", "html": "#e34c26", "css": "#563d7c", "scss": "#cd6799",
        "md": "#519aba", "sh": "#4eaa25", "bash": "#4eaa25", "yaml": "#cb171e",
        "yml": "#cb171e", "sql": "#e38c00", "go": "#00add8", "rs": "#dea584",
        "php": "#777bb4", "rb": "#cc342d", "conf": "#6c8ebf", "ini": "#6c8ebf",
        "c": "#555555", "h": "#a074c4", "cpp": "#f34b7d", "java": "#b07219",
        "cs": "#178600", "kt": "#a97bff", "swift": "#f05138", "txt": "#8a8a99",
        "xml": "#e37933", "lua": "#000080", "toml": "#9c4221",
    }
    color = colors.get(ext, "#8a8a99")
    pm = QPixmap(QSize(16, 16))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, 16, 16, 3, 3)
    p.end()
    icon = QIcon(pm)
    _ICON_CACHE[ext] = icon
    return icon


def get_folder_icon() -> QIcon:
    if "__folder__" in _ICON_CACHE:
        return _ICON_CACHE["__folder__"]
    pm = QPixmap(QSize(16, 16))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#89b4fa"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 2, 16, 14, 2, 2)
    p.end()
    icon = QIcon(pm)
    _ICON_CACHE["__folder__"] = icon
    return icon


# ==============================================================================
# SSH Session
# ==============================================================================
class SSHSession:
    """Thread-safety model:
       - get_sftp() returns a *shared* channel used ONLY from the GUI thread
         (mkdir/rename/new file). GUI ops are synchronous so never overlap.
       - new_sftp() returns a *fresh* channel for each background worker.
       Independent paramiko channels are safe to use concurrently; this avoids
       both data corruption AND any cross-thread lock that could freeze the UI.
    """

    def __init__(self, host, port, user, password="", key_path=""):
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
            kwargs = dict(hostname=self.host, port=self.port, username=self.user,
                          timeout=12, banner_timeout=12, auth_timeout=18)
            if self.key_path:
                self.ssh.connect(key_filename=self.key_path, **kwargs)
            else:
                self.ssh.connect(password=self.password, look_for_keys=False,
                                 allow_agent=False, **kwargs)
            tr = self.ssh.get_transport()
            if tr:
                tr.set_keepalive(30)
            self._sftp = self.ssh.open_sftp()
            return ""
        except paramiko.AuthenticationException:
            return "Authentication failed - wrong username or password/key"
        except (socket.timeout, TimeoutError):
            return "Connection timed out"
        except (socket.gaierror, OSError) as e:
            return f"Network error: {e}"
        except Exception as e:
            return str(e)

    def get_sftp(self) -> paramiko.SFTPClient:
        if self.ssh is None:
            raise RuntimeError("Not connected")
        if self._sftp is None or getattr(self._sftp, "sock", None) is None:
            self._sftp = self.ssh.open_sftp()
        return self._sftp

    def new_sftp(self) -> paramiko.SFTPClient:
        if self.ssh is None:
            raise RuntimeError("Not connected")
        return self.ssh.open_sftp()

    def open_shell(self, cols=120, rows=32):
        tr = self.ssh.get_transport()
        chan = tr.open_session()
        chan.get_pty(term="xterm-256color", width=cols, height=rows)
        chan.invoke_shell()
        return chan

    def is_alive(self) -> bool:
        try:
            tr = self.ssh.get_transport() if self.ssh else None
            return tr is not None and tr.is_active()
        except Exception:
            return False

    def close(self):
        for obj in (self._sftp, self.ssh):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        self._sftp = None
        self.ssh = None


# ==============================================================================
# Worker Threads
# ==============================================================================
class ConnectWorker(QThread):
    success = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, host, port, user, password="", key_path=""):
        super().__init__()
        self.args = (host, port, user, password, key_path)

    def run(self):
        sess = SSHSession(*self.args)
        err = sess.connect()
        if err:
            sess.close()
            self.failed.emit(err)
        else:
            self.success.emit(sess)


class DirWorker(QThread):
    done = pyqtSignal(str, list)
    failed = pyqtSignal(str, str)

    def __init__(self, sess: SSHSession, path: str):
        super().__init__()
        self.sess = sess
        self.path = path

    def run(self):
        sftp = None
        try:
            sftp = self.sess.new_sftp()
            items = []
            for a in sftp.listdir_attr(self.path):
                is_dir = _stat.S_ISDIR(a.st_mode) if a.st_mode else False
                items.append((a.filename, is_dir, a.st_size or 0))
            items.sort(key=lambda x: (not x[1], x[0].lower()))
            self.done.emit(self.path, items)
        except Exception as e:
            self.failed.emit(self.path, str(e))
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass


class ReadFileWorker(QThread):
    done = pyqtSignal(str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, sess: SSHSession, path: str):
        super().__init__()
        self.sess = sess
        self.path = path

    def run(self):
        sftp = None
        try:
            sftp = self.sess.new_sftp()
            st = sftp.stat(self.path)
            if (st.st_size or 0) > MAX_FILE_SIZE:
                self.failed.emit(self.path, "File too large (>8 MB)")
                return
            with sftp.open(self.path, "rb") as f:
                f.prefetch()
                raw = f.read()
            content = raw.decode("utf-8", errors="replace")
            self.done.emit(self.path, content)
        except Exception as e:
            self.failed.emit(self.path, str(e))
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass


class SaveFileWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str, str)

    def __init__(self, sess: SSHSession, path: str, content: str):
        super().__init__()
        self.sess = sess
        self.path = path
        self.content = content

    def run(self):
        sftp = None
        try:
            sftp = self.sess.new_sftp()
            data = self.content.encode("utf-8")
            with sftp.open(self.path, "wb") as f:
                f.write(data)
            self.done.emit(self.path)
        except Exception as e:
            self.failed.emit(self.path, str(e))
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass


class DeleteWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str, str)

    def __init__(self, sess: SSHSession, path: str, is_dir: bool):
        super().__init__()
        self.sess = sess
        self.path = path
        self.is_dir = is_dir

    def run(self):
        sftp = None
        try:
            sftp = self.sess.new_sftp()
            if self.is_dir:
                self._rmrf(sftp, self.path)
            else:
                sftp.remove(self.path)
            self.done.emit(self.path)
        except Exception as e:
            self.failed.emit(self.path, str(e))
        finally:
            if sftp:
                try:
                    sftp.close()
                except Exception:
                    pass

    def _rmrf(self, sftp, p):
        for a in sftp.listdir_attr(p):
            full = p.rstrip("/") + "/" + a.filename
            if a.st_mode and _stat.S_ISDIR(a.st_mode):
                self._rmrf(sftp, full)
            else:
                sftp.remove(full)
        sftp.rmdir(p)


# ==============================================================================
# Terminal: reader thread (cross-platform: NO select()) + ANSI-aware widget
# ==============================================================================
class TerminalReader(QThread):
    data = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self._run = True
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def run(self):
        ch = self.channel
        try:
            ch.settimeout(0.1)
        except Exception:
            pass
        while self._run:
            try:
                chunk = ch.recv(32768)
                if not chunk:
                    break
                self.data.emit(self._decoder.decode(chunk))
            except socket.timeout:
                continue
            except Exception:
                break
        self.closed.emit()

    def stop(self):
        self._run = False


def _xterm256(n: int):
    basic = [
        (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238),
        (205, 0, 205), (0, 205, 205), (229, 229, 229), (127, 127, 127),
        (255, 0, 0), (0, 255, 0), (255, 255, 0), (92, 92, 255),
        (255, 0, 255), (0, 255, 255), (255, 255, 255),
    ]
    if n < 16:
        return basic[n]
    if n >= 232:
        v = 8 + (n - 232) * 10
        return (v, v, v)
    n -= 16
    r, g, b = n // 36, (n % 36) // 6, n % 6
    conv = lambda x: 0 if x == 0 else 55 + 40 * x
    return (conv(r), conv(g), conv(b))


_ANSI_FG = {
    30: "#484f58", 31: "#ff7b72", 32: "#3fb950", 33: "#d29922",
    34: "#58a6ff", 35: "#bc8cff", 36: "#39c5cf", 37: "#b1bac4",
    90: "#6e7681", 91: "#ffa198", 92: "#56d364", 93: "#e3b341",
    94: "#79c0ff", 95: "#d2a8ff", 96: "#56d4dd", 97: "#f0f6fc",
}
_ANSI_BG = {k + 10: v for k, v in _ANSI_FG.items()}
DEFAULT_FG = "#e6edf3"
DEFAULT_BG = "#0d1117"

_SPECIAL_KEYS: Dict = {}


def _init_special_keys():
    k = Qt.Key
    return {
        k.Key_Return: b"\r", k.Key_Enter: b"\r", k.Key_Backspace: b"\x7f",
        k.Key_Tab: b"\t", k.Key_Escape: b"\x1b",
        k.Key_Up: b"\x1b[A", k.Key_Down: b"\x1b[B",
        k.Key_Right: b"\x1b[C", k.Key_Left: b"\x1b[D",
        k.Key_Home: b"\x1b[H", k.Key_End: b"\x1b[F",
        k.Key_PageUp: b"\x1b[5~", k.Key_PageDown: b"\x1b[6~",
        k.Key_Delete: b"\x1b[3~", k.Key_Insert: b"\x1b[2~",
        k.Key_F1: b"\x1bOP", k.Key_F2: b"\x1bOQ", k.Key_F3: b"\x1bOR",
        k.Key_F4: b"\x1bOS", k.Key_F5: b"\x1b[15~", k.Key_F6: b"\x1b[17~",
        k.Key_F7: b"\x1b[18~", k.Key_F8: b"\x1b[19~", k.Key_F9: b"\x1b[20~",
        k.Key_F10: b"\x1b[21~", k.Key_F11: b"\x1b[23~", k.Key_F12: b"\x1b[24~",
    }


class SSHTerminal(QPlainTextEdit):
    """Pragmatic ANSI-aware terminal: colours, line editing, erase, cursor
    moves and clear-screen -- enough for shells, package managers, git and most
    line-oriented apps. Not a full VT100 grid, but fast and cross-platform."""

    closed = pyqtSignal()

    def __init__(self, session: SSHSession, log_fn=None):
        super().__init__()
        self.session = session
        self._log = log_fn or (lambda *a, **k: None)
        self.channel = None
        self.reader: Optional[TerminalReader] = None
        self._pending = ""
        self._fmt = QTextCharFormat()
        self._fmt.setForeground(QColor(DEFAULT_FG))
        self._csi_re = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
        self._osc_re = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

        self.setFont(QFont(MONO, 11))
        self.setReadOnly(False)
        self.setUndoRedoEnabled(False)
        self.setMaximumBlockCount(8000)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCursorWidth(8)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        global _SPECIAL_KEYS
        if not _SPECIAL_KEYS:
            _SPECIAL_KEYS = _init_special_keys()

    def start(self):
        if not self.session.is_alive():
            self._log("ERROR", "Cannot start terminal: not connected")
            return False
        try:
            cols, rows = self._dims()
            self.channel = self.session.open_shell(cols, rows)
            self.reader = TerminalReader(self.channel)
            self.reader.data.connect(self._on_data)
            self.reader.closed.connect(self._on_closed)
            self.reader.start()
            self._log("INFO", "Terminal session started")
            return True
        except Exception as e:
            self._log("ERROR", f"Terminal start failed: {e}")
            return False

    def stop(self):
        if self.reader:
            self.reader.stop()
            self.reader.wait(1000)
            self.reader = None
        if self.channel:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None

    def _on_closed(self):
        self._write_plain("\n[Session closed]\n")
        self.channel = None
        self.closed.emit()

    def _dims(self):
        vp = self.viewport()
        w = vp.width() if vp else 800
        h = vp.height() if vp else 400
        fm = QFontMetricsF(self.font())
        cw = fm.horizontalAdvance("M") or 8.0
        ch = fm.height() or 16.0
        return max(20, int(w / cw)), max(5, int(h / ch))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.channel:
            try:
                cols, rows = self._dims()
                self.channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def _send(self, data: bytes):
        if self.channel and self.channel.active:
            try:
                self.channel.send(data)
            except Exception as e:
                self._log("ERROR", f"Send failed: {e}")

    def keyPressEvent(self, e):
        if self.channel is None:
            return
        key = e.key()
        mods = e.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)

        if ctrl and shift and key == Qt.Key.Key_C:
            self.copy(); return
        if ctrl and shift and key == Qt.Key.Key_V:
            self._paste(); return
        if ctrl and key == Qt.Key.Key_Insert:
            self.copy(); return
        if shift and key == Qt.Key.Key_Insert:
            self._paste(); return

        if key in _SPECIAL_KEYS:
            self._send(_SPECIAL_KEYS[key]); return

        if ctrl and not shift and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self._send(bytes([key - Qt.Key.Key_A + 1])); return
        if ctrl and key == Qt.Key.Key_Space:
            self._send(b"\x00"); return
        if ctrl and key == Qt.Key.Key_BracketLeft:
            self._send(b"\x1b"); return
        if ctrl and key == Qt.Key.Key_Backslash:
            self._send(b"\x1c"); return

        text = e.text()
        if text:
            data = text.encode("utf-8")
            if alt:
                data = b"\x1b" + data
            self._send(data)

    def _paste(self):
        cb = QApplication.clipboard()
        if cb:
            self._send(cb.text().encode("utf-8"))

    def insertFromMimeData(self, source):
        if source.hasText():
            self._send(source.text().encode("utf-8"))

    def _menu(self, pos):
        m = QMenu(self)
        a_copy = m.addAction("Copy  (Ctrl+Shift+C)")
        a_paste = m.addAction("Paste  (Ctrl+Shift+V)")
        m.addSeparator()
        a_clear = m.addAction("Clear")
        a_sel = m.addAction("Select All")
        a_copy.triggered.connect(self.copy)
        a_paste.triggered.connect(self._paste)
        a_clear.triggered.connect(self.clear)
        a_sel.triggered.connect(self.selectAll)
        m.exec(self.viewport().mapToGlobal(pos))

    def _on_data(self, text: str):
        sb = self.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 4
        self._process(text)
        if at_bottom:
            sb.setValue(sb.maximum())

    def _cursor(self) -> QTextCursor:
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        return c

    def _process(self, text: str):
        s = self._pending + text
        self._pending = ""
        i, n = 0, len(s)
        out = ""
        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        while i < n:
            c = s[i]
            if c == "\x1b":
                if i + 1 >= n:
                    self._pending = s[i:]; break
                nxt = s[i + 1]
                if nxt == "[":
                    m = self._csi_re.match(s, i)
                    if not m:
                        self._pending = s[i:]; break
                    self._flush(cur, out); out = ""
                    self._handle_csi(cur, m.group(0))
                    i = m.end(); continue
                elif nxt == "]":
                    m = self._osc_re.match(s, i)
                    if not m:
                        self._pending = s[i:]; break
                    i = m.end(); continue
                elif nxt in "()":
                    if i + 2 >= n:
                        self._pending = s[i:]; break
                    i += 3; continue
                else:
                    i += 2; continue
            elif c == "\r":
                self._flush(cur, out); out = ""
                cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                i += 1
            elif c == "\n":
                self._flush(cur, out); out = ""
                cur.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cur.insertText("\n"); i += 1
            elif c == "\b":
                self._flush(cur, out); out = ""
                if not cur.atBlockStart():
                    cur.movePosition(QTextCursor.MoveOperation.Left)
                i += 1
            elif c in ("\x07", "\x00"):
                i += 1
            else:
                out += c; i += 1
        self._flush(cur, out)
        self.setTextCursor(cur)

    def _flush(self, cur: QTextCursor, text: str):
        if not text:
            return
        for ch in text:
            if not cur.atBlockEnd():
                cur.movePosition(QTextCursor.MoveOperation.Right,
                                 QTextCursor.MoveMode.KeepAnchor)
                cur.removeSelectedText()
            cur.insertText(ch, self._fmt)

    def _write_plain(self, text: str):
        cur = self._cursor()
        cur.insertText(text)
        self.setTextCursor(cur)

    def _handle_csi(self, cur: QTextCursor, seq: str):
        final = seq[-1]
        body = seq[2:-1]
        if body.startswith("?"):
            return
        params = [int(p) if p else 0 for p in body.split(";")] if body else []

        if final == "m":
            self._apply_sgr(params or [0])
        elif final == "K":
            mode = params[0] if params else 0
            if mode == 0:
                cur.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                 QTextCursor.MoveMode.KeepAnchor)
            elif mode == 1:
                cur.movePosition(QTextCursor.MoveOperation.StartOfBlock,
                                 QTextCursor.MoveMode.KeepAnchor)
            else:
                cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cur.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                 QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
        elif final == "J":
            mode = params[0] if params else 0
            if mode in (2, 3):
                self.clear()
                cur.movePosition(QTextCursor.MoveOperation.End)
            else:
                cur.movePosition(QTextCursor.MoveOperation.End,
                                 QTextCursor.MoveMode.KeepAnchor)
                cur.removeSelectedText()
        elif final == "C":
            for _ in range(max(1, params[0] if params else 1)):
                if cur.atBlockEnd():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Right)
        elif final == "D":
            for _ in range(max(1, params[0] if params else 1)):
                if cur.atBlockStart():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Left)
        elif final in ("G", "`"):
            col = (params[0] if params else 1) - 1
            cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            for _ in range(col):
                if cur.atBlockEnd():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Right)

    def _apply_sgr(self, params: List[int]):
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self._fmt = QTextCharFormat()
                self._fmt.setForeground(QColor(DEFAULT_FG))
            elif p == 1:
                self._fmt.setFontWeight(QFont.Weight.Bold)
            elif p == 22:
                self._fmt.setFontWeight(QFont.Weight.Normal)
            elif p == 3:
                self._fmt.setFontItalic(True)
            elif p == 4:
                self._fmt.setFontUnderline(True)
            elif p == 23:
                self._fmt.setFontItalic(False)
            elif p == 24:
                self._fmt.setFontUnderline(False)
            elif p == 39:
                self._fmt.setForeground(QColor(DEFAULT_FG))
            elif p == 49:
                self._fmt.clearBackground()
            elif p in _ANSI_FG:
                self._fmt.setForeground(QColor(_ANSI_FG[p]))
            elif p in _ANSI_BG:
                self._fmt.setBackground(QColor(_ANSI_BG[p]))
            elif p in (38, 48):
                is_fg = p == 38
                if i + 1 < len(params) and params[i + 1] == 5 and i + 2 < len(params):
                    r, g, b = _xterm256(params[i + 2]); i += 2
                elif i + 1 < len(params) and params[i + 1] == 2 and i + 4 < len(params):
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]; i += 4
                else:
                    i += 1; continue
                col = QColor(r, g, b)
                if is_fg:
                    self._fmt.setForeground(col)
                else:
                    self._fmt.setBackground(col)
            i += 1


# ==============================================================================
# Code editor with line numbers + current-line highlight (VSCode style)
# ==============================================================================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._search_selections: List = []
        self.blockCountChanged.connect(self._update_width)
        self.updateRequest.connect(self._update_area)
        self.cursorPositionChanged.connect(self._refresh_selections)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(MONO, 11))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self._update_width(0)

    # ---- gutter ----
    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(),
                                         self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#0d1117"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        cur_line = self.textCursor().blockNumber()
        fh = self.fontMetrics().height()
        width = self.line_number_area.width() - 8
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#e6edf3") if block_number == cur_line
                               else QColor("#636c76"))
                painter.drawText(0, top, width, fh,
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # ---- extra selections (current line + search highlights) ----
    def set_search_selections(self, sels):
        self._search_selections = sels or []
        self._refresh_selections()

    def _refresh_selections(self):
        sels = []
        if not self.isReadOnly():
            line_sel = QTextEdit.ExtraSelection()
            line_sel.format.setBackground(QColor("#161d2b"))
            line_sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            line_sel.cursor = self.textCursor()
            line_sel.cursor.clearSelection()
            sels.append(line_sel)
        sels.extend(self._search_selections)
        self.setExtraSelections(sels)
        self.line_number_area.update()

    # ---- editing niceties (VSCode-like) ----
    def keyPressEvent(self, e):
        if self.isReadOnly():
            super().keyPressEvent(e)
            return
        key = e.key()
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if key == Qt.Key.Key_Tab and not shift:
            cur = self.textCursor()
            if cur.hasSelection():
                self._change_indent(True)
            else:
                cur.insertText("    ")
            return
        if key == Qt.Key.Key_Backtab:  # Shift+Tab
            self._change_indent(False)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            block_text = self.textCursor().block().text()
            indent = ""
            for ch in block_text:
                if ch in " \t":
                    indent += ch
                else:
                    break
            super().keyPressEvent(e)
            if indent:
                self.textCursor().insertText(indent)
            return
        super().keyPressEvent(e)

    def _change_indent(self, indent: bool):
        cur = self.textCursor()
        doc = self.document()
        start_block = doc.findBlock(cur.selectionStart()).blockNumber()
        end_pos = cur.selectionEnd()
        end_block_obj = doc.findBlock(end_pos)
        end_block = end_block_obj.blockNumber()
        if end_block > start_block and end_pos == end_block_obj.position():
            end_block -= 1
        cur.beginEditBlock()
        for bn in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(bn)
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if indent:
                c.insertText("    ")
            else:
                t = block.text()
                if t.startswith("    "):
                    for _ in range(4):
                        c.deleteChar()
                elif t.startswith("\t"):
                    c.deleteChar()
                else:
                    n = len(t) - len(t.lstrip(" "))
                    for _ in range(min(n, 4)):
                        c.deleteChar()
        cur.endEditBlock()


# ==============================================================================
# Find / Replace bar (editor)
# ==============================================================================
class FindBar(QWidget):
    def __init__(self, editor: CodeEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setVisible(False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(2)

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        self.find_in = QLineEdit()
        self.find_in.setPlaceholderText("Find")
        self.find_in.textChanged.connect(self._highlight_all)
        self.find_in.returnPressed.connect(self.find_next)
        row1.addWidget(self.find_in, 1)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("color:#8b949e; font-size:11px;")
        row1.addWidget(self.count_lbl)

        self.case_cb = QCheckBox("Aa")
        self.case_cb.setToolTip("Match case")
        self.case_cb.toggled.connect(self._highlight_all)
        row1.addWidget(self.case_cb)

        self.word_cb = QCheckBox("W")
        self.word_cb.setToolTip("Whole word")
        self.word_cb.toggled.connect(self._highlight_all)
        row1.addWidget(self.word_cb)

        prev_b = QToolButton(); prev_b.setText("\u2191"); prev_b.setToolTip("Previous (Shift+Enter)")
        prev_b.clicked.connect(self.find_prev)
        next_b = QToolButton(); next_b.setText("\u2193"); next_b.setToolTip("Next (Enter)")
        next_b.clicked.connect(self.find_next)
        self.toggle_rep = QToolButton(); self.toggle_rep.setText("\u21c5"); self.toggle_rep.setCheckable(True)
        self.toggle_rep.setToolTip("Toggle replace")
        self.toggle_rep.toggled.connect(self._toggle_replace)
        close_b = QToolButton(); close_b.setText("\u00d7"); close_b.setToolTip("Close (Esc)")
        close_b.clicked.connect(self.hide_bar)
        for b in (prev_b, next_b, self.toggle_rep, close_b):
            row1.addWidget(b)
        outer.addLayout(row1)

        self.rep_widget = QWidget()
        row2 = QHBoxLayout(self.rep_widget)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(4)
        self.rep_in = QLineEdit()
        self.rep_in.setPlaceholderText("Replace")
        self.rep_in.returnPressed.connect(self.replace_one)
        row2.addWidget(self.rep_in, 1)
        rep_b = QPushButton("Replace"); rep_b.clicked.connect(self.replace_one)
        rep_all_b = QPushButton("All"); rep_all_b.clicked.connect(self.replace_all)
        row2.addWidget(rep_b); row2.addWidget(rep_all_b)
        self.rep_widget.setVisible(False)
        outer.addWidget(self.rep_widget)

    def _flags(self, backward=False):
        f = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            f |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_cb.isChecked():
            f |= QTextDocument.FindFlag.FindWholeWords
        if backward:
            f |= QTextDocument.FindFlag.FindBackward
        return f

    def _toggle_replace(self, on):
        self.rep_widget.setVisible(on)
        if on:
            self.rep_in.setFocus()

    def show_bar(self, replace=False):
        self.setVisible(True)
        if replace:
            self.toggle_rep.setChecked(True)
        sel = self.editor.textCursor().selectedText()
        if sel and "\u2029" not in sel:
            self.find_in.setText(sel)
        self.find_in.setFocus()
        self.find_in.selectAll()
        self._highlight_all()

    def hide_bar(self):
        self.setVisible(False)
        self.editor.set_search_selections([])
        self.editor.setFocus()

    def _highlight_all(self):
        text = self.find_in.text()
        selections = []
        count = 0
        if text:
            doc = self.editor.document()
            cur = QTextCursor(doc)
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#3b5070"))
            while count < MAX_HIGHLIGHTS:
                cur = doc.find(text, cur, self._flags())
                if cur.isNull():
                    break
                count += 1
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cur
                sel.format = fmt
                selections.append(sel)
        self.editor.set_search_selections(selections)
        self.count_lbl.setText(f"{count} found" if text else "")

    def find_next(self):
        if not self.editor.find(self.find_in.text(), self._flags()):
            cur = self.editor.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cur)
            self.editor.find(self.find_in.text(), self._flags())

    def find_prev(self):
        if not self.editor.find(self.find_in.text(), self._flags(backward=True)):
            cur = self.editor.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cur)
            self.editor.find(self.find_in.text(), self._flags(backward=True))

    def replace_one(self):
        cur = self.editor.textCursor()
        target = self.find_in.text()
        matched = cur.hasSelection() and (
            cur.selectedText() == target or
            (not self.case_cb.isChecked() and cur.selectedText().lower() == target.lower()))
        if matched:
            cur.insertText(self.rep_in.text())
        self.find_next()
        self._highlight_all()

    def replace_all(self):
        text, rep = self.find_in.text(), self.rep_in.text()
        if not text:
            return
        doc = self.editor.document()
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        find_cur = QTextCursor(doc)
        n = 0
        while True:
            find_cur = doc.find(text, find_cur, self._flags())
            if find_cur.isNull():
                break
            find_cur.insertText(rep)
            n += 1
        cur.endEditBlock()
        self._highlight_all()
        self.count_lbl.setText(f"{n} replaced")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.find_prev()
        else:
            super().keyPressEvent(e)


# ==============================================================================
# Login Dialog (profiles + remembered credentials)
# ==============================================================================
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Connect")
        self.setFixedSize(440, 480)
        self.session: Optional[SSHSession] = None
        self.config = load_config()
        self.use_key = False
        self.worker: Optional[ConnectWorker] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(22, 20, 22, 20)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Fast SSH/SFTP editor & terminal")
        sub.setStyleSheet("color:#8b949e; font-size:11px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)
        layout.addSpacing(6)

        prof_row = QHBoxLayout()
        prof_row.addWidget(QLabel("Saved:"))
        self.profile_cb = QComboBox()
        self.profile_cb.addItem("New connection", None)
        for p in self.config.get("profiles", []):
            self.profile_cb.addItem(p.get("name") or p.get("host", ""), p)
        self.profile_cb.currentIndexChanged.connect(self._load_profile)
        prof_row.addWidget(self.profile_cb, 1)
        self.del_btn = QToolButton(); self.del_btn.setText("\U0001f5d1")
        self.del_btn.setToolTip("Delete selected profile")
        self.del_btn.clicked.connect(self._delete_profile)
        prof_row.addWidget(self.del_btn)
        layout.addLayout(prof_row)

        layout.addWidget(QLabel("Host:"))
        self.host_in = QLineEdit()
        self.host_in.setPlaceholderText("192.168.1.1 or hostname")
        layout.addWidget(self.host_in)

        row = QHBoxLayout()
        row.addWidget(QLabel("Port:"))
        self.port_in = QLineEdit("22")
        self.port_in.setFixedWidth(60)
        row.addWidget(self.port_in)
        row.addSpacing(10)
        row.addWidget(QLabel("User:"))
        self.user_in = QLineEdit("root")
        row.addWidget(self.user_in, 1)
        layout.addLayout(row)

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
        auth_row.addWidget(self.auth_in, 1)
        self.show_btn = QToolButton(); self.show_btn.setText("\U0001f441"); self.show_btn.setCheckable(True)
        self.show_btn.setToolTip("Show / hide")
        self.show_btn.toggled.connect(self._toggle_show)
        auth_row.addWidget(self.show_btn)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setVisible(False)
        self.browse_btn.clicked.connect(self._browse_key)
        auth_row.addWidget(self.browse_btn)
        layout.addLayout(auth_row)

        opt_row = QHBoxLayout()
        self.remember_cb = QCheckBox("Remember credentials")
        self.remember_cb.setToolTip("Save host/user AND password/key for this profile")
        opt_row.addWidget(self.remember_cb)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        warn = QLabel("Saved credentials are stored locally (base64, NOT encrypted).")
        warn.setStyleSheet("color:#6e7681; font-size:10px;")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color:#f85149; font-size:11px;")
        layout.addWidget(self.status_lbl)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("font-size:14px; padding:8px; font-weight:700;")
        self.connect_btn.clicked.connect(self._connect)
        layout.addWidget(self.connect_btn)

        last = self.config.get("last", "")
        if last:
            for i in range(self.profile_cb.count()):
                p = self.profile_cb.itemData(i)
                if p and p.get("name") == last:
                    self.profile_cb.setCurrentIndex(i)
                    break

    def _toggle_show(self, on):
        if not self.use_key:
            self.auth_in.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)

    def _set_key_mode(self, on):
        self.use_key = on
        if on:
            self.auth_label.setText("Private Key:")
            self.auth_in.setEchoMode(QLineEdit.EchoMode.Normal)
            self.auth_in.setPlaceholderText("Path to private key")
            self.browse_btn.setVisible(True)
            self.show_btn.setVisible(False)
            self.auth_type_btn.setText("Use Password")
            self.auth_type_btn.setChecked(True)
        else:
            self.auth_label.setText("Password:")
            self.auth_in.setEchoMode(
                QLineEdit.EchoMode.Normal if self.show_btn.isChecked()
                else QLineEdit.EchoMode.Password)
            self.auth_in.setPlaceholderText("Enter password")
            self.browse_btn.setVisible(False)
            self.show_btn.setVisible(True)
            self.auth_type_btn.setText("Use Private Key")
            self.auth_type_btn.setChecked(False)

    def _toggle_auth(self):
        self._set_key_mode(not self.use_key)

    def _browse_key(self):
        start = os.path.expanduser("~/.ssh")
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Select Private Key", start)
        if path:
            self.auth_in.setText(path)

    def _load_profile(self):
        p = self.profile_cb.currentData()
        if not p:
            self.host_in.clear(); self.port_in.setText("22")
            self.user_in.setText("root"); self.auth_in.clear()
            self._set_key_mode(False)
            self.remember_cb.setChecked(False)
        else:
            self.host_in.setText(p.get("host", ""))
            self.port_in.setText(str(p.get("port", 22)))
            self.user_in.setText(p.get("user", "root"))
            self._set_key_mode(p.get("auth") == "key")
            if p.get("auth") == "key":
                self.auth_in.setText(p.get("key_path", ""))
            else:
                self.auth_in.setText(_b64d(p.get("password", "")))
            self.remember_cb.setChecked(bool(p.get("remember", False)))

    def _delete_profile(self):
        p = self.profile_cb.currentData()
        if not p:
            return
        self.config["profiles"] = [
            x for x in self.config.get("profiles", []) if x.get("name") != p.get("name")]
        save_config(self.config)
        self.profile_cb.removeItem(self.profile_cb.currentIndex())

    def _connect(self):
        host = self.host_in.text().strip()
        user = self.user_in.text().strip()
        if not host or not user:
            self.status_lbl.setText("Please enter Host and Username")
            return
        try:
            port = int(self.port_in.text())
            if not (0 < port < 65536):
                raise ValueError
        except ValueError:
            self.status_lbl.setText("Invalid port number")
            return

        password = key_path = ""
        if self.use_key:
            key_path = self.auth_in.text().strip()
            if key_path and not os.path.isfile(key_path):
                self.status_lbl.setText("Key file not found")
                return
        else:
            password = self.auth_in.text()

        name = f"{user}@{host}"
        remember = self.remember_cb.isChecked()
        profile = {
            "name": name, "host": host, "port": port, "user": user,
            "auth": "key" if self.use_key else "password",
            "remember": remember,
            "key_path": key_path if remember else "",
            "password": _b64e(password) if (remember and not self.use_key) else "",
        }
        profs = [x for x in self.config.get("profiles", []) if x.get("name") != name]
        profs.insert(0, profile)
        self.config["profiles"] = profs[:15]
        self.config["last"] = name
        save_config(self.config)

        self.connect_btn.setEnabled(False)
        self.status_lbl.setText("Connecting...")
        self.status_lbl.setStyleSheet("color:#8b949e; font-size:11px;")

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
        self.status_lbl.setStyleSheet("color:#f85149; font-size:11px;")


# ==============================================================================
# Main Window
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self, session: SSHSession):
        super().__init__()
        self.session = session
        self.current_path = "/"
        self.home_path = "/"
        self.modified = False
        self._workers: List[QThread] = []
        self.current_file: Optional[str] = None
        self._highlighter: Optional[CodeHighlighter] = None
        self._loading_file = False
        self.terminal: Optional[SSHTerminal] = None
        self.news_manager: Optional[QNetworkAccessManager] = None
        self.reconnect_worker: Optional[ConnectWorker] = None

        self.setWindowTitle(f"{APP_NAME} - {session.user}@{session.host}")
        self.setWindowIcon(build_app_icon())
        self.setMinimumSize(900, 560)
        self.resize(1240, 760)

        self._build()
        self._setup_news_banner()
        self._start_terminal()
        self._start_keepalive()
        self.log("INFO", f"Connected to {session.user}@{session.host}:{session.port}")

        try:
            self.home_path = remote_norm(session.get_sftp().normalize("."))
        except Exception:
            self.home_path = "/"
        self._list_dir(self.home_path)

    # ---------- UI build ----------
    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(4)
        root.setContentsMargins(6, 6, 6, 6)

        path_bar = QHBoxLayout()
        path_bar.setSpacing(4)
        self.home_btn = QPushButton("Home"); self.home_btn.setFixedWidth(70)
        self.home_btn.clicked.connect(self._go_home)
        path_bar.addWidget(self.home_btn)
        self.up_btn = QPushButton("Up"); self.up_btn.setFixedWidth(55)
        self.up_btn.clicked.connect(self._go_up)
        path_bar.addWidget(self.up_btn)
        self.refresh_btn = QPushButton("Refresh"); self.refresh_btn.setFixedWidth(75)
        self.refresh_btn.setToolTip("Refresh (F5)")
        self.refresh_btn.clicked.connect(lambda: self._list_dir(self.current_path))
        path_bar.addWidget(self.refresh_btn)
        self.path_in = QLineEdit(); self.path_in.setFont(QFont(MONO, 10))
        self.path_in.returnPressed.connect(self._go_path)
        path_bar.addWidget(self.path_in, 1)
        go_btn = QPushButton("Go"); go_btn.setFixedWidth(50)
        go_btn.clicked.connect(self._go_path)
        path_bar.addWidget(go_btn)
        root.addLayout(path_bar)

        # news banner (hidden until news loads)
        self.news_container = QWidget()
        nl = QHBoxLayout(self.news_container)
        nl.setContentsMargins(0, 0, 0, 0); nl.setSpacing(4)
        self.news_label = QLabel()
        self.news_label.setStyleSheet(
            "QLabel{background:#1f2a3e;color:#79c0ff;padding:4px 8px;"
            "font-size:11px;border-radius:4px;}")
        self.news_label.setWordWrap(True)
        self.news_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.news_label.setOpenExternalLinks(True)
        news_close = QPushButton("\u00d7"); news_close.setFixedSize(20, 20)
        news_close.clicked.connect(self.news_container.hide)
        nl.addWidget(self.news_label, 1); nl.addWidget(news_close)
        self.news_container.hide()
        root.addWidget(self.news_container)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_list = QListWidget()
        self.file_list.setFont(QFont(MONO, 10))
        self.file_list.setIconSize(QSize(16, 16))
        self.file_list.itemDoubleClicked.connect(self._on_item_double_click)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._context_menu)
        splitter.addWidget(self.file_list)

        right_split = QSplitter(Qt.Orientation.Vertical)

        editor_area = QWidget()
        ea = QVBoxLayout(editor_area)
        ea.setContentsMargins(0, 0, 0, 0); ea.setSpacing(2)
        self.file_info_lbl = QLabel("No file selected")
        self.file_info_lbl.setStyleSheet("font-size:10px; padding:2px 6px;")
        ea.addWidget(self.file_info_lbl)

        self.editor = CodeEditor()
        self.editor.setReadOnly(True)
        self.editor.document().modificationChanged.connect(self._on_modification_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_pos)

        self.find_bar = FindBar(self.editor)
        ea.addWidget(self.find_bar)
        ea.addWidget(self.editor, 1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        self.save_btn = QPushButton("Save  (Ctrl+S)"); self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_file)
        btn_row.addWidget(self.save_btn)
        self.find_btn = QPushButton("Find  (Ctrl+F)"); self.find_btn.setEnabled(False)
        self.find_btn.clicked.connect(self._show_find)
        btn_row.addWidget(self.find_btn)
        self.close_btn = QPushButton("Close  (Ctrl+W)"); self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self._close_file)
        btn_row.addWidget(self.close_btn)
        btn_row.addStretch()
        ea.addLayout(btn_row)
        right_split.addWidget(editor_area)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setTabPosition(QTabWidget.TabPosition.North)

        term_wrap = QWidget()
        tw = QVBoxLayout(term_wrap)
        tw.setContentsMargins(0, 0, 0, 0); tw.setSpacing(2)
        term_toolbar = QHBoxLayout(); term_toolbar.setSpacing(4)
        self.term_restart_btn = QPushButton("Restart shell")
        self.term_restart_btn.clicked.connect(self._restart_terminal)
        self.term_clear_btn = QPushButton("Clear")
        self.term_clear_btn.clicked.connect(self._clear_terminal)
        term_toolbar.addWidget(self.term_restart_btn)
        term_toolbar.addWidget(self.term_clear_btn)
        term_toolbar.addStretch()
        hint = QLabel("Ctrl+Shift+C copy  -  Ctrl+Shift+V paste  -  Ctrl+C interrupt")
        hint.setStyleSheet("color:#6e7681; font-size:10px;")
        term_toolbar.addWidget(hint)
        tw.addLayout(term_toolbar)
        self.terminal = SSHTerminal(self.session, log_fn=self.log)
        tw.addWidget(self.terminal, 1)
        self.bottom_tabs.addTab(term_wrap, "Terminal")

        logs_wrap = QWidget()
        lw = QVBoxLayout(logs_wrap)
        lw.setContentsMargins(0, 0, 0, 0); lw.setSpacing(2)
        log_toolbar = QHBoxLayout(); log_toolbar.setSpacing(4)
        self.log_copy_btn = QPushButton("Copy logs")
        self.log_copy_btn.clicked.connect(self._copy_logs)
        self.log_clear_btn = QPushButton("Clear logs")
        self.log_clear_btn.clicked.connect(lambda: self.logs.clear())
        log_toolbar.addWidget(self.log_copy_btn)
        log_toolbar.addWidget(self.log_clear_btn)
        log_toolbar.addStretch()
        lw.addLayout(log_toolbar)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFont(QFont(MONO, 10))
        self.logs.setMaximumBlockCount(5000)
        lw.addWidget(self.logs, 1)
        self.bottom_tabs.addTab(logs_wrap, "Logs")

        right_split.addWidget(self.bottom_tabs)
        right_split.setSizes([460, 300])
        splitter.addWidget(right_split)
        splitter.setSizes([320, 920])
        root.addWidget(splitter, 1)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.conn_dot = QLabel("\u25cf")
        self.conn_text = QLabel("Connecting...")
        self.conn_text.setStyleSheet("color:#8b949e;")
        self.reconnect_btn = QPushButton("Reconnect")
        self.reconnect_btn.setFixedHeight(22)
        self.reconnect_btn.clicked.connect(self._reconnect)
        self.status.addWidget(self.conn_dot)
        self.status.addWidget(self.conn_text)
        self.status.addPermanentWidget(self.reconnect_btn)
        self._msg = QLabel("Ready")
        self._msg.setStyleSheet("color:#8b949e;")
        self.status.addWidget(QLabel("  |  "))
        self.status.addWidget(self._msg, 1)
        self.pos_lbl = QLabel("")
        self.pos_lbl.setStyleSheet("color:#8b949e;")
        self.lang_lbl = QLabel("")
        self.lang_lbl.setStyleSheet("color:#8b949e;")
        self.status.addPermanentWidget(self.pos_lbl)
        self.status.addPermanentWidget(self.lang_lbl)

        # shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_file)
        QShortcut(QKeySequence("Ctrl+F"), self, self._show_find)
        QShortcut(QKeySequence("Ctrl+H"), self, self._show_replace)
        QShortcut(QKeySequence("Ctrl+G"), self, self._goto_line)
        QShortcut(QKeySequence("F5"), self, lambda: self._list_dir(self.current_path))
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_file)
        QShortcut(QKeySequence("Ctrl+`"), self, self._focus_terminal)
        QShortcut(QKeySequence("Alt+Z"), self, self._toggle_wrap)
        QShortcut(QKeySequence("Escape"), self.editor, self.find_bar.hide_bar)

    def show_msg(self, text: str):
        self._msg.setText(text)

    # ---------- status / keepalive ----------
    def _start_keepalive(self):
        self.ka_timer = QTimer(self)
        self.ka_timer.timeout.connect(self._check_conn)
        self.ka_timer.start(5000)
        self._check_conn()

    def _check_conn(self):
        if self.session.is_alive():
            self.conn_dot.setStyleSheet("color:#3fb950; font-size:14px;")
            self.conn_text.setText(f"Connected - {self.session.user}@{self.session.host}")
        else:
            self.conn_dot.setStyleSheet("color:#f85149; font-size:14px;")
            self.conn_text.setText("Disconnected")
        self.reconnect_btn.setEnabled(True)

    def _reconnect(self):
        self.log("INFO", "Reconnecting...")
        self.conn_dot.setStyleSheet("color:#d29922; font-size:14px;")
        self.conn_text.setText("Reconnecting...")
        self.reconnect_btn.setEnabled(False)
        old = self.session
        self.reconnect_worker = ConnectWorker(old.host, old.port, old.user,
                                              old.password, old.key_path)
        self.reconnect_worker.success.connect(self._on_reconnected)
        self.reconnect_worker.failed.connect(self._on_reconnect_failed)
        self.reconnect_worker.start()

    def _on_reconnected(self, sess: SSHSession):
        try:
            self.session.close()
        except Exception:
            pass
        self.session = sess
        if self.terminal:
            self.terminal.session = sess
        self.log("INFO", "Reconnected successfully")
        self._check_conn()
        self._restart_terminal()
        self._list_dir(self.current_path)

    def _on_reconnect_failed(self, err: str):
        self.log("ERROR", f"Reconnect failed: {err}")
        self._check_conn()
        QMessageBox.critical(self, "Reconnect Failed", err)

    # ---------- logs ----------
    def log(self, level: str, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        color = {"INFO": "#58a6ff", "ERROR": "#f85149", "WARN": "#d29922"}.get(level, "#8b949e")
        msg = (msg or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.logs.appendHtml(
            f'<span style="color:#6e7681">[{ts}]</span> '
            f'<span style="color:{color}">{level}</span> '
            f'<span style="color:#e6edf3">{msg}</span>')

    def _copy_logs(self):
        QApplication.clipboard().setText(self.logs.toPlainText())
        self.show_msg("Logs copied to clipboard")
        QTimer.singleShot(2500, lambda: self.show_msg("Ready"))

    # ---------- terminal ----------
    def _start_terminal(self):
        if self.terminal:
            self.terminal.start()

    def _restart_terminal(self):
        if self.terminal:
            self.terminal.stop()
            self.terminal.clear()
            self.terminal.start()

    def _clear_terminal(self):
        if self.terminal:
            self.terminal.clear()

    def _focus_terminal(self):
        self.bottom_tabs.setCurrentIndex(0)
        if self.terminal:
            self.terminal.setFocus()

    # ---------- editor helpers ----------
    def _show_find(self):
        if self.current_file:
            self.find_bar.show_bar(replace=False)

    def _show_replace(self):
        if self.current_file:
            self.find_bar.show_bar(replace=True)

    def _toggle_wrap(self):
        mode = self.editor.lineWrapMode()
        if mode == QPlainTextEdit.LineWrapMode.NoWrap:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            self.show_msg("Word wrap: ON")
        else:
            self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            self.show_msg("Word wrap: OFF")

    def _goto_line(self):
        if not self.current_file:
            return
        total = self.editor.blockCount()
        cur_line = self.editor.textCursor().blockNumber() + 1
        line, ok = QInputDialog.getInt(self, "Go to Line",
                                       f"Line (1-{total}):", cur_line, 1, total)
        if ok:
            block = self.editor.document().findBlockByNumber(line - 1)
            cur = QTextCursor(block)
            self.editor.setTextCursor(cur)
            self.editor.centerCursor()
            self.editor.setFocus()

    def _update_cursor_pos(self):
        if not self.current_file:
            self.pos_lbl.setText("")
            return
        cur = self.editor.textCursor()
        self.pos_lbl.setText(f"Ln {cur.blockNumber() + 1}, Col {cur.columnNumber() + 1}")

    # ---------- news ----------
    def _setup_news_banner(self):
        QTimer.singleShot(600, self._fetch_news)

    def _fetch_news(self):
        try:
            self.news_manager = QNetworkAccessManager()
            self.news_manager.finished.connect(self._on_news)
            self.news_manager.get(QNetworkRequest(QUrl(NEWS_URL)))
        except Exception:
            pass

    def _on_news(self, reply: QNetworkReply):
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                d = json.loads(bytes(reply.readAll().data()).decode("utf-8"))
                text, link = d.get("text", ""), d.get("link", "")
                if text:
                    text = text.replace("<", "&lt;").replace(">", "&gt;")
                    disp = (f'<a href="{link}" style="color:#79c0ff;'
                            f'text-decoration:none;">{text}</a>') if link else text
                    self.news_label.setText(disp)
                    self.news_container.show()
                    QTimer.singleShot(15000, self.news_container.hide)
        except Exception:
            pass
        finally:
            reply.deleteLater()

    # ---------- file browser ----------
    def _track_worker(self, w: QThread):
        self._workers.append(w)

        def cleanup():
            try:
                self._workers.remove(w)
            except ValueError:
                pass
            w.deleteLater()

        w.finished.connect(cleanup)
        return w

    def _go_home(self):
        self._list_dir(self.home_path)

    def _go_up(self):
        self._list_dir(remote_parent(self.current_path))

    def _go_path(self):
        path = self.path_in.text().strip()
        if not path:
            return
        if not path.startswith("/"):
            path = self.current_path.rstrip("/") + "/" + path
        self._list_dir(remote_norm(path))

    def _list_dir(self, path: str):
        if not self.session.is_alive():
            self.show_msg("Connection lost - please reconnect")
            return
        path = remote_norm(path)
        self.current_path = path
        self.path_in.setText(path)
        self.show_msg(f"Loading {path}...")
        w = DirWorker(self.session, path)
        w.done.connect(self._populate_list)
        w.failed.connect(self._on_dir_error)
        self._track_worker(w)
        w.start()

    def _on_dir_error(self, path: str, err: str):
        self.show_msg(f"Error: {err}")
        self.log("ERROR", f"List {path}: {err}")

    def _populate_list(self, path: str, items: list):
        if path != self.current_path:
            return
        self.path_in.setText(path)
        self.show_msg(f"{path}   ({len(items)} items)")
        self.file_list.clear()
        for name, is_dir, size in items:
            it = QListWidgetItem(f"{name}{'/' if is_dir else ''}")
            it.setIcon(get_folder_icon() if is_dir else get_file_icon(name))
            it.setData(Qt.ItemDataRole.UserRole, {
                "name": name, "is_dir": is_dir,
                "path": remote_join(path, name), "size": size})
            if not is_dir:
                it.setToolTip(f"{name} - {self._fmt_size(size)}")
            self.file_list.addItem(it)

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

    # ---------- editor ----------
    def _open_file(self, path: str):
        if not self.session.is_alive():
            QMessageBox.critical(self, "Error", "Connection lost")
            return
        if self.modified:
            if QMessageBox.question(
                self, "Unsaved changes",
                "The current file has unsaved changes. Open another anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        self.show_msg(f"Opening {path}...")
        w = ReadFileWorker(self.session, path)
        w.done.connect(self._on_file_loaded)
        w.failed.connect(self._on_file_error)
        self._track_worker(w)
        w.start()

    def _on_file_loaded(self, path: str, content: str):
        self._loading_file = True
        self.current_file = path
        self.modified = False
        self.editor.setReadOnly(False)
        self.editor.setPlainText(content)
        self.editor.document().setModified(False)
        cur = self.editor.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cur)
        self._loading_file = False

        self.file_info_lbl.setText(f"Editing: {path}")
        self.save_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.find_btn.setEnabled(True)
        self.show_msg(f"Opened: {path}")
        self.log("INFO", f"Opened {path}")

        lang = detect_language(path)
        self.lang_lbl.setText(lang.capitalize() if lang != "text" else "Plain Text")
        if self._highlighter is not None:
            self._highlighter.setDocument(None)
            self._highlighter = None
        self._highlighter = CodeHighlighter(self.editor.document(), lang)
        self._update_cursor_pos()
        self.editor.setFocus()

    def _on_file_error(self, path: str, error: str):
        QMessageBox.warning(self, "Error", f"Cannot open {path}\n\n{error}")
        self.show_msg("Open failed")
        self.log("ERROR", f"Open {path}: {error}")

    def _on_modification_changed(self, modified: bool):
        if self._loading_file:
            return
        self.modified = modified
        if self.current_file:
            mark = "* " if modified else ""
            self.file_info_lbl.setText(f"{mark}Editing: {self.current_file}")

    def _save_file(self):
        if not self.current_file or not self.modified:
            return
        if not self.session.is_alive():
            QMessageBox.critical(self, "Error", "Connection lost")
            return
        content = self.editor.toPlainText()
        self.show_msg(f"Saving {self.current_file}...")
        w = SaveFileWorker(self.session, self.current_file, content)
        w.done.connect(self._on_saved)
        w.failed.connect(self._on_save_error)
        self._track_worker(w)
        w.start()

    def _on_saved(self, path: str):
        if path == self.current_file:
            self.editor.document().setModified(False)
        fn = os.path.basename(path)
        self.show_msg(f"Saved: {fn}")
        self.log("INFO", f"Saved {path}")
        QTimer.singleShot(3000, lambda: self.show_msg(f"Ready - {self.current_path}"))

    def _on_save_error(self, path: str, err: str):
        QMessageBox.critical(self, "Save Failed", f"{path}\n\n{err}")
        self.log("ERROR", f"Save failed {path}: {err}")

    def _close_file(self):
        if not self.current_file:
            return
        if self.modified:
            if QMessageBox.question(
                self, "Close File", "This file has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        self._loading_file = True
        self.editor.clear()
        self.editor.document().setModified(False)
        self._loading_file = False
        self.editor.setReadOnly(True)
        self.save_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.find_btn.setEnabled(False)
        self.find_bar.hide_bar()
        self.file_info_lbl.setText("No file selected")
        self.current_file = None
        self.modified = False
        self.pos_lbl.setText("")
        self.lang_lbl.setText("")
        if self._highlighter is not None:
            self._highlighter.setDocument(None)
            self._highlighter = None

    # ---------- context menu / fs ops ----------
    def _context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        menu = QMenu(self)
        menu.addAction("New File", self._new_file)
        menu.addAction("New Folder", self._new_folder)
        menu.addAction("Refresh", lambda: self._list_dir(self.current_path))
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                menu.addSeparator()
                menu.addAction("Rename...", lambda: self._rename(data["path"]))
                menu.addAction("Delete", lambda: self._delete(data["path"], data["is_dir"]))
        menu.exec(self.file_list.viewport().mapToGlobal(pos))

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if not ok or not name.strip():
            return
        path = remote_join(self.current_path, name.strip())
        try:
            with self.session.get_sftp().open(path, "w") as f:
                f.write("")
            self._list_dir(self.current_path)
            self.log("INFO", f"Created file {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        try:
            self.session.get_sftp().mkdir(remote_join(self.current_path, name.strip()))
            self._list_dir(self.current_path)
            self.log("INFO", f"Created folder {name.strip()}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _rename(self, old_path: str):
        name, ok = QInputDialog.getText(self, "Rename", "New name:",
                                        text=os.path.basename(old_path))
        if not ok or not name.strip():
            return
        new_path = remote_join(remote_parent(old_path), name.strip())
        try:
            self.session.get_sftp().rename(old_path, new_path)
            if self.current_file == old_path:
                self.current_file = new_path
                self.file_info_lbl.setText(f"Editing: {new_path}")
            self._list_dir(self.current_path)
            self.log("INFO", f"Renamed {old_path} -> {new_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete(self, path: str, is_dir: bool):
        if QMessageBox.question(
            self, "Delete", f"Delete:\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.show_msg(f"Deleting {path}...")
        w = DeleteWorker(self.session, path, is_dir)
        w.done.connect(self._on_deleted)
        w.failed.connect(lambda p, e: (QMessageBox.critical(self, "Error", e),
                                       self.log("ERROR", f"Delete {p}: {e}")))
        self._track_worker(w)
        w.start()

    def _on_deleted(self, path: str):
        self.log("INFO", f"Deleted {path}")
        if self.current_file == path:
            self._loading_file = True
            self.editor.clear()
            self.editor.document().setModified(False)
            self._loading_file = False
            self.editor.setReadOnly(True)
            self.current_file = None
            self.modified = False
            self.save_btn.setEnabled(False)
            self.close_btn.setEnabled(False)
            self.find_btn.setEnabled(False)
            self.file_info_lbl.setText("No file selected")
        self._list_dir(self.current_path)

    # ---------- close ----------
    def closeEvent(self, event):
        if self.modified:
            if QMessageBox.question(
                self, "Exit", "There are unsaved changes. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        if self.terminal:
            self.terminal.stop()
        for w in list(self._workers):
            try:
                w.wait(800)
            except Exception:
                pass
        self.session.close()
        event.accept()


# ==============================================================================
# Theme
# ==============================================================================
DARK_THEME = """
    QMainWindow, QWidget {
        background:#0d1117; color:#e6edf3;
        font-family:'Segoe UI','Ubuntu','Helvetica Neue',sans-serif; font-size:12px;
    }
    QLineEdit, QPlainTextEdit, QListWidget, QComboBox {
        background:#161b22; color:#e6edf3;
        border:1px solid #30363d; border-radius:6px; padding:4px 8px;
        selection-background-color:#388bfd; selection-color:#ffffff;
    }
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border-color:#388bfd; }
    QPushButton {
        background:#21262d; color:#e6edf3; border:1px solid #30363d;
        border-radius:6px; padding:5px 12px; min-height:20px;
    }
    QPushButton:hover { background:#30363d; border-color:#8b949e; }
    QPushButton:pressed { background:#161b22; }
    QPushButton:disabled { color:#484f58; background:#0d1117; border-color:#21262d; }
    QPushButton:checked { background:#388bfd; border-color:#388bfd; }
    QToolButton {
        background:#21262d; color:#e6edf3; border:1px solid #30363d;
        border-radius:5px; padding:3px 6px;
    }
    QToolButton:hover { background:#30363d; }
    QToolButton:checked { background:#388bfd; }
    QCheckBox { color:#8b949e; }
    QLabel { color:#8b949e; }
    QListWidget::item:selected { background:#388bfd; color:#ffffff; border-radius:4px; }
    QListWidget::item:hover { background:#21262d; border-radius:4px; }
    QStatusBar { background:#161b22; color:#8b949e; border-top:1px solid #30363d; }
    QStatusBar QLabel { color:#8b949e; }
    QSplitter::handle { background:#21262d; }
    QSplitter::handle:horizontal { width:3px; }
    QSplitter::handle:vertical { height:3px; }
    QSplitter::handle:hover { background:#388bfd; }
    QTabWidget::pane { border:1px solid #30363d; border-radius:6px; }
    QTabBar::tab {
        background:#161b22; color:#8b949e; padding:5px 14px;
        border:1px solid #30363d; border-bottom:none;
        border-top-left-radius:6px; border-top-right-radius:6px;
    }
    QTabBar::tab:selected { background:#0d1117; color:#e6edf3; }
    QScrollBar:vertical { background:#0d1117; width:9px; border-radius:4px; }
    QScrollBar::handle:vertical { background:#30363d; border-radius:4px; min-height:20px; }
    QScrollBar::handle:vertical:hover { background:#484f58; }
    QScrollBar:horizontal { background:#0d1117; height:9px; border-radius:4px; }
    QScrollBar::handle:horizontal { background:#30363d; border-radius:4px; min-width:20px; }
    QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
    QDialog { background:#0d1117; }
    QComboBox QAbstractItemView {
        background:#161b22; color:#e6edf3; border:1px solid #30363d;
        selection-background-color:#388bfd;
    }
    QMenu { background:#161b22; color:#e6edf3; border:1px solid #30363d;
        border-radius:8px; padding:4px; }
    QMenu::item { padding:5px 20px; border-radius:4px; }
    QMenu::item:selected { background:#388bfd; color:#ffffff; }
    QMenu::separator { background:#30363d; height:1px; margin:3px 8px; }
    QToolTip { background:#161b22; color:#e6edf3; border:1px solid #30363d; padding:3px; }
"""


def main():
    if not sys.platform.startswith("win"):
        os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.wayland*=false")
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(build_app_icon())

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted or login.session is None:
        sys.exit(0)

    win = MainWindow(login.session)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()