"""
AunSSH Mini - Lightweight SSH/SFTP file manager, editor and terminal IDE.
A fast, PuTTY-light alternative for editing files on remote servers without
installing heavy server-side extensions (unlike VSCode Remote).

Created by Aunhelloworld.

Requirements:
    pip install PyQt6 paramiko

Run:
    python main.py
"""

import os
import re
import sys
import json
import base64
import codecs
import select
import socket
import datetime
import stat as _stat
from pathlib import Path
from typing import Optional, List, Dict

import paramiko

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QRegularExpression, QSize, QTimer, QUrl, QEvent,
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon, QPixmap,
    QPainter, QKeySequence, QShortcut, QTextCursor, QLinearGradient, QBrush,
    QTextDocument, QFontMetricsF, QAction,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QPlainTextEdit,
    QSplitter, QLabel, QFileDialog, QMessageBox, QStatusBar, QInputDialog,
    QDialog, QMenu, QTabWidget, QToolButton, QComboBox, QCheckBox, QFrame,
    QSizePolicy,
)

APP_VERSION = "1.0.5"
APP_NAME = f"AunSSH Mini {APP_VERSION}"
CONFIG_FILE = Path.home() / ".aunssh_mini.json"
MONO = "JetBrains Mono, Cascadia Code, Fira Code, Consolas, Menlo, Monospace"
NEWS_URL = "https://www.aunssh.com/news.json"


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
            if "profiles" not in data:
                data["profiles"] = []
            return data
        except Exception:
            pass
    return {"profiles": [], "last": ""}


def save_config(data: dict):
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), "utf-8")
    except Exception:
        pass


_ICON_B64 = """
AAABAAEA3fIAAAEAIABIXgMAFgAAACgAAADdAAAA5AEAAAEAIAAAAAAAqEMDAMMOAADDDgAAAAAAAAAAAAD//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+7t7f/t7Oz/7u7u///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Pz/9vb2//Py8v/29fT/9fX0//b19f/4+Pf/9vb1//z8/P/8/Pz//v7+//z8/P/5+fn/+fn4//j4+P/7+/v/+vr6//v7+//9/f3/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////1tXV/8zLy//BwMH///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/6+vr/9PT0/9ra2v/Y19f/z87P/9DQ0f/V1NX/3t3e/9TU1f/Qz9D/4N/f/+jn5//u7u3/3t3d/9TT1P/Pz9D/09PT/9XU1P/g39//4+Li/+zr6//4+Pf/+/r6//39/f/+/v7//v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/f/q6ef/+vn5///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////R0ND/urm5/7e2t//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f/39/f/+Hh4f/e3t3/2tnZ/93d3f/d3d3/39/f/+Pj4//u7u7/1tXV/9XV1f/W1tb/2dnZ/9zb2//a2dn/2NfX/93c3P/f39//3t7e/9fW1v/X1tb/0dDQ/9TS0v/c29r/3t3d/93c3P/X1tb/1tXU/9vb2v/Y2Nf/4eHg/9vb2v/i4uH/2dnX/9zb2v/Z2Nf/3dzb/9jX1v/a2dn/2NfY/9zb3P/b29v/4eDg/87Nz//c29z/1dTW/9rZ2v/e3t//5+fn/9va3P/s7O3//v7+/////////////v7+//v7+//6+fr/9PP0//X19f/i4eH/6Ojo/9va2//X19f/1tXV/9va2//e3t7/1tXV/9fW1v/i4eH/2djY/9DPz//Y19f/3tzc//n4+P/l5eX/3Nzb/9ra2f/i4uL/6unp/+jo6P/m5ub/4uLh/+Xl5f/t7e3/7Ozr/+jo6P/z8/P/+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/7a1tP/m5eP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9XV1f+2tbX/srGy//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////X09P/e3Nz/4N/e/9zc2//Z2Nj/29ra/9va2v/c29z/397f/+fm5v/S0dH/1NPT/9PS0//W1db/2djY/9fX1//T0tP/2djZ/9va2v/b2tr/19bW/9jX1//W1dX/2tjX/+Ti4P/l5OL/5eTj/+Li4f/h4eH/5ubl/+Tj4//s7Oz/5+fn/+zs7P/n5+f/6unp/+np6f/r6+v/6Ojo/+vq6v/s7Oz/8fHx/+/u7v/08/P/6ejo/+zr6//o6Oj/6enp/+3t7f/v7+//8fHx//b29v/8/Pz/+vr6//r6+v/4+Pj/9PPz//Py8v/y8fH/8fDw/+fm5v/t7Oz/5uXl/+Pi4v/i4eH/5+bn/+fn5v/i4uH/5OPj/+rp6P/m5eX/5eTk/+bl5P/r6un/8/Lx/+fm5v/k4+L/4uHh/+Pj4v/o5+b/5+bk/+Xk4//j4eD/5OPi/+no5//o5+b/5OPj/+/t7P/39/X//fz8//38/P/+/v7//v7+///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////09PT/paSl/9DQ0P//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////0dHR/7Sysv+wsLD////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f/1NPT/9DPz//Z2dn/39/f/8bFxf/Mysr/vbu6/8XDwf+9u7r/v768/8bEwv/HxcL/wr+8/8bEwf/Ewr//xMK//8PBv/+/vbz/tbOz/7Sys/+1s7L/rq2s/7W0tP+2tLT/p6Wk/6+urf+uraz/s7Gv/7Gvrv+0srD/raqp/6+tq/+1s7L/trS0/7Wzs//ExMP/t7W2/7+9vf+6uLn/vr29/7y6uv+9vLz/vry8/7a2tf+9vLz/sLCw/7S0tP+0s7T/uLi4/7a2tv+7u7v/vb29/76+vv/AwMD/wcHC/76+vv++vr7/vLu8/7Oysv+trKz/sK6v/6yqq/+4t7b/x8XE/7a1tf+1s7P/s7Gx/767uv+xr6//trW1/7Kxsf/CwMD/ube3/6inp/+1s7T/sa+v/7m3tv+4trb/t7W1/768u//Lycj/v728/8TDwv/HxsX/u7m5/727uv++vbz/vr28/8LAv/++vLr/y8nI/8LAv/+6uLf/vru6/8TCwv+5t7j/urm6/7u5uv+1tLX/srGy/7Kxsv+0s7T/vby8/8LCwv/Hxsb/w8PD/8/Pz//My8v/zMzM/8jHx//Pz8//19bW/+Tk5P////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////T09P+cm53/zczN///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////U09P/s7Ky/7Oys//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/7Ovr/+Dg3//m5eT/4+Hh/9rY1v/m5OP/7+/v/+Tj4v/V09P/29rY/9rY1//Z19T/0c/N/9HPzf/FxMT/xcTD/8TCwf/JyMf/w8HB/8jHx//Hxsb/x8bG/8jHx//Hxsb/xsXF/8PDwv/CwcL/v76+/7+/v/++vb3/vby9/7i3t/+3trb/uLe4/7Kxsv+ura7/rayt/6qpqf+mpaX/oKCh/5+en/+dnJz/np2f/52cnf+ZmJj/mpmZ/5+dnv+dm5v/nJub/56dnf+cm5v/mpiZ/5qYmf+bmZn/mpiZ/5yamv+enJz/o6Gh/6Ohof+dnJz/mJaX/5yam/+enZ7/npyd/5+env+gn5//o6Ki/6WkpP+rqqr/pqWl/6Gfn/+lpKT/rKur/6elpv+mpaX/rKur/6Wjov+op6f/pKOj/6WkpP+lpKT/p6am/6Gfn/+hoJ//oqGg/6empf+pqKf/pKKi/6mnpv+rqqr/qqmp/6uqqv+traz/rays/66trf+zsrL/ubm4/7y7uv+8urn/vbu6/8rHxv/Qzs3/zs3L/9PRz//b2Nb/yMbF/9PR0f/Jx8j/zczM/8zLzP/S0dH/09LT/9bV1v/h3+D/4N/f/93c3P/e3d7/3Nvc/+bl5v/u7e7/6ejo/+rq6f/x8PD/7u7u//Ly8v/4+Pj/////////////////////////////////////////////////////////////////////////////////////////////////////////////////9PT0/6Oiov/JyMf//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9XV1f+ysrP/s7Oz///////////////////////////////////////////////////////////////////////////////////////////////////////8/Pz//Pz8//z8/P/6+vr/+vr5//r6+f/49/f/+Pj3//Py8v/f3t3/29nY/9bV1P/Ozcz/3dza/+bl4//y8fD/0M7N/8PDw//Ew8P/w8LC/8jHxv/BwMD/vry7/7m4t/+4t7f/uLe3/8C/v//NzMv/zs7M/8zLyv/Kycj/yMfH/8bFxf/GxMT/x8XE/8jHxv/DwsH/wcC//768vP++vL3/vLq7/7q5uv+1tLX/urm6/7m4uf+4trf/u7m5/7m3t/+4trb/tLGy/7q5uv+7urv/trS1/7Kwsf+zsbL/sK6v/66srv+xr7D/sK6v/6upqv+qqKn/p6Wm/6Ohov+opqf/r62u/6yqq/+op6j/sK6v/7Curv+ysLD/ube4/7WztP+8urr/vru7/727u/+8urr/vry7/8PBwf/Bvr//wL6+/7q4t/+xrq//trW1/7Kxsf+zsbL/srCx/7W0tf+1tLT/trW1/7e2t/+zsrP/tLOz/7a1tf+1s7T/sa+w/7Oxsf+0srP/tbO0/7Oxsf+zsrL/s7Gx/7Curv+wrq7/rKur/7GvsP+0s7P/srGy/7m4uP/Av77/zczM/9DPz//Ny8r/zcrJ/9TT0f/GxMP/ycfH/8nIx//Jycn/ysnK/83Mzf/V1NX/0dDR/93c3f/i4eH/3Nvc/9nY2f/Y19j/2djZ/9rZ2v/V1NX/1dTV/+Pi4f/c29v/4+Li/+3s7P/+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////y8vL/lJOU/8fGxv//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////0dHR/7CvsP+xsLH//////////////////////////////////////////////////////////////////////////////////////////////////f39/+Pi4f/c29n/09LQ/8vKyf/Lysn/1NPS/8XDw//DwsH/x8bF/728u//FxMP/ysnI/8jGxf/Pzs3/zszL/+fl5P/IxsX/zs7N/8nIx//Ew8L/0dDP/8/Ozv/Kycj/w8LB/6empf+Xl5f/h4aG/359ff9wb2//b25u/2lnaP9fXV7/ZGJk/2NhYv9eXF7/W1la/11bXP9cWlz/WVdZ/1pXWf9XVVj/V1ZZ/1dVWP9cWl3/XVte/11bXf9dW1z/XFpb/11bXf9hX2H/XVtc/1xaXP9dW17/YF5h/2NhY/9jYmP/ZGJj/2RiZP9iYGP/XFpd/2FfYv9jYWT/Xlxf/11bXf9jYWP/YmFk/2BeYf9raGv/aWhp/2BeYP9lY2T/ZmNl/2NhY/9fXF7/YWBh/2JhYv9fXmD/YV9i/19dXv9hX2D/YmBh/2BeX/9kY2T/Yl9g/2JgYv9dXF3/YV9h/2JfYf9jYWP/aWZo/2hmaP9gXmD/YmBj/2BeYP9gXmH/XFpa/2FfYP9fXV7/W1lb/19dXv9kYmP/X11e/2RiZf9pZ2n/ZmRm/2VjZv9kYmT/YmBi/2NiZP9oZmj/a2pr/3Jxc/99e3z/joyN/5qYmP+pp6f/srGx/7a0tP+0s7T/tbS0/7q5uv+3trf/urq6/7m4uP+9vLz/uLe3/8LAwP+2tbX/vLu6/7++vf++vLz/19XU/93c2//8+/v/+/r6//7+/v/+/v3//f39//79/f/+/v7//v7+//////////////////////////////////////////////////////////////////////////////////Hx8P+Ylpb/zs3N///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////X19j/sK+w/6ysrP///////////////////////////////////////////////////////////////////////////////////////v7+//7+/v/+/v7/+/r5//r5+P/6+vj/+/r6//v6+v/l49//29fT/8zJxv/PzMn/xMG//8zJxv+4trT/v728/7Sysv+6uLb/tbOy/7m3tf+rqan/q6mp/5WUlf+amZj/lpWV/4iGhv84Nzj/ISAj/xsaHf8YFhn/FRMV/xMRFP8SEBP/FBMV/xUUFv8TERT/FBIV/xQSFf8TEhP/ExIT/xMRFP8TEhT/ExET/xMRE/8TEhT/FRMV/xUTFf8UExX/FRMW/xMRE/8SERP/ExEU/xMSFP8UExX/FhQW/xUUFv8VExf/FRMV/xYUF/8WFRf/FhQW/xYUF/8VFBb/FRMV/xMRE/8UEhP/FRMV/xYUFf8WFBb/FBIU/xUTFf8XFRf/FRMV/xUTFf8WFBf/FBMV/xQTFv8TEhT/FBIU/xUTFv8VFBX/FBIV/xQTFf8VExX/FhQW/xQSFf8VFBb/ExIU/xMSFP8TERT/ExET/xMSFP8UEhX/FBMV/xUTFv8VFBf/ExIU/xMSFP8UExb/FBIV/xMSFP8TEhT/FBIW/xQSFf8UEhX/FBIV/xMRFf8UEhX/EhEU/xMRFP8SERT/ExEU/xMRE/8TERT/ExIU/xcWGf8eHCD/ISAk/zUzN/9bWVv/enh6/4F/gP+OjY3/lJKT/5eWl/+fnZ7/n52d/6GfoP+gn5//pKOj/6alpf+qqKj/oJ+e/5mYmf+YmJj/l5aX/5+en/+mpaX/o6Ok/6moqf/CwcD/zczL/9PR0P/U0tH/8/Py////////////////////////////////////////////////////////////////////////////8PDv/5aUlf/Kycn//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9XU1P+xsLD/r6+w////////////////////////////////////////////////////////////+vr6/9/e3f/GxcT/z83M/8G/vv/T0c//4d/d//z7+//29fP/8vDu/8PBv/+8urr/wcDA/8C/vv/Av7//wb+//7+9vf++vb3/vr29/8C/v/++vLz/v729/7y7u//Av8D/xcTF/8DAwP+9vLz/vby9/7+9vf+6ubj/QD9A/xYVGP8hICP/Xlxf/359f/+EgoP/oaCj/5iXmv+Yl5j/oJ+h/5aUlf+npqj/nZyd/6SipP+Zl5n/pqWn/56dnv+hn6H/p6ao/6Sjpv+hoKL/qaiq/6Ggov+ZmJv/paSn/5ybnv+hoKP/lZSW/6Ggov+fnqH/jo2Q/6Wlp/+ZmJr/m5ud/5aUl/+gn6L/lpWX/5WUl/+SkZP/npye/56doP+TkZT/oJ+i/4SDhv+ko6b/jIuN/5qZmv+cm57/kpCR/5aVlv+WlZf/g4GE/5iXmf+KiIr/oaCj/4KBgv+WlZf/iIaI/5eVmP9+fX//kpGU/4mIi/+Mi47/lJOW/4+NkP+RkJT/h4WI/5iXmv+Eg4X/kZCT/4mHiv+Hhon/h4aI/4+Nj/+EgoT/l5aY/4aEhP+bmZv/hIGC/5mYmf96eHn/jYqM/4F/gP9+fX//l5aY/4F/gv91cnT/i4mM/05MTv9OTE3/QT9C/xwbH/8XFhr/GRgd/x8eIP8/PD3/WVdY/2VkZv9ubG7/d3V5/399gP+Ihof/j42N/5OQkP+WlZT/n52d/6WkpP+0s7T/xMLB/87Nzf/W1dT/1tXU/9fV1P/b2tn/4eDf/+Pi4f/o5+b/5+bl/+Pj4f/k4+H/5+fm/+7t7f/x8PD/8vLx//b29f/5+fn////+///////////////////////////////////////y8fH/oJ+f/83MzP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////09PT/6+urv+wsLH/////////////////////////////////9/b2/+Pj4//l5eX/4+Lj/+Pj4//s6+v/3d3c/9zc2//S0dL/1dTU/9zb2//g3t7/397d/93d3P/T0tH/1NPS/9TT0v/Ozc3/ysnJ/8rJyv/Kycn/ysnI/8nIyP/IyMf/y8rK/8nIyP/Lysr/ycjI/8rKyv/BwcH/w8PD/8C/wP++vb3/tbSz/5WUlf8dHB//R0ZK/zQyN/92dHb/YF5h/1RSU/92dHX/aWdq/1RSU/9mZGX/VlNU/3Nxcf9fXF3/fXt9/0pISP+OjIz/Uk9R/3p4ef9CPz//h4WG/01LTf94dnb/XVpb/2BfX/9wbm//SkhJ/4F/f/9IR0n/b21u/2ViZP9QTlD/dHJ0/0ZERv+Bf4H/Q0BC/4SCg/9QTlD/cW9w/1xaW/9VVFT/amlp/0pISv90cnT/NzU2/3x5e/9lY2X/VlRW/4B+gP9DQUL/bGpr/05LTf9lYmL/TUpL/1FPT/9vbW7/Ojc3/3h2d/9HRUb/e3l6/zk3OP99e33/Pz0//3BucP9RT1L/X15f/0xKS/9ZWFj/bGpr/0pISf9ta2z/REJD/4WEhv9MSUn/VlNT/1pYWf9ycXL/R0RE/3Bub/9CQED/Z2Zm/zUzNP9hX2D/REJD/2poaf9KR0f/TEpK/2hmZ/9OS0z/PTw9/zc1Nv85Nzj/LSwv/xkYHP8aGR3/Hx4h/zg2Of9GQ0X/VlNW/2NhY/9paGv/cG5w/3Nxc/98en3/fHp8/3l4ef+Eg4T/i4qL/5SSk/+enZ3/pqWl/6qqqf+wr7D/trW1/7W0tP+2tbX/uLe3/7y7u/+6urn/u7u6/7y7u/+/vr//wcDA/8rKyf/Ew8P/zs3M/9fV1P/l5OT/5+fn/+np6f/p6en//Pz8//////////////////Hx8f+dnJz/1NPT///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////b29v/pqSk/6ioqf/////////////////////////////////19fT/4+Hg/+Pi4v/g39//4uHh/+7t7f/d3Nz/3dvb/9TT0v/X1tX/393c/+Hg3//f3t3/3Nvb/9TT0v/Z2Nf/29nZ/9LR0f/My8v/ysnJ/8nIx//JyMf/xsTE/8jHxv/GxcT/yMfH/87Nzf/Kycr/ysnJ/8LCwf/CwsL/ubi4/7e2tv+wr6//iomK/xYVGv9bWl3/NzY5/4aFiP9kYmX/ZmRn/46MkP9xb3P/a2ls/3NxdP92dHf/dHJ0/3Fvcf97en3/ZmRm/5CQkv9lY2b/iYeJ/1pYWv+Xlpn/Wlld/5STlf9jYWT/gYCC/39+gf9kY2f/jo2P/1VUV/+GhIb/dXN1/11bXv+JiIv/V1VY/4+Nj/9UUlT/lpSX/2JgY/+Bf4H/bmxv/29tcP+Jh4n/XVxf/5GPkv9RT1P/kI6S/3x7f/9iYGP/fHp+/1RTVv+AfoH/Y2Jk/4B+gP9YV1n/a2lr/3h1d/9UUVL/g4KE/1ZVWP+DgYT/T01Q/4WDh/9UU1X/h4aJ/09OUP97eX3/Xlxf/2ZlZ/9XVVj/c3F0/1hWWP9ZWFr/YmBi/3NydP9RUFH/ZGNl/3BucP9fXWD/ZGJk/1JQUf93dXb/TkxO/3Z0dv9UUVP/b2xt/1pYWf9dW13/b21v/0pISv9EQ0X/UlFU/zo5O/82NDj/HRwh/xoYHf8gHyP/LSsv/zk2Ov88Oz3/Q0FE/0E/QP9OTU//V1VX/1xaXf9iYWP/ZWNm/21sbf+DgoP/jYyM/5KSkv+ioaH/qaio/7Kysv+3trb/uLi3/7q5uf+9vLz/xcTE/8jIx//Ozc3/xsXE/83MzP/JyMj/zc3M/8rJyP/JyMf/ycjH/9DOzf/R0M//0tDQ/9nY1//5+Pf/////////////////8vLy/5mXl//DwsL//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9jY2P+qqKn/paSm////////////////////////////////////////////////////////////+fn5/9jW1//Lysr/zMzM/8zMzP/T0tL/3dzb/7i2tv/Nysj/0s/N/8G/vv+6uLj/s7Kw/6elpP+joqL/pqSk/7Cvr/+qqaj/qKen/6empv+qqqr/rays/7Kxsf+ysbH/srGy/7Oys/+xsLH/r66u/6inp/+GhYb/GBcc/2BfYv8rKi//MS8z/x0bH/8kIif/Liww/zIxNf8uLDH/LSww/zQzN/81Mzj/NjU6/zw7QP87OT3/PDo//zc2O/8+PED/Pjw//z89Qf89Oz3/RENG/0RDRf9FREb/RURG/0dFSP9GRUj/Q0JG/0VDR/9GREj/QD5C/0VESP9BQET/RENI/z49Qv8/PkL/Pz1B/z07Pv89Oz7/Pjw//zU0N/8rKi3/OTg8/zMyNv80Mzf/MTA1/zAuM/81NDn/Ly0y/zEvM/8xLzP/NjU5/y8tMf8yMTb/NjQ4/y8tMf8tKzD/JyUq/yUjJ/8jIib/JiUo/ygnK/8mJCn/IiAj/yopLf8nJSn/JCIm/yIgI/8mJCj/JCIm/yQjJv8kIyf/JiUp/yEgJP8kIib/IyEl/yQjKP8jIib/ISAk/ycmK/8iISb/JCMn/x8dIv8gHyP/HRsf/xsaHf8bGRz/FhUX/xUTFv8fHiD/IiAi/z07QP8ZGBz/GBcc/xoYHP8bGR3/IR8i/yQjJv8mJCb/IyEk/ygmKP8rKSv/MjAx/zIwMP8/PDz/R0RF/01LS/9cWVv/b21u/4SDhP+JiIj/j42O/5COjv+Xlpb/n56d/6mnp/+qqan/q6qq/7Cvr/+3t7b/v769/8rJx//U09H/8O/u//z8+//+/v7//v7+//7+/v/+/v7//v7+//7+/f/+/v7////////////y8vL/mJeX/8HAwP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////2tra/62srP+oqKn///////////////////////////////////////////////////////r6+v/4+Pf/9fX0//Lx8P/k4uL/29ra/9zb2v/c29r/y8rI/8nHxf+1s7L/sa+t/6mnpP+koqH/oqCe/5uZmP+amJj/nJqZ/5+dnP+Zl5b/k5GP/5WTk/+TkZH/jo2N/4yLi/+KiIj/g4KD/4B/gP99fH3/bm1u/11cX/8dHCH/JiUp/5uanv/V1df/6enr/+/v8P/u7u//7+/w/+7u8P/u7vD/7u7v/+/u8P/u7u//7u3v/+7t7//v7/D/7+/w/+/v8P/u7e//7u7v/+7u7//u7e7/7u7v/+/u7//u7vD/7u3v/+/v8P/v7/D/7+/w/+/v7//v7u//7u7v//Dv8P/w8PD/8PDx//Hw8f/w7/D/8fDx//Hw8f/x8PD/8PDx//Lx8v/y8fL/8fHx//Hx8f/w8PH/8PDx//Dw8f/v7/D/8PDx//Dw8f/x8fL/8PDy//Hx8v/w8PL/8O/x/+/v8f/w7/H/7+/w//Dv8P/v7/D/7+/w/+/v8f/v7/H/8O/x/+/u8P/u7u//7u7w/+7u8P/t7e//7e3v/+zs7v/u7u//7e3u/+vr7f/r6+3/6+vt/+rq7P/p6ev/6enr/+np6//o6Or/6enr/+rq7P/n5+r/5eXn/+Pj5f/k5Ob/19fa/7m4vP9zcnb/SklN/xgWG/8aGBv/JCMn/zQyN/85OD3/SklO/1taXv9aWFz/XFtf/2Vkaf9oZ2z/amht/29tcP93dnf/dnV2/3l4ef95eHj/gH5//4F/gP9+fHz/fn19/399ff+CgYL/ioiI/46NjP+Rj4//kY+P/5SSk/+cm5v/m5mZ/6OhoP+qqKj/q6io/7SxsP+xr67/wsG//8bFw/+zsrL/xMLD/+3s6//+/v7//////+/v7/+WlJX/v76+///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Z2dn/qKan/6enqP/////////////////////////////////////////////////+/v7/1NLS/8vKyf/GxMP/w8HA/8fEw/+8urn/v729/7m3t/+6ubn/wL++/8G/vf+2tLP/tLOx/7CurP+wrq3/qain/6qpqP+fnp7/mpmZ/5STk/+Lion/j46O/5WUlf+hoKH/pKOj/5+env+dnJz/kpGR/42LjP+CgYP/eHZ5/z49Qf8aGRz/Z2Zo/66srv+SkZT/i4qM/5iXmv+qqar/oaCh/6Sjpf+lo6X/pKOk/6CfoP+koqP/qaeo/6upq/+mpKb/pqSm/6elp/+lpKX/q6mr/6qpqv+pp6j/rKqs/6alpf+ioKH/pqSl/66srf+rqar/rKqr/6yqrf+npqj/rKut/6urrP+vra//pKKj/5+en/+lpKX/pqSl/6akpv+lpKX/pKKk/62rrv+ioaP/paSl/6alpv+npqf/ra2u/6elpv+hoKL/mpmb/52cnv+cnJ7/nZye/5qZm/+cm53/oJ6f/6elp/+wr7D/rq2v/6upq/+wrrD/n56g/56dn/+npqj/trW2/6Wkpv+joaP/paOl/6Kgof+ioKL/n52f/56dnv+fnqD/m5mb/56cn/+bmp3/m5qd/5WUlv+SkZT/lZSW/4yLjf+Qj5D/i4mL/4iHif+Bf4H/hIKE/3Vzc/94dXb/gX5//11aXv8jIiX/HBse/ywqLv9KSU3/TUxR/1BPU/9PTlT/U1JW/1pZXf9hX2P/XFpd/19dYf9lY2f/bm1u/3h3eP+DgoP/iomJ/4iHiP+CgIH/jIuL/4qJif+JiIj/i4qK/46Mjf+OjY3/kY+P/5eVlf+Zl5f/mpiX/6elpP+opqT/sa6t/7azsv+/vLv/0c/M/9TRz//c2tj/8/Hv//39/P/9/fz//f39//7+/v//////8vLy/5GQkP+zsrP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9nZ2f+tq6z/oJ+h/////////////////////////////////////////////////////////v7//v7+//Lx8P/p5+b/7u3s/+Ph4v/X19f/4N/f/+Tj4v/W1dT/7u3s//Hw7//z8/L/5OPj/+7u7f/o5+f/3t3c/9va2f/U09P/ycjI/9LR0f/JyMj/u7q5/6+trP+wrqv/rKmm/62rqv+enJv/m5mY/5eUlP+Sj5D/mpmZ/2ZkZP8gHyH/LCsv/3x7fv+oqKr/lZSY/52cnv+ko6T/paSl/6uqqv+6uLn/tbS1/7Cvsf+vrq//r66w/7Gwsf+ura7/r66u/7W0tf+ura3/rKqr/6+urv+vrq7/trS0/7q4uf+2tbf/u7q7/6yrq/+tq6z/rqyu/6uqq/+sq63/tLO1/62srf+sq63/rKus/62srf+xr7H/srKz/66trv+pqKn/sK+w/6ioqf+urKz/rayt/6qpqf+vrq//tbO1/6yrq/+ysbH/rKqs/7CvsP+5uLr/r62v/6akpv+opqj/oqCj/6SipP+npqj/p6am/6akp/+joaT/qaiq/6SjpP+lo6X/oJ6h/6Gfof+hn6L/m5mc/5uZm/+joaT/nJud/5eWmP+Xlpj/kpCT/46NkP+Ni47/jo2Q/4aFh/+DgYP/gX+C/3x7ff96eXr/enl6/3h2d/9jYWP/eHd7/29tb/87OTv/GBca/z8+Qf9vbXD/goCC/4SChP+GhIf/joyO/5aVl/+Yl5j/mJeY/52cnv+gn6D/qqqq/7Kxsf+3t7f/ubi4/7u7u//CwcH/w8LD/8XEw//JyMj/zczM/83NzP/R0ND/09PS/9bW1v/U09P/1dTU/9jX1v/Y19f/2tnZ/93b2//g39//3t3c/+Df3v/n5uT/5+bl/+zr6v/5+Pf//f38//7+/v/////////////////w8PD/kpGS/7W0tP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////2tra/6upqv+dnZ7//////////////////////////////////////////////////////////////////Pz7//j4+P/5+Pj/9PTz//Ly8v/08/P/7+/u/+vr6//x8fD/7Ozr/+3t7P/m5eX/7Ovq/+7s6//s6+r/6unn/+jn5v/m5eT/6Ofm/97d3P/i4eD/ysnJ/8fGxv/Ix8f/xsXF/8LBwP/DwsL/wcDB/727vP+5uLj/trW1/9DP0P9tbG3/HBsd/y4sL/+WlZf/xsXH/7m3uf/Qz9H/0M/Q/9bV1v/c29v/397g/+Df3//i4eL/4+Pj/+Lh4f/j4eL/4+Li/+Pi4v/i4uL/4+Lj/+Lh4v/j4uP/4uHi/+Hg4f/h4OD/4ODg/+Hg4P/h4OH/4ODh/+Hg4f/j4uP/4eDh/+Dg4f/i4eH/4uHi/+Hg4f/h4OH/4eDh/+Dg4P/i4eH/4N/f/+Df4P/h4OH/4N/g/+Lh4f/k4+P/4eDg/+Li4v/h4eH/4uHi/+Xl5f/j4uP/4uLi/+Dg4f/h4OH/4eDh/97d3v/h4OD/4N/g/+Df4P/d3N3/3d3e/93c3f/c29z/2NfY/9DP0P/OzM3/zszN/83Lzf/BwMH/wL7A/8PBw//Hxsf/wsDC/7i3uP+wsLH/srGy/7Gvsf+sqqr/r66v/6akpP+joqL/iYaH/6akpf9LSkz/FRMW/x8eIv9sa2//c3J0/3x7fv+DgoT/jIuM/5GPkf+Uk5T/kpGS/5OSk/+Lior/mJeX/6SjpP+hoKH/oqGh/6Wkpf+ko6T/paWl/6alpf+npqf/qqmp/6mpqf+npqb/q6qq/6uqqv+qqan/srGx/7GvsP+xsLD/s7Ky/7e2tv+8u7v/srGx/769vf/CwcH/w8LC/7u6uf++vLv/xcPB/8bFw//IxsT/3t3c//////////////////Dv7/+Qjo//ubm5///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Z2Nj/o6Gj/6Cfof////////////////////////////////////////////////////////////////////////////////////////////Tz8//s6ur/9fT0/9jX1//Av8D/uLa4/7u5u//Bv8L/ysjJ/8vJyf/Avr7/wcC+/9TS0P/HxML/wL27/8XDwf+9u7r/tLOy/7GwsP+0s7P/s7Kx/6empv+lpKT/paSk/56dnf+dnJz/oqGh/7u5uP+9u7v/U1NU/xgXGv9JSEr/hoSH/4eGh/+Yl5j/n52f/6Wkpf/Ly8z/qaiq/5STlP+VlJb/lpWW/52bnf+UkpT/sK+x/7Gvsf+0s7T/qaip/6Cenv+ko6T/o6Kk/6akpv+joqT/n56f/5iXmf+bmZz/mJeZ/5KSlP+Qj5L/kpGT/5WUl/+VlJj/k5GU/5SUlv+Rj5L/lZOW/42Mjv+Qj5L/jYyN/5COkP+RkJL/kZCS/4+OkP+Pjo//kI+R/4mIiv+NjI7/j46Q/4eGh/+MjI7/jYuO/42Ljf+Hhoj/iomM/42Mjf+SkZL/ioiK/42Mjf+Mi47/hoWG/4qIif+Liov/jIqL/42Mjf+NjI3/jo2O/5SSlf+Mioz/kI+R/46Mj/+OjI7/iIaH/5KQkv+Vk5X/mJaX/5GPkP98enz/cnBz/2tpbP9KSUz/FxYZ/x8dIP9EQ0T/jIyN/5uanP+opqf/rKqq/66trf+wr67/sa+v/7Gvr/+vrq3/sa+v/5yamf+qp6X/rayr/62rq/+op6f/r62t/6+urv+0s7P/wL+//769vf+/vr7/yMfI/8jIyP/Gxcb/wcHA/9DQ0P/V1dT/z87O/9nY2P/c29r/2tnY/+Tj4v/m5OP/1tbV/9nY1//b2tn/3t3c//j39v//////////////////////////////////////7+/v/42Li/+3trf//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9nY2P+ioaL/o6Ok///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7//v79//39/f/5+fn/0dDQ/8PCw//Av77/zMrJ/8jGxf+8urr/u7q5/8C+vf+9u7v/yMfH/9XU0/+8u7v/wcDA/7u6uv+3trb/vLu7/7e3t/+8urv/t7a2/8TDwv/Y1tX/q6qr/0A/Qf8eHSD/WFda/3Nydf90c3b/g4KF/5COkP+VlJb/n56h/5qYmf+cm53/mpmb/5mXmf+ioaL/np2e/5ybnP+gn6H/mpma/5eVl/+Zl5n/l5aX/5mYmv+cm53/lpWX/5ybnf+bmZz/mZia/5mYmv+hoKL/m5qc/5qYmv+fnZ//pqWn/6OhpP+dm57/m5mb/5aVl/+UkpT/npye/5qYmf+enJ7/mpia/6CeoP+cm5z/lJKU/5eVl/+dm53/kpCS/5COkP+Vk5X/jIqM/42Ljv+OjI7/kI+R/46NkP+OjY//iIeJ/42Ljf+HhYf/jIuM/4iHh/+Qj5D/jIuN/4SDg/+Ihoj/iYiL/4WDhf+GhYf/g4KF/4SChf96eXv/f36A/3x7fP9nZWb/ZmRm/1hWWP8yMDP/LSst/xkXGv9aWVr/vr2+/97d3f/S0tH/0tHR/9fX1//Y2Nj/1tXV/9fW1f/U09P/09PS/9bV1f/W1dT/tLKy/5aVlv/X1tX/3dzc/93c3P/c29v/1tXV/9rZ2f/b29v/29ra/9fW1v/Z2dj/2djY/9bV1f/Y19f/19bW/9rZ2f/X19f/3Nzc/9PS0f/R0ND/3Nva/93c2//r6+n/7ezr/+3r6v/19PP/+/v6///////////////////////////////////////u7u7/kI6P/7e2t///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////zczM/6moqv+enp/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3//Pz8//z8/P/7+/v/+/v7//n5+P/39vb/9vb1//Py8v/j4uL/19XU/9LQz//Ix8b/ycjI/83My//EwsL/vLq6/7KwsP+vrq3/wb++/8bDw//n5ub/7u3t/5iYmP8uLS//JyYo/2RiZf9zcnX/Y2Jl/3Z1eP+Fg4b/iIeI/4KBgv+Mi4z/j46O/5KQkv+PjY//joyO/5OSk/+Qjo//kY+Q/5KRkv+RkJL/i4mL/4aEh/+Jhoj/lJKV/46Mjf+Ni47/iomK/4qIiv+Ihoj/h4aH/5GPkf+PjY//jYuN/5WUlf+Vk5T/j42O/4uJiv+KiIj/jIqK/4aEhP+Miov/kY+Q/46Mjf+Oi4z/jIqM/4yKjP+Hhof/h4SH/4eFiP+CgYL/g4GD/4SChP+Bf4D/f35//358ff+CgYL/gX+A/3t6ev98env/gH5//4F/gP+CgIH/fXt8/3t6e/9/fX7/enh5/3l3ef95d3j/enh5/3h2d/9ta2z/Xltd/1VTVP9HRUb/MTAx/xcVF/9OTU3/s7Kz/8TDw/+xsLD/rqys/7Cvr/+xsLD/trW1/7a1tf+5uLj/wcDA/7++vv++vb3/v76+/8LBwP+lpKP/hoSG/7y6uP/GxcT/yMbG/8jHxv/Kycj/0M/O/9DOzf/S0M//1dPS/9bV1P/V09L/09LR/9fX1v/X19b/2tnZ/9nY2P/d3Nz/2djY/9rZ2P/g4N//5uTj//39/P/+/v7//////////////////////////////////////////////////////+/u7v+Pjo//srGx//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+1tLX/rq2v/7W0tf////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////r5+f/39/f/+Pj3//T09P/19PT/9fX1//Hx8f/m5uX/4uHh/+Df3v/j4uL/5OLi/+vq6//u7e3/8fDw/+Xl5P9/fn7/HBsd/yopLP9nZWn/bWtu/317fv+CgYL/iIaI/4KAgf+EgoP/iIaJ/4OBhP+DgYT/iIeJ/4F/gf+FhIX/iYiK/3p5e/95eHr/fn1//316ff99e33/fnx+/3l4ev97eXv/enl7/4B+gf9+fYD/e3p8/359f/+DgoT/fn1//318fv98enz/fnx//317ff98e33/f36A/317fv+CgYP/fXt9/3x5e/94dnj/gH+B/4B+gP98en7/eXd6/3t5e/+Afn//f31+/4F/gP9/fX3/gX+B/317fP+Af4H/fnx9/3FucP91c3X/eXd5/3h2eP9ycHL/dnR2/3Btb/9zcHL/dHFy/2RiY/9samz/bGpr/1pXV/9nZWb/Pjw//xoYG/85Nzj/qqmp/9zb2v+5t7f/tLKx/66sq/+urKz/tbSz/8LAv/+9u7n/xMLA/7q5t/+9vLr/t7a0/7Oysf+4t7X/t7Wz/6Ognv+Ih4n/p6Sj/7i2tv+3tbT/vLq5/8nIx//EwsH/ycjG/7+9vP/Jx8b/y8nH/83Lyf/X1dL/1tTS/9XS0f/V09L/3dvZ/9zZ1//GxML/ycfG/8jGxP/Ny8j/5eTi//79/f//////////////////////////////////////////////////////8PDv/46Njv+5ubn//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////4+Oj/+amZz/0tLS//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v6+v/7+/v//////////////////////////////////v7+/9va2P/Z2Nf/yMbF/8rJyP/CwMD/x8bG/8C/vv/My8v/6unp//7+/v/Y2Nj/XVtd/x8eIf85Nzv/Ozo9/y4sLv8sKi3/MC4x/zIwM/8sKy3/LSsu/zEvMv8yMDT/MC4w/zEvMP82NTf/NDM1/zEvMv80MjX/NzU5/zY0Nv83NTf/NzU4/zk3Ov82NDf/NzU3/zc1OP81MzX/NDEz/zIwM/80MjT/MC4w/zEvMf8xLzH/MjAy/zAuMf8tKy3/MS8y/ywqLf8sKiv/MC0w/ywqLP8tKy3/Liww/zMxNf8wLjH/Mi8y/zAuL/8yMDD/NTI0/zc1Nv86ODr/PDo8/zY1Nv81MzT/NjQ2/zc2N/8uLC3/NjQ2/zEvMP8yMDH/Li0u/zIvMP8zMTL/MjAw/yknKv8iICP/Hh0h/xsaHv8rKi//iomL/+rp6P/n5+b/6eno/+vq6v/u7ez/7u3t/+7u7v/v7+7/7ezs/+rp6f/x8PD/7ezr/+rp6P/r6un/6+rp/+7t6//q6ej/wL++/4eFiP/My8r/xcTD/83Ly//CwL//xsTE/9LQ0P/z8/H/2djX/8/Ny//JxsT/5uPh//39/P/+/f3//v7+///////////////////////////////////////////////////////////////////////////////////////////////////////v7+7/ioiJ/7Oys//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////09PT/lJOV/3Z1eP/6+vr/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////29va/9/e3P/09PT////////////////////////////////////////////////////////////////////////////////////////////8/Pz/v7/A/05MTv8bGR3/Ly4x/4yLjf+TkpX/oaCi/6alqP+gn6H/pqap/6OipP+mpaj/p6ao/6Sjpf+qqav/qKep/6uqrP+op6n/pqWm/6inqP+np6n/qqmr/6Wkpf+op6n/o6Kl/5+en/+ioqT/m5qe/5WTl/+dnJ//oqGj/5ybnv+bmpz/nZye/6Cfov+cm5//oJ+i/5qZnP+Ni47/j46S/5mYm/99e4D/hoSI/4GAhf+Eg4j/iIeK/3Z0d/+Lio3/iYeK/4J/gv99env/fnx9/398fv90cnT/hIGE/2RjZv9lYmb/cW9z/1FQU/9mZGj/XFte/2BfYf9ZWFr/UE5R/xgWGv8fHSH/Z2Zo/93d3f/+/v7/7+/v/83MzP/S0dH/0tLS/9bV1f/Y2Nj/2NfY/9zc3P/X1tf/1dXV/+Tk5P/c29v/2NjY/9jX1//a2tn/397e/+Df3//GxcT/hIKF/9zc2//6+fn/+/v7//z7+//+/f3//v7+///////+/v7//v7+///+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/+OjI3/sbCx/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7a1tv+rqqz/jYyN///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Y19f/ycjI/9DQ0P//////////////////////////////////////////////////////////////////////////////////////////////////////9fT0/5WVlv8dHB//joyP/2dmaP97eXv/jYyO/4OBg/+HhYf/g4GC/4SDhP+RkJH/ioiK/42LjP+EgoP/iIeI/3Z0df+Bf4D/e3l7/4GAgf96eXv/b21w/3Z0dv96eHr/e3l7/318fv91c3T/enh5/3t4ev98eXr/h4WG/3x7fP92dXb/hYSH/3Fucf9wbm//dHJz/3d1df92dHb/fHp7/25sbf98env/ZWNk/25sbP9xb3D/XVpb/3p3ef9qaGn/eHZ2/1ZSUf93dXT/ZmNi/2dkZP9TUVL/a2lq/1FOTv9fXFz/Xlxe/2ZkZv9WVFb/WFVX/4J/gP88Ojv/Hx4g/6Wkpf/5+fn//////////////////////////////////////////////////////////////////////////////////////////////////////8jHyP+DgYT/4ODg////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8vHx/5aVlf+wr6/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////k4+P/kpGR/3d1dv/k4+P//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9HR0f+2tLX/xcTF////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/1BPUv9KSEz/i4qN/8PCxP/Hxcf/vby+/9rZ2/+4t7j/z8/P/9bV1v/CwcP/2trb/8XDxf/W1Nb/vr2+/8rIyv+9vL3/w8LD/8bFx//CwcL/zMrM/8PCxP/Av8D/wsDC/7q5uv/CwcL/sbCw/8XExf/Kysv/tbO0/8C+v//FxMX/zs3P/6+tr//Ix8f/lZOT/87Nzv+hn57/ysjJ/5GOjv/DwsH/mZaV/6yqqv+hn6D/srGx/6Siov+dmpn/s7Gw/4aCgP+IhIT/rqur/2toaP+al5f/eHV2/357fP+hn6H/ZGJk/5KQk/9sa2//m5mc/xQSFf92dXb//f39////////////////////////////////////////////////////////////////////////////////////////////////////////////w8PD/4SDhf/k4+P////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+//mZiZ/7W1tf//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9fT0/4qJiv+sq63/np6f//7+/v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////0tLS/7WztP/Ix8f/////////////////////////////////////////////////////////////////////////////////////////////////////////////////o6Kj/xYVGf+vrrD/SUhM/3Rzdf93dXf/WVdY/3x6fP91c3b/fXt+/4GAgv9ta27/fXt9/3t6fP9/foH/fnx//4eGif+LiYz/jo2Q/4OBhP+TkZT/jIuO/4uKjf+Eg4X/goGD/4uJi/+Mio3/g4GD/3t6fP+Mi47/cnBz/4aFiP+CgoT/e3p8/317ff9/fX//gH+A/399fv9+e3z/cW5u/317fP9zcXL/cW9x/3RzdP9qZ2n/gH5+/3Ryc/9mZGX/hoSI/2hnaf9gXl//d3R2/2ppa/93dXn/TUtN/3x6fP9XVlj/VVRX/1JRVv9eXWL/Ghgc/8zMzP/////////////////////////////////////////////////////////////////////////////////////////////////////////////////Jycn/jIuN/+Hg4P///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/+TkpP/srGx/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+7t7f+KiYr/r66w/4yLjP/19fX////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pzs7/mZiZ/8jGx//////////////////////////////////////////////////////////////////////////////////////////////////////////////////j4+P/LCsu/319f/9WVFj/dnV3/2BeYP9jYWL/a2lp/2JfYP9gXl//dXN0/1dVVv9xb3D/W1lb/3Nxcv9qaGr/cnBw/2poaf9zcXH/aGVl/3d1d/9samz/dXR2/2tpa/9ta2z/aGVm/2hlZv9zcnP/ZWJk/3BucP9ta27/dnR2/2FfYf9xcHL/V1VW/3Fvcf9YVlf/amhp/11aW/9kYmP/VlNV/3Bvcf9YVlj/ZmRm/1BOUv9paGv/WFZY/1pYWf9YVVb/Y2Jl/05MTv9VUlP/VFJU/1VTVf9LSUv/TEpM/0E/Qf9HRkn/dHN2/ywrMP86Ojz/+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////8bFxv+EgoX/39/f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8fHx/5aUlf+xsLH///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f/FxMT/kpGS/66tr/+Hhof/7e3s/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////83MzP+SkZP/x8bG//////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f9mZGb/MC8y/5uanf91c3b/ZGJk/4OBg/9hYGH/cG5v/3h2dv9wbW3/gX9//2xpaf96eXr/bmxu/52cnv9zcXL/lpSW/21qa/+Ni4v/g4GD/4WDhP+DgYL/iomK/3h2d/+OjI3/cnBu/4yKiv97eXr/enl6/3x6fP92dHb/enh6/358fv9saWv/iomJ/3Jwcf9/fX7/Y2Fi/4aDhP9nZGb/dHJz/3d1eP9+e33/ZmRn/4B+gP9yb3D/gH5+/1JQUf90cnP/amhp/1lWV/9ZV1j/YF5g/2ZkZv9PTU7/WVda/05NT/+DgYT/Gxod/4SDhP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////x8bH/4mHif/e3t7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////x8fH/lZOU/6+usP////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f/FxcX/l5WW/7i3uP+Ihon/mZeZ//f39///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////zMvL/5CPkf/Ew8P//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6+ur/8WFBb/rayt/1hXWv+JiIr/cnF0/2ZkZv+Mi43/WlhZ/5aTk/9pZ2j/end4/3Rycv+gn6H/S0lK/6imp/9dWln/npyd/1lWV/+PjY7/iYeJ/3Nxcv+Lior/jYuL/357e/+HhIT/jYuN/317fv9+fH7/eXd5/5aUlv9nZWb/gH+A/3Fvcf90cXH/bGlp/19cXP+KiIn/V1RU/4uJif9iYGH/nZud/1ZVV/9nZWf/eHd5/15dXv9wbW//dXN0/1lYWf+Fg4X/aGdq/11cXv9YV1j/cG5w/1tZW/9oZ2v/REJG/2FfY/8VExb/1tXW///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////BwMH/joyP/9ra2v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/+OjI3/s7Kz//////////////////////////////////////////////////////////////////////////////////////////////////////////////////Dv7//y8vL/0dHS/+bl5f/ExMT/zs3O/7a1t/+urK7/s7Kz/7++vv+xsLH/p6Wl/7e1tv+rqqz/e3p9/9XU1f/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Ozc7/i4qM/8fGxv//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6urq/yUjJf9vbW//Wlhb/2ZkZv9RT1D/YWBh/1tZXP9ramz/WVdX/1lWVv9oZmj/Xl1f/1xaXP9jYGH/XFla/4eGhv9GRET/l5aX/1JPUf91dHX/V1RW/3d1dv9NS0z/eHV2/1pZWv9bWVr/amlr/1BPUf99fH7/Q0FE/3Jwcf9MSkv/e3l7/0lHSP9kYWL/VVJT/1NRUf9pZ2n/REFD/2tqbP85Nzf/amhs/0lHSv9BP0H/TEpK/0dFR/9iYGL/V1VZ/z07PP9WVFb/Xlxf/zUzNP9KSEn/SUdL/0ZER/9hYGX/NDI1/zc2N//8/Pz//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8bGxv+Ihon/4uLi////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8PDw/5KQkf+sq6z/////////////////////////////////////////////////////////////////////////////////////////////////////////////////q6mq/6Khov+hoKL/oqGi/56dn/+cm53/nJud/6SjpP+koqP/pKOk/6alpv+npaX/rKys/9PS0//9/f3//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9DQ0P+Ni47/ycjI///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/W1pc/zIwMv9ycXL/WVdZ/0dFRf9MSUj/NTIx/1hUVf9FQkL/PTk2/1NQUf9FQkL/Y2Fh/0A+Pv9TUVD/TktL/21qaf9EQkL/YV9f/2dlZf9VUlL/Xlxb/1BNTf9pZ2b/Pz09/2toaP9RT0//TUtN/1BOTv9hXl//SkhJ/1ZUVf9gXl//QkBB/1JOTP9DQEH/SUZF/0NAQP9WU1P/UE1N/0VDQv9IRkb/RkRF/0VCQv9WU1L/Ozk6/0ZERf9OTU7/QT9B/zY1Nv9dXF7/PDo9/0A+P/9LSUz/MC4w/2FgZP8ZGBz/gH+A////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////xsXG/46Mjv/e3t7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////w8PD/kY+Q/66urv/////////////////////////////////////////////////////////////////////////////////////////////////////////////////t7e3/7e3t/+7u7v/s7Oz/6enp/+vq6v/r6+v/6+vr/+zs7P/z8/L/+vr6//7+/v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z87O/42Ljv/Hx8f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+ko6T/Ghgb/4iGh/9VU1X/SUhJ/2BdYP9UUlT/cG5v/zw4N/+Cf4D/RUJC/2FfYP9QTU7/b21u/1ZUVf+Miov/TElJ/5CNj/9WU1P/dnR0/2ZkY/+GhIT/YFxb/3Rycv9vbW3/hoOD/2RgYP90cnL/cW9w/1VSU/9xbm//WFVV/3VzdP9QTk//YV9f/1tYWf9gXV7/VVNS/19bWf9ZVVT/XFhY/zs5Of9nZWX/QkBA/1lVVP9fXV//RkND/1dVV/9iYWX/ODc5/2VkZv9ZV1v/MS8x/2VjZv80Mzj/VlRa/xYVGf/ExMX////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Hxsf/joyO/9zc3P////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Dw8P+NjI3/qqmq///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Ozc7/jYuN/8LBwf///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/u7/8dHB//TkxM/z47PP9hX2D/NDM1/1BNTv9JR0n/TUtN/1dUVP9BPj7/RUJC/2dmaP8wLi7/WFVX/zo4Of9MSkv/Pz0+/19cXv8+PD3/WFVV/zo2NP9LSEf/VFJS/0ZDQ/9EQUH/QT4+/1BOTf85Njb/SUdH/0E/P/85Njb/TUpK/zs4OP84NTT/Q0BA/zc0Nf9QTlD/Lisq/0E+P/81MzP/QkFE/z07PP9FQ0X/LCss/0E/Qf8tKy3/REJG/0A+Qv9TUlb/MC4w/0dGSP9FQ0f/JiUn/1BOU/8dHCD/MzI1/+3t7f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8bFxf+NjI7/3Nzc////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8PDw/4iGiP+trK3//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Oz/+Hhof/wsHB/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////11cXv8tKy7/Q0FC/09NTv8eHBz/NTIy/yooKv89Ozz/NjM0/yspKf9APj//Hx0e/0xKSv8rKSr/SEZH/y4sLf9IRUX/KScn/0pIR/8yLy//Pjs6/yonJv82MzP/MzAw/0RCQf8kIyP/NDAw/ywqKv9BPkD/KScn/zAuLv8+Ozz/Lisr/zUyMv8pJyj/Pjw9/y4sLP8sKin/KSco/zIvMf8eHB7/NzY3/yknKP8hICH/IyIj/zEvMf8iICL/JSQn/zIwNP8fHiD/MTAz/z08P/8iISP/TUxQ/xcWGv9paGr//f39////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////xcTE/4qJi//Z2dn////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////w8PD/ioiJ/6inqP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z87O/4WEhP++vr7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////np2e/xsZHP9YVlj/Wlhb/zg2N/9IR0n/SUdJ/1VTVf8+PD3/SEVH/0JAQ/9UUlT/Ly0u/1VTVf82NDb/UE5P/zAuMP9aWFn/PTs7/11aXP83NTb/SEZH/0VDQ/9UUlL/QT9A/1FPUf80MTL/SUdI/09NUP9APT3/Q0FA/z06Ov9WVFT/Ojc4/0lGR/83NDX/S0hK/z89P/9HRUb/ODY4/1lXW/8sKy3/T05R/zQyNP8xLjD/SkhL/z8+QP8zMTP/RUNH/zMyNf83NTn/TUtO/0xLTv82NTr/FxUY/6moqf/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Hxsb/jIqN/9jY2P////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Dw8P+LiYv/qKep///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pzs//h4aI/7u6u//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////c3Nz/HRwg/0NCRv8rKSz/X11h/1BOUf8xLjD/UU9R/zw6Pf9EQkb/Q0FD/zg2OP9VVFj/QkBD/zUzNP9TUVL/MS8w/01LTf86OTr/NzU2/0VDRf8rKSv/QD9C/0RDRv8qKCr/RkVG/zAuMP84Njn/QT9C/zMwMv9GREb/NzU3/zw6O/88Ojz/KCYn/zc0Nv88Oj3/MzE0/y0rLf8vLS//Kigq/0JBQ/8oJyn/NTQ3/z48QP8pKCv/PDo//zAuMv8nJSj/MC8y/y4tMP8rKiz/OTc8/xoZHP8rKSz/3t7e/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8C/wP+Ni43/1dTV////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8PDw/4yKi/+lpKX//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Ozv+GhYb/ubi5//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////f39/9MS03/Gxoe/ygnKv8sKi3/IiAj/yMiJf8kIiT/JyUn/yEfIf8pJyn/Ly4w/yMhIv8mJCb/Ly0v/ycmJ/8mJSf/JSQk/x8dHv8pJyn/IyEj/yMiJP8hICL/JyUn/yMhI/8mJCb/ISAh/ygmKf8hHyD/IR8h/yYlJ/8fHiD/IyIj/yQiJf8iISP/IB8h/yQjJf8gHyH/IiEj/xwaHf8eHR//IR8i/xsaHv8dHB//Hx4h/xsZHf8iISX/HRwg/xgWGf8aGR3/HRse/xsZHP8hHyT/GBYa/1NSU//7+/v/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+//42Ljf/W1tb////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////w8PD/iYeI/6inp///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////zs7O/4aFhv+8u7z//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/4qJi/8aGR7/NjU5/ywqLv8nJir/Kikt/x4cH/8fHSD/GBYa/x4cH/8aGBr/HBoc/xwaHP8cGx7/Ghkc/yMiJv8aGBv/GRca/xoZG/8gHyL/IyEk/ycmKv8eHB7/JCIl/x0bHf8bGRv/IR8i/x8dIP8eHB7/KSgr/ywqLv8eHB//MS8z/yEgI/8oJyr/KCYp/yUjJ/8fHSH/HRwg/xkYG/8gHiP/IB8j/x0cIP8YFxr/JyUq/yEfI/8wLjH/ISAj/y8uMv8vLjH/Hx4h/ysqLv8YFxr/kZCR///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Av7//i4mM/9XV1f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Dw8P+Liov/qKeo//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/19fX/5OTk/+Dg4P/e3t7/2dnZ/9va2v/c3Nz/2djY/9jX1//b2tr/2tna/9fW1v/X1tb/19bW/9bW1v/V1dX/1tXV/9fX1//X1tb/19fX/9nZ2f/Y19f/19bW/9fW1v/Z2Nj/1tXV/9bV1f/W1tb/1dXV/9XV1f/V1dX/1dTU/9XV1f/V1NT/1dXV/9XU1P/V1dT/0tLS/9TT0/+xsLD/dHJ0/56dnv/R0dH/09LS/9PS0v/S0tL/09PT/9HR0f/U09P/1NTU/9LR0v/S0tL/1dTU/9TU0//U09T/0tLS/9PS0v/T09P/0tLS/9PS0//S0dL/0dDR/9HQ0f/R0NH/z8/P/87Nzv/MzMz/mpma/xYVGP8aGR3/GBcb/xgXG/8YFhv/GBYZ/xgXG/8YFhr/GRgc/xkXG/8YFhn/GBca/xgWGv8YFhv/FxYa/xgWG/8bGR7/GRgc/xkXHP8bGh7/GBcZ/xkXGv8ZGBv/Gxkc/xsZHP8YFxr/GRgb/xkYGv8ZGBv/Ghkd/xoYHP8aGR7/Gxke/xkXG/8bGRz/GRcb/xcWGv8YFhr/Gxkd/xkYHf8bGh//GRgd/xgXG/8YFhv/GRgd/xkYHP8ZGB3/GRgd/xoYHP8ZGBz/FxYa/xsaHf+gn5//zczM/83Mzf/Ozc3/zc3N/8zMzP/Ozs7/0M/P/8/Ozv/Ozc7/z8/P/8/Pzv/Ozs7/z87P/9DQ0f/Qz9D/z87O/8/Pz//Q0ND/z87O/8/Pz//R0NH/0dDR/9LR0v/Q0ND/1dTU/6Oiov9vbW//rq2t/9DQ0P/Q0ND/0NDQ/9DQ0P/Q0ND/z8/P/9DQ0f/R0NH/0M/Q/9HR0f/U09P/0dHR/9HQ0f/T09P/1NTU/9LR0v/S0tL/1NTU/9DQ0P/R0dH/0tHS/9PS0//T09P/09PT/9LS0v/V1NT/1NTU/9PT0//U09T/1NTU/9TU1P/V1NT/zMvL/3d1d/+JiIj/2NfX/9jY1//h4eH/8PDw//7+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+//Ix8f/d3Z3/0A/Qf8tKy3/Kyos/ycmKP8iICP/IiAj/yQjJP8iISP/IB4h/yIhJP8iICP/Hx0g/x4cH/8fHSD/Hx0g/x0bHf8eHB7/IB4g/x0bHf8eHB7/IR8i/yAdIP8fHSD/Hx4g/yAeIf8eHB//Hh0f/x4cH/8eHR//Hhwf/xwaHf8bGh3/HBsd/x0bHv8dGx3/HRsd/x0bHf8bGRz/Gxkc/xsZHP8YFhj/GBYY/xwaHP8cGh3/HBoc/x0bHf8cGhz/Ghgc/xsZHP8dGx7/HBod/xsaHP8fHSD/HBod/xwaHf8bGR3/Gxod/xwbHf8cGx7/HRwf/xwaHf8aGBz/Gxkc/xwbHv8aGBv/GRcb/xgWGv8YFhn/FBMW/xUUF/8WFRn/FRQX/xQTFv8UEhb/FBMW/xMSFv8UExf/FRMX/xQTFv8UExb/FRMX/xUTF/8UExj/FRMX/xQTFv8UEhb/FRMX/xYVGP8VFBb/FRMW/xQTFv8UEhX/FBIW/xUTFv8VExf/FhQX/xYUF/8VFBf/FhUY/xYVGP8VFBj/FhQY/xUTF/8VExj/FRMX/xQTF/8VFBf/ExIW/xQTF/8UExf/FBIW/xMSFv8UExb/FRMX/xUTF/8VExf/FBMX/xQTFv8VExf/FRMW/xcVGP8YFhn/FhUX/xcVGP8WFBj/FhUY/xkYGv8aGRv/Ghkc/xgXGf8aGBv/Gxob/xkXGf8YFhn/Ghgb/xsZHf8aGBv/GRga/xoZHP8ZFxr/GBca/xsZHf8bGRz/HBoe/xoYGv8dGx7/Ghkb/xYUF/8YFhj/GBcZ/xkXGv8bGhz/Gxkc/xkYG/8XFhn/GRgb/xoYG/8ZGBv/Gxkc/x4dIP8aGRz/Ghkc/xwbHv8fHSH/HBse/xsZHf8eHCD/Ghkc/xoZHP8bGhz/HBoc/xwbHf8dHB7/Ghkc/x0cH/8dGx//HBse/x0bHv8dHB//HRse/xwaHP8cGh3/FhQY/xYVF/8fHiD/Hx4f/yooKv84Nzn/ZWRl/7Kysv/y8vL////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////j4+P/YV9g/x4dIP8lJCf/UlFV/z89P/8tKy3/Kyks/y4tMP8yMDP/MjAy/zQzNv81MzX/Mi8z/yclKP8rKCz/LSst/y4sL/8uKy7/MS4x/yspK/8xLjH/MjAy/y4rLv8uLC7/MS8x/zMxM/8wLjD/MjAy/y8uMP8uLC7/LSst/y4sLv8wLjD/Ly0w/zAtMP8xLjH/MzEy/y0qK/8zMDP/Ojc5/zg2OP83NDb/PTs8/zw6O/86ODn/Ozk7/0A9QP9FQkT/Pjw9/0E+QP9APkD/PDo8/zw5PP8/PD7/Pzw//z88P/86ODr/OTg6/z49QP8/PUD/Pz1A/0JAQ/9HRUn/SEdL/0lISv9IRkn/SUhK/0xKTf9RT1L/VlRX/19dX/9mZGb/bWtu/29tb/95d3n/e3p9/3l4e/95eHv/gYCD/4OChf+CgIP/gYCC/358f/94d3n/fn1//4KAg/+Eg4X/fXt+/318fv99fH//fXt+/4B/gf+DgoT/g4KD/4KBhP+CgYT/g4KF/4OChf+GhIb/hYWH/4GBg/+CgYP/gYCC/4GAgv+AfoH/gH+B/4B/gf+AfoH/goGE/4SDhf+GhYf/goGD/359gP+AfoD/fn1//3x7ff9+fYD/fHp+/3p5fP97en3/e3p9/3d2eP9wbnD/aWdp/2VjZv9paGr/ZWRm/2hmaP9samz/ZmRm/15cX/9eXF//YF5g/1VTVf9UUlT/TEpN/01LTv9RT1L/TUtN/0lHSf9HRUj/R0ZI/0NCRf9GREf/RkVI/0NCRf9CQUT/QD9D/z89Qf89PD//PTxA/z08QP8+PED/Pz5B/zs5PP88Oz//Pz5A/0FAQ/8+PUD/ODU5/zw6Pf8/PkH/PjxA/0NBRf9DQkX/Q0FF/z48Qf9GRUj/RENG/z49QP8+PD//QD9C/0FAQ/89PD//PDo9/zs6Pf82NTj/MS8z/zIwM/8wLjL/MS8y/zY0Nv88Ojz/Pjw//0NBQ/9DQkX/S0lN/0hGSv9JR0n/XVpa/2VkZv8pJyr/FxUY/z08Pv+1tLX//v39///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/xsXF/yYkJv8oJyr/dXR3/3d2ef9OTFD/cnBz/6Kgov+ysbP/wMDD/8TDxv/CwcP/ysrN/8fGyP/OztH/2tnc/9rZ3P/Q0NP/0dHU/9bV2f/V1Nf/2Nfa/9rZ3P/e3eD/29vd/9zb3f/c3N//2trc/9nY2//e3d//2tnb/93d3//c3N7/29ve/9bV2P/f3+H/3d3f/93d4P/e3d//4uHk/+Li5f/g3+H/4eHj/+Dg4//f3+H/3d3e/9va3f/W1tn/0dDT/9DQ0v/R0NL/zczQ/9LR1P/Qz9L/zMvO/9HQ1P/Kysz/zMvO/8zLz//Hxsr/wcDC/7+/wv+9vL//trW4/7e3uv+4t7r/t7a4/7S0tf+wsLL/sK+y/6yrr/+gn6T/nZyg/5iXmv+Xlpr/jo2Q/4uKjv+Mi4//i4qN/4mHiv+Hhon/h4aJ/4qKjf+JiYz/i4qN/4uLjf+Ih4n/h4aJ/4qJi/+NjI//kI+S/4+OkP+RkJL/kI6R/4iHiv+GhYn/hoWI/4ODhf+BgIP/goGE/4KBg/+Eg4b/g4OG/4KBg/+CgYT/goGE/4OChf+CgYT/f36B/359gP+Af4L/gH+B/359f/9/foH/gYGD/4WEh/+EhIb/goGD/39/gv+Af4L/gH+C/4SDhv+GhYj/h4aK/4yMkP+OjZH/iYiM/4qJjf+MjI//jYyP/5CPkv+NjY//jo6Q/4+Pkv+WlZn/mpmc/52cn/+dnKD/nJue/5+eov+bmp7/pKOn/6Oipv+mpaj/oqGk/6WlqP+mpan/q6qu/7Oytf+lpKj/q6uv/7Cws/+wr7L/s7K2/7Kxtf+4t7r/trW3/7m5u/+1tLf/uLi6/7Oytf+2tbj/t7e5/7u6vP+5ubv/t7a4/7u6vv+4uLv/urm8/729wP+8vL//vLu+/8C/wv/Av8L/v73A/7++wP/BwcT/uLi7/8HAw//CwcX/wcDE/8HAxP+/vsL/vLu+/7i2uf+1tLf/rayw/6emqf+amZ3/i4qP/2xrcP9VVFj/R0VI/4qIiv+Hhof/Pjw//xkYG/9/fn//+Pj4/////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/8DAwP8nJij/Q0JF/5WUlf9KSEr/TktN/2lnaf9hX2D/YmFj/2JhY/9qamz/amls/21rb/9oZmr/c3J2/3Z1eP90c3f/dXR4/3Z1eP95d3r/hIOG/358gP95eHv/eHd6/3h3e/+FhIf/hIOG/318f/9/fYD/hIKF/318f/+Af4P/hIKF/399gP9/foH/gH6C/4iGif+MjI7/jIuP/4eGiP+KiIr/i4qM/4GAg/+Ghoj/i4mM/5KQkv+Ni43/lJOV/42Mj/+GhIf/kI6P/5CPkP+Mio3/h4aI/4mIi/+FhIj/hoSI/39+gf+Fg4f/hIKG/4SDhv+JiIn/i4qM/4eGiP+Eg4X/jIuM/4qJjP+GhYf/goGC/4WEh/+EgoX/g4KE/4OChP+GhYf/iIaI/4aFh/+Ghof/iYeJ/4qJi/+Hhof/iomK/4uKi/+KiYr/jIqL/4+Nj/+KiYr/h4WG/4iGiP+Mioz/jIuM/5GQkv+PjY7/jo2O/4yKjP+OjI7/j42P/46Nj/+Ni43/j46Q/5CPkf+Mi4z/iIeI/42Ljf+JiIn/iIaI/4eGh/+Fg4X/hIKE/4aEhv+LiYv/iYeJ/4KBg/+FhIb/ioiK/4OBgv+FhIX/ioiL/4WDhf+Mi4z/iIaH/4OBgv+KiIn/hIOD/4WDg/+KiYn/iomK/4OCg/+Jh4n/h4WH/4SChP+Eg4T/h4aH/4aFhv+DgoL/hIOE/4aFh/+DgYP/hoSF/4SDhP+BgIH/gH6A/4KAgv+DgYL/gX+A/4OCg/+EgoP/hIKD/4KAgv+BgIH/hYOF/39+gP9/fn//fnx+/39+f/+Afn//fn1//4KAgf+Afn//fXx+/359f/+Af4D/e3l7/399f/+CgYP/gH6A/318ff+CgIL/gX+B/3l4ev95eHr/d3V3/3V0dv9wb3D/eHZ4/3NxdP92dXf/cnFz/3h3ev9wbnD/b25x/21sb/9mZWb/b25w/2dmaP9kYmT/ZmRk/2hmZ/9jYmP/V1ZX/1tZWv9YV1n/TEpL/1hXWf9TUVL/Ozk7/y8tL/90cnP/b25w/xoZHf9ubW//9vb2///////////////////////////////////////////////////////////////////////////////////////////////////////j4+L/NjQ1/1BPU/+joaT/RkRG/5GPkv+amZn/pqSm/5aTlf+1tLb/uLe5/8nIyf/Av8D/ysnK/8fGyP/My8z/ycnK/87Oz//Qz9H/0dDT/9XV1v/V1db/0tLU/9HR0v/S0tT/09LU/9XU1v/T0tT/0tLU/9DP0f/Qz9H/z8/Q/9PS1P/R0dL/zczN/9LR0v/U09T/09PU/93d3v/X1tj/3Nvd/9nY2f/T09T/39/h/9rZ2v/Y19n/z8/Q/9LR0v/Qz9D/z87P/9zb3P/T0tT/1NPU/9fX2P/h4OL/3Nvd/97e4P/l5ef/19fY/9HR0v/W1df/2dja/9ra2v/Z2dr/3dze/9zc3f/V1Nb/4eDh/+Df4f/Y19n/397f/+Tk5f/k4+X/1tbX/9TT1P/X1tj/zs3O/8nIyv/Ozc//zMvN/8fGx//My8z/ysnK/8bFxv/Ix8j/zMrM/8zLzf/JyMn/xcTG/8jGyP/My8z/ysnK/8XExv/JyMn/xsXF/8jHyf/JyMn/y8rM/8rJzP/IyMr/yMfJ/8nIyv/MzM//ysnL/8rIyv/Gxsb/x8bH/8vKy//JyMn/wsHD/8bFxv/My8z/xMPF/8jGyP/Ozs//xMPF/7++v//Kycr/ysnL/8zLzP/Kycr/xMLD/8LBwv/Ew8T/v76+/8nIyf/JyMn/wsHC/8fGyP/Hxsf/xcXG/8XDxf/Gxcb/xcTF/8HBwf+/vr//ysnK/8XExf++vb//wL/B/8XExv/Av8H/wsHC/8bFxf/DwsP/x8bH/8TExP/FxMb/vby9/8C/wP/NzM7/w8PG/8DAw/+/v8H/w8LE/8TDxP/Gxcb/xsXG/8fGyP/Av8D/xcTG/8XExv+8u77/wcDC/8XExv/FxMb/w8LE/7++wP/Hx8j/wsHC/728vf+8urv/wL/A/7q5uv+7urz/tLO1/7Kxsv+1s7X/wL/B/7Oys/+xsLL/tbS2/66srv+npqf/o6Kj/6+ur/+0srH/joqJ/7Kxsv+Zl5n/lJGS/5eWmf+EgoT/dHFy/5aUlf9fXV3/c3F0/0tKTf9XVlf/hIOF/xsZHf+Qj5D//v7+/////////////////////////////////////////////////////////////////////////////////////////////f39/3x7fP8qKSz/tLO3/yooKv9PTU//Xlxd/2lnav9ycHL/dHN1/3p4ev9/fYD/enh5/39+gP+KiYz/hoaJ/4SDhv+Mi47/i4qN/5OSlv+VlJj/k5KV/5mYm/+enaD/l5aZ/6Gfov+ioaP/qKep/6uprP+sq67/rKuu/7Gwsv+zsrT/qqmr/66tr/+ura//sbCy/6uqrP+trK7/w8LE/6yrrf+ysbL/srGy/7Kxsv+8u7z/sa+x/769v/+sq63/r66w/62rrP+3trf/wL/B/7SytP+trK7/s7O1/728v/+3t7r/rKuu/7W0t/+ko6b/pqWo/6yrrf+qqKr/pqSn/6inqv+mpaj/q6mr/56doP+dnJ//np6h/5qZnf+bmZz/np2g/6moqv+dnJ//m5qd/6moqv+npqj/pKKk/6yqrf+npqj/q6qr/6upq/+sq67/q6qt/66tsf+rqq3/oaCi/6Ggov+lpKf/oaCj/5+eof+gn6H/n56h/6Cfof+dnJ7/o6Kk/6OipP+ZmJr/nZye/4aFh/+Mi43/k5KU/5iXmf+amJr/mpib/5ubnf+hoKL/mZia/5KRk/+hoKL/n5+g/52bnf+Yl5n/mJaY/6Ggof+cmp3/mJeY/5CPkP+npaj/oJ+h/5WTlv+gn6H/p6an/6Kgov+ioaP/n56g/5ORlP+mpqj/oqGk/52cnv+cm57/oqCj/5SSlf+bmpz/p6ao/5ybnv+enZ//nJqc/5uanf+Uk5X/kI6Q/5uanP+SkZL/n52g/6Ggo/+Qj5D/iYeI/6Ggov+gnqH/m5qc/4yLjv+VlJf/mJib/42Mj/+OjI7/lZOV/5+eoP+RkJL/mZib/5eWmP+QjpD/kpGT/56doP+hn6P/paSn/5OSk/+RkJH/mpmd/5WUl/+Ih4n/lJOW/4eGiv+Ih4n/iIaJ/5qZnf+AfoH/k5KV/4yKjP+Zl5n/kZCR/4F/gf+QjpD/i4mL/5GPkf+FhIb/eXd4/3RzdP+Ih4r/bGps/2ZlZ/+Ih4r/V1ZY/2xqb/9XVln/V1VX/0VDRf9PTlD/QD5A/0pJSv9SUFH/cnFz/yQjJv/U1NT////////////////////////////////////////////////////////////////////////////////////////////q6ur/IyIk/4qJjf9fXWD/bGpt/3x6fP+Bf4H/gn9//4uJif+Uk5T/mJaX/6Gfof+op6n/pKOl/6emp/+urq//r66w/6SjpP+op6n/rq2v/7Kxsv+wr7H/rq2u/7CvsP+wr7D/q6qr/6+ur/+wrq//sbCw/7Cvsf+vrq//tbW2/7u6vf+2tbb/tbW1/7SztP+zsrT/sbGz/6+usP+8u77/ubi6/7Sztv+6ubv/urm7/7e2tv+0tLX/tbS1/7Gvsf+vrq//sK+w/7q6vP/Qz9H/3Nzd/7y6vP+3t7j/uLe5/7S0tf+3trj/u7q8/7u6vP+9vL7/vr6//728vv/Av8H/vby9/8G/wf++vr//wcDC/7u6u//AwML/vLu9/7m4uf+6ubv/tbW2/7SztP+2tLb/ubi5/7m4uP+6uLn/tLOz/7Kxsv+zsrP/s7K0/7OytP+0s7T/tLO1/7Gwsf+2tbb/tLO0/7SztP/Av8H/vLy9/7Sztf+zs7T/uLe5/7m4uv+0s7X/srGz/8HAwf/Ix8n/x8bH/8bFxv/NzM7/wL/B/769vv+6urv/trW3/7Sztf+2tbf/s7K0/6upqv+vrq//sK+x/66trf+ura7/oZ+h/6+ur/+tra3/qqir/6emp/+wr7D/rKut/6qqq/+wsLH/mpiY/6CfoP+sq6z/pqWn/6uqrP+wr7D/mpiZ/6Sjpf+rqqv/q6ut/6inqf+fnp//nJqc/6Oio/+ioaL/oJ+h/5ybnf+cm53/nJuc/6CeoP+Vk5X/i4qL/5+eoP+SkZL/j46P/52cnf+dm53/lpWW/5WTlf+VlJX/j46Q/4uKjP+PjZD/kpGT/5KRkv+Yl5j/j46Q/4mIif+FhIX/hoWG/5CPkf+Hhoj/iYiK/4WEhf+KiYv/iomL/4eGiP+Hhoj/h4aI/4WEhv+BgIH/hoWG/4aFh/98e3z/gX+A/2xqa/+Afn7/hIOE/21qa/9/fX7/fXt8/2xqav9xbm7/c3Fz/4iGh/+Af3//ZWNk/4GAgP9raGn/Uk9Q/3d1df9TUFD/V1RT/3x6ev9CQUL/aGZn/yYkJ/94dnj/LSwv/3Rzdf/9/f3//////////////////////////////////////////////////////////////////////////////////////6alpv8qKCz/lJOW/zw6PP97en3/d3Z4/3d1eP+Xl5n/j42P/6Cfof+rqqz/iYaI/7CvsP+4t7n/qair/5ybnP+6ubz/wMDC/7y7vP/AvsD/uri6/7m5uv/Gxcb/wsHC/8bFxv/Kysz/xsXH/8bFx//CwcP/yMfJ/8vKy//V1Nb/y8vN/8fHyP/Ew8T/ysnK/8zMzf/Ew8X/z87Q/8TDxv+9vL7/wL/A/8HAwv+8u7z/ysnJ/8nIyf/Qz9D/0dHS/9HQ0f/Ozc//2tnb/87Nz//c293/xsXH/8fGyP/Gxcf/xsXH/8LBw/++vr//v76//728vv+/vsD/xMPF/8rKzP+3trn/tbS3/7Gxs/+7urv/vLu9/7Cwsf+trK7/ubi6/7m3uv+/vsH/t7a5/8HAwv+wr7L/wL/B/6+ur/+8urv/xcXH/8LBw//Dw8T/uLe6/7e2uP/Av8H/w8LE/8LCw//BwML/wcHC/7a2uP+urbD/u7q8/7e3uf+3trf/vr3A/728vv+ysbT/q6qs/7m4uv+/v8D/ubm6/8HAwv++vb7/ubi6/7q5u/+7ur3/urq8/729v/+8u77/v77B/7i3uv+xsLP/tLO0/8bGx/+8u77/urq8/8DAwv/ExMb/srG0/66sr//Av8H/qqms/728vv+/vsD/sbCy/6+ur/+5ubr/uLi5/6mnqP/CwcT/v77B/7a1t//Hxsj/xMTG/728vv/CwcL/xcXH/7W0uP+5uLr/ysnL/6yrrf+8u73/x8bI/7q5vP/Ix8r/r66y/8jHyv/Hx8n/sK+x/8C/wf/IyMr/xMTG/7Gxs//My87/u7u//8PDxv++vL//v76//7y7vf/Ew8X/s7Kz/8zMzf/Hxsf/xcPE/8zLzf/R0NP/xMPF/7OxtP/Hx8j/ycjJ/6uprP/Ew8X/ysrM/7OytP+3trj/yMfK/66tsP+7ubv/pqSm/7y6u/+tq63/wcDC/6OipP+pp6n/wcDC/5uanP+0s7b/nJue/5eWmf+2tbf/gH6A/5KRlP+op6n/cnBz/5GPkv9xb3D/VlRW/42Ljf9EQkT/c3Bx/y0rLf9raWv/Kikr//Dw8P//////////////////////////////////////////////////////////////////////////////////////ZGJk/1lYW/9ubG//NTM2/1pYWv9QTk//TEpK/19dXf9iYGH/Y2Fj/2hnaP9ubG7/Z2Vm/21rbf95eHr/eXd5/3Z1d/9/foD/gX+A/4mHif+Fg4T/hYOE/4KAgf99fH3/lZSW/4qIi/+LiYv/joyN/5GPkf+PjY7/l5WX/4+NkP+WlZf/1NLT/7Gvsf+mpaf/nJqc/5mXmf+PjY7/kpCS/5eVlv+Ylpf/lJOU/5STlP+cm53/nJub/56dnv+Yl5j/lpWW/5aVl/+bmZv/nZyd/6Khov/CwcL/29rb/7u6u/+rqav/zczO/6Sjpf+mpKb/oJ+h/6Ggov+dm5z/mJaY/5qZmv+amJr/lJOU/5WUlf+joKH/t7a3/6elp/+enZ//mJaY/52cnv+WlZf/mZiZ/5uam/+vrrD/k5KU/5ORk/+amJr/kI+Q/6CeoP+Rj5H/mpma/5WUlv+TkpT/mZia/5STlv+TkpT/mZiZ/5STlf+Qj5H/lpSV/5SSk/+UkpP/lJKT/6mnqf/W1db/2djZ/62srv+cm53/n56g/7u7vP/g3+D/rKus/5KRk/+JiIz/hoSI/4mIif+KiIv/j42Q/4yKjP+DgYL/hIGD/5aUlP+Fg4T/fHp8/317ff+JiIn/mpia/3d1dv+SkZL/hoWI/5STlP+HhYf/j4yN/3d1dv+IhYf/hoWG/4yLjP+HhYb/iYeL/4OCg/+Hhoj/hYSH/3Z0d/99fH//kI6R/4GAgv9zcXT/jIuN/3d2eP9xb3H/jo2O/3Jwcv+Mio3/dHJz/3Nxc/9+fX//dHJ1/359gP+Bf4L/fXx+/25tcP96eXz/fXx9/3Nycv+Bf4D/fXt8/3V0df98e33/e3l8/3x6fP97env/bGpr/3VzdP98env/eXd6/2NhY/95d3n/cW9x/15cXv97enz/dHJ1/2JgY/9kYmT/d3V4/2lnaf9tbG7/b21u/2NhYv9ZV1j/e3p7/2ViY/9VU1T/dXN1/2VjZP9aWFn/a2lq/0ZEQ/9zcnP/S0lL/01LTP9lY2b/QT5C/0lGR/9MS07/NDI0/y4sLv9CQEH/MS8x/2BdX/8cGh3/zMzM//////////////////////////////////////////////////////////////////////////////////////87Oj3/fHt+/2ZkZ/9gX2L/o6Kk/6emp/+OjI7/sK6w/7i2uP+npaj/wcDB/8fGx//Lysz/pKOl/8TDxP/R0NL/w8LE/8C/wP/DwsT/ycjK/8jHyf+7u73/wcHD/8/O0P/My83/xMPF/8fGx//Ny83/4eDh/9va2v/Y1tf/1dTV/9ra2//b2tv/393e/9fW1//V1Nf/3t3f/+rp6v/p6Oj/4eDg/93c3P/W1dX/09LS/8nJyv/CwcL/wL/A/97e3//Hxsj/xMPE/9HQ0v/NzM//ycjK/+Xl5v/p6Oj/3Nvc/9jY2P/b2tz/2tna/9rZ2//U09X/5eTl/+Tj5P/k4+T/6+rr/+no6P/n5ub/6enp/+3s7f/v7u//7e3u/+fm5//k5OT/5eXm/+Xj5P/j4+P/4+Pk/+bm5//h4eL/6enq/+Xk5v/j4+T/5OTm/+Hh4v/e3d//5OTl/+Lh4v/j4uT/4eHj/+Dg4f/k4+X/5OPl/+Tk5P/m5eb/5eTk/+Tk5P/k4+T/4N/g/3Vzdf8mJCj/GBca/xYVGP8VFBX/Gxkb/0JBRP+1tLX/6ejp/+Tj5f/n5uj/5eTl/+Xl5v/h4eL/4eHi/+Li4//X1tf/3t3f/+bm5//j4+X/4+Pl/87Nzv/k5OX/2trb/9/e4P/T09X/39/h/97e4P/l5eb/5OTm/9HQ0v/l5eb/5OPk/9nY2f/r6uv/5uXm/8zLzf/m5eb/5eXm/9fW2P/j4uP/6ejq/+Hh4//NzM7/5ubn/9DQ0f/f3uD/1dTW/8XExv/j4eP/t7a4/97d3//Y19n/vLu+/9XU1v/V1Nf/t7a5/7W0t//Y19n/0dDT/8LBw//T0tT/ycjK/8vKzf/Y19r/w8LF/8vKzf/a2dv/tLO1/7u6u//a2tr/tLO1/8HAwv/e3d//zMzO/7Gvsv/c293/3Nve/7Gvsv+4trj/vr3A/6Wkpv/NzM7/sK+w/62srf+tq63/v76//7Gwsv+npqf/ycfI/5GQkf+pp6f/o6Gh/4mHh/+8u7z/mZeY/4OBgv++vLz/WlhZ/56dnf9nZWj/Tk1Q/4KAg/9HRUj/bWtr/y8tLv+ko6T//////////////////////////////////////////////////////////////////////////////////f39/yYkJ/+Ihon/aWdo/zY0Nv9OTE3/Q0BA/01LS/9LSUn/Yl9f/2BdXf9ta2z/Y2Bh/4OCg/+GhIb/dHFy/317ff+ZmJr/lJOV/4qIiv+Ihof/ioiJ/6Sjpf+enaD/hYOG/5ybnf+pqKn/oaCh/6CeoP+IhYX/n56e/6qoqf+koqT/qKep/6Oho/+opqn/qKeo/6qpq/+koqP/0tHS/5iWmP+sq6z/rq2u/62srf+xsLH/tLOz/7u6u/+8u73/0tLU/83Mzf+4t7j/v77A/7++wP/FxMb/zMvM/769vv+qqar/pqWn/66tr/+vrrD/09PU/7Cvsf+pqKn/kI6R/5qZmv+WlJb/jo2P/6Ggof+Mi4v/lpSU/4+Njv+QjZD/l5WW/56cn/+Yl5r/k5KU/56cn/+ZmJz/l5aX/5aVl/+bmp3/hIOF/5CPkf+dnJ7/j42O/46Mjv+CgYL/hYOF/46Njv+Ni47/jIqN/39+gP+Hhof/ioiJ/46Mjv+Vk5T/xcTG/93c3f9APkD/FxUZ/yQjKP8kIyf/NDM3/yEgI/8mJCn/HBse/xcVGP+bmpv/vLu9/5aVmP+EgoX/d3Z4/4eFiP90cnX/f32A/3NydP9nZGb/gYCA/3x6e/91c3X/b21v/3d0dv94dnf/eHd5/29sbv92dHX/hIKD/21rbP+GhIf/g4GD/2xqa/9jYGH/dnR1/2lnaP90cnX/dHJ1/1ZVVv95d3j/fXt9/29tb/9paGr/fnt8/4aEhf9pZmf/e3p7/4KBg/96eHn/f3x9/3Jwcf+Qjo//eXd3/4OBgv+SkZP/aGZo/4aEhf+Xlpf/k5KU/3Z0df+KiYv/eHZ4/3Rxc/+Ni43/iomK/2JfYP+Uk5T/jIuN/2VjZf9/fYD/iIeJ/1tYWv+MiYv/f31//19dXv9/fX7/iYeJ/1FPUf92dXb/bWts/15cXf9ycHP/fHt9/1xZWv9qaGn/Z2Zn/2dmaP92dXf/VlVX/3x7fv9KSEv/fnx//2hmaP9APj//dnV5/zs5O/9lY2X/WFZa/0NBRP9VU1X/R0VH/0RCR/81NDf/S0lL/y4tL/9xbnD/List/4iHiP/////////////////////////////////////////////////////////////////////////////////7+/v/HBse/4yLjf+EgoL/WFZX/4B+f/97eXv/bGpr/3d1d/+SkJD/fnx7/5SSkv+DgYH/h4WF/5eWlv+bmZv/k5GS/5uZmv+dm5z/lJOU/56dnf+TkZP/m5ma/6Sio/+fnp//m5ub/6qqqv+gnp//paSl/6qpqv+op6f/qKeo/6Wkpf+rqqv/rKur/6yrrP+trK3/rq2u/7Sys/+wrq7/qaio/6qpqv+trK3/q6qr/6empf+qqar/rayu/6yrrf/DwcL/rq2u/7Kxsv+wr7D/srGz/62rrf+ura7/rKus/8zLzP++vL3/1dXV/6yrq/+ura//rayu/7Cvsf/Fw8X/uLi5/8TDxf+vrrD/sbCx/7Kxsv++vb7/u7q8/7Kys/++vL3/xsTG/8jGyP/Hxsj/wsHC/9XU1f/My8z/yMfI/8jHyf/Hx8j/ycnL/87Nz//W1df/1tXX/9PS0//Nzc7/zMzN/87Nz//T0tP/09LT/9HP0f/My83/ysnL/9ra2//t7e7/aGZp/xYVGf8sKzD/ISAl/0RCSP8wLzP/NjQ3/yEfIv8nJiv/IyEl/xgWGf+0srP/6+vs/8zLzf/Ix8n/y8nL/7q5u/+8u7z/w8LE/8G/wP/DwcP/tLK0/8bExf+9vL7/wcDD/7u6vP/CwcP/wsHD/6yrrf/CwcL/sK+y/6OhpP+2tbb/vr2//7u7vP+wr7H/sK+w/7m3uf+9vL3/uri6/6Sjpf+8vL7/sbCz/6moq/+0s7T/vLq8/7S0tv+amJr/t7a3/7a1t/+vrrH/n56g/6moqv+vrq7/npyd/7m3uP+mpab/h4WG/6mnqP+ysbP/l5WX/4yKi/+vrrD/j46Q/4iHif+1tLX/n56h/399fv+mpaX/uLe5/4SDhf+hn6D/kI+Q/5iXmP+mpab/iIeI/4uKi/+joqT/kY+R/4OBgv+VlJX/np2f/4B+gP+Uk5T/kpGS/4eFhv+Zl5j/bmxs/4+Ojv94dnb/gX+B/4WDhP9/fYD/kZCR/25sbf9kYWL/jIqL/1xZWv91cnL/VVJT/2xpZ/97eXn/RkRG/05NTv9aWFr/MC8x/3x6e/8vLTD/gYCB//////////////////////////////////////////////////////////////////////////////////v6+v8dGx3/i4qM/4SBgf9ST1H/fHt7/399f/91dHX/fXt8/6Ohof+vrq7/sa6u/7y7vP/ExMX/wL6//8HAwf/Gxcf/zMzN/8jHyf/JyMr/zs3P/87Nzv/JyMn/y8rM/9DP0f/Lysv/x8bG/8vJyv/My8z/zcvM/8vJyv/Kycr/zs3O/9DP0P/Pzc7/z87P/9HQ0f/R0ND/09LT/9XU1f/V1NX/1dXV/9jX1//Z2Nj/19bW/9XU1f/W1tb/1dTU/97d3v/U09X/2djZ/9XU1f/X1tf/2dnZ/97d3v/d3N3/4uLi/9XU1f/o6On/1dXV/9bV1v/X1df/1dTV/9fW1//W1db/3Nzc/9TU1f/T0tP/zs3O/9DP0P/T0tT/0M/Q/9HQ0f/Q0NH/0M/R/9HQ0v/IyMj/z8/Q/8TExv/AwMH/v77A/728vf/CwcP/w8PE/8vKzP/Jycr/urm6/8LBwv+6ubr/vby9/7W0tf+6uLr/urm7/7q5u/+5uLr/0tHS/8jHyP8cGh7/IyIn/zUzOP9PTlL/MjAz/0dFR/8qKSv/ODY5/zw6Pf8mJSr/Ghkd/0hHSf/p6er/yMfI/6Ggov+5uLn/urm6/7OytP+urK3/vLu8/8C/wf/Av8H/q6mr/7q5u//Av8H/s7O1/6uqq/+2tbb/rKut/6uqq//Fxcb/wsHE/76+v//Av8H/wL/A/8LBw/+9vL7/wcDC/8LBwv+9vb7/u7q7/6+ur//BwcL/ycnL/7Kxsf+9vL3/ysnL/8LBwv/Av8H/xcXH/7KxtP/Ew8b/wMDC/7Oysv+7ubn/vLu7/8XExP/FxMb/rays/7a0tf/Gxsj/rq2v/5uanP/CwsP/sa+w/6Kgn/+/vr//vLu8/5aUlf+5ubr/yMjJ/6+usP+pqKr/v76//7a0tf/BwML/qqmp/6Khov/BwcH/t7a3/5SSk/+5uLn/wcDC/5SSk/+1tLX/s7Kz/66srP+3tbX/srGy/42Ki/+3trf/jImK/7S0tv9wbm//r66v/5+eoP92c3P/m5ma/1xaW/+amZv/T0xN/3d0dv9gXmD/RENF/4OBhP8xMDH/eXZ3/zAuMf9+fX7/////////////////////////////////////////////////////////////////////////////////+vr6/x4cH/+JiIr/fnp6/0RCQ/9hXl//aGdo/1FOTf9QTEv/YV5c/2FeXv9jYWP/ZGJi/25sbP91c3T/enh6/3l3ev+Lior/gH9//4yKi/+OjI3/jIuN/4uJif+VlJT/l5aX/5ORkv+Rj5D/lZOU/5eVlv+WlZf/lpWX/5ybnP+koqP/np6f/5yam/+mpaf/nZud/56cnP+gnp//nJub/6Kgov+cm5z/oJ6e/6emp/+zsbP/o6Ki/5qYmf+dm5z/n52e/6Cen/+gn5//pKOl/6alp/+wr7D/ysnK/6impf+mo6T/n52e/5WTlP+SkZH/lZSV/5uZmf+em53/lJGS/5WTlP+bmZn/mZiZ/4+Njv+XlZb/nZyd/5uam/+cm5z/paOk/5ybnf+Xlpf/npyf/5iXmf+gn6L/lZOW/5aUlv+ZmJj/mZiZ/5KRk/+dm5z/jYyO/56dn/+fnaD/mZia/5uZm/+npqf/pKOk/5qZm/+VlJX/mZia/6mnqv/n5uf/iIeJ/xMSFf8/PkL/NzU5/zUzNv9eXWH/Ojg7/1BPU/80Mzb/NDM2/yspLf8cGyD/IyEk/8/Oz/+1tLX/o6Gj/5iWmP+TkZL/lJKT/5eWl/+GhIT/jYuL/5COj/+TkpP/hYOF/42LjP+Pjo//jYuM/5COjv+LiYr/ioiJ/4uJiv+LiYr/jYuL/5CNjf+Qjo7/iYeG/4mGhf+DgYD/goB//5yamf+LiIf/ioiI/316ev+DgYD/jIqK/3x5eP+PjIz/hYOD/4WDg/+UkpL/hYOD/3d1df+Ni4v/ioiI/3p3d/94dXT/iYeH/358fP95dXP/hIKB/3Rycv+EgYH/fHl7/2xqaf9+fXz/iIaH/21sbP+Bfn7/f319/2poaP+Eg4L/hIKC/3Rxcf95d3b/goCB/2ZkZP97eHj/dHFx/2xpav99e3r/enh5/1hWVv9ta2z/b21u/1xaW/9qaGr/XFlZ/2ZjYv92c3X/WVZV/1lWVv9oZmb/VFFR/2toaf9MSkv/aGVm/1xaW/9APT7/ZWJk/zg2OP9EQUH/TEpK/zw5O/85Nzj/S0dG/zAuL/+GhIT/Liwu/3t6e//////////////////////////////////////////////////////////////////////////////////7+/v/Hx0g/4SChP+UkZH/ZGNk/5mXmf+fnqH/lZSW/6Kgof/EwsL/uLa2/9vb2//S0dH/w8HA/8TDw/+7urv/vLu9/7q5u/+zsrT/rq2u/6akpv+pp6r/nZuc/5WUlf+Xlpf/l5aW/5eWl/+Uk5T/k5KT/5aVl/+Uk5P/kI6Q/5GQkf+VlJX/l5WV/5OSk/+Mi4z/l5aX/5GPkf+TkpP/lJKU/56cnf+bmpv/m5mb/5iXmP/BwMD/rqyt/6Ohov+pp6j/rKqr/6+trv+8u73/vr2//9PS0//Lysz/19fY/+Hg4f/m5ef/5eTm/+Pj5P/l5Ob/4+Li/+Xk5f/m5eb/4eHi/+Pi4//j4uP/4+Lj/+Dg4P/f3uD/39/g/9/e4P/b2tv/2NjZ/9nX2P/h4OH/3t3e/+Hh4f/k4+T/5OPk/+Tj5P/l5OX/5ubn/+fm5//m5uf/5ubn/+fn6P/m5ef/5OTl/+Xl5v/o5+j/6Ojp/+vq6//p6en/6unp/+7u8P9qaWz/GRgc/zQyNv9HRkv/Xl1i/yooKf9QTlH/MS8x/0dERv84Nzn/MC4y/x0cIf8aGR3/ubi5/+np6v/l5eb/5OTm/+Xk5f/j4+T/5ubn/+bl5//n5+f/5+fo/+Pi4//h4eP/4+Pl/+Tk5f/m5eb/5+fo/+Xk5f/j4uP/5eXm/+Xl5//m5uf/2dna/+Hg4f/k4+X/4uHj/93c3f/i4eL/4eDh/9fW1v/j4uP/3Nzc/97e3v/f39//4+Lj/8nIyP/h4eH/1dXV/+Dg4f/j4uP/5OPk/9DP0P/h4OH/5OTl/+Df3//DwcH/5OTk/9bV1f/FwsL/3t7e/9DOzf/e3t7/5OPk/6ajo//X19f/4+Pj/9HPzv/g4OD/1tXU/9XU1P/i4uP/3t3d/9LQ0P/T0tP/4+Hh/83KyP/i4uL/tbKw/8zJyf/k5OT/2NfY/4+Njv/Z2Nj/z87P/6mnqP/U0tL/lZOT/7e1tv/f39//oZ+f/6Ohof/HxsX/nJqa/9PR0v95dnb/vr29/7q5uf9qZ2n/ube4/0dFRP+ysLD/YFxd/2BdXv+Ni4v/NTM1/4qIif8wLzL/e3p6//////////////////////////////////////////////////////////////////////////////////v7+/8fHiD/hIKE/4B9ff9KSUr/ZWNj/29tbv9QTU3/TEpK/2toaP90cXH/bWpr/4uKi/+Eg4T/iomL/5aVl/+qqav/p6ap/7OytP+1tLX/xsXF/9PS1P/R0dH/2tnZ/9TT0//l5OX/7Ovr/+zq6//t7e3/6urq/+Xj5f/q6en/6ejp/+Xk5f/n5ub/4uHh/9/e3v/o5+j/5uXm/+no6f/q6er/7ezt/+3s7f/q6er/6Ofo/+jo6f/c29z/5OPj/97d3v/o5+f/4eDh/+vq6//a2dr/y8rM/7Cvsf+2tbb/tLO2/7W1t/+6urz/qKep/6qpq/+gn6H/q6ms/7Wztv+op6n/o6Kk/6emqP+op6n/paSm/6akpv+mpaf/rayv/6+usP+ysbL/sbCx/6+urv+pp6n/sbCx/6mnqv+rqqz/paSl/6Wkpf+ura//srGy/62trv+ioaP/srCy/6upq/+ko6X/rayu/7m4uv+4t7n/wL/B/7Kxsv++vr//5ubn/2dmaP8dGx//Xlxe/1xbX/8zMDL/aGZo/z8+Qf9LSEz/OTY5/zEvMv9BP0L/HRwg/xkXHP+0tLX/x8bI/6qprf+lpKb/n52g/5qYm/+mpKf/nZuf/7Cvsf+op6r/o6Gi/6CfoP+jo6X/lZSX/6Khov+sqqz/nJqc/52bnf+enZ//np2e/7SytP+goKH/m5mb/6imp/+op6j/nJqc/5ybnP+dm53/mZiZ/5aVl/+ampv/mJeY/5SSk/+enJ7/lpSW/5uam/+gnp//lpSW/5yam/+dm5v/oaCi/5eVl/+amJr/mJeZ/56cnv+Ni4z/n52f/5GPkf+CgIH/kZCR/4eGiP+JiIn/jouN/4F/gf+TkZL/hoKD/46Mjf+dm53/jIuN/21rbf+Ni47/iYiJ/399fv9wbW7/hIOE/3d0df+Qjo//f31//2BdX/+DgYP/hYKD/1xZWv+HhIf/jIqM/2VjY/+EgoL/cG5u/19cXP+Bf4L/amZm/2JfX/95d3j/WVVV/4aEhv9YVlf/WFVW/3Bvcf9QTU//X1tc/0hFRf9HRUX/PTs7/2hlZf8sKyz/f3x8/zEvMv+BgIH/////////////////////////////////////////////////////////////////////////////////+/v7/yEfIv+CgYT/mJaX/1lXWv92dHT/hIGC/21rav9nZGL/iYeH/5eVlv+LiYr/hYOD/42LjP+CgIL/fHt8/4KBgv+Fg4X/ioiJ/46Njv+Pjo//k5GT/42Mjf+Uk5X/k5KV/5STlv+Uk5b/k5KU/5WUlf+hoKP/paSm/7e2t/+hoKL/n5+i/4+OkP+qqqz/nJue/5qZm/+NjI//m5qd/6Ggo/+dnJ//1tXX/8nIy/+lpaf/np2f/6KhpP+ysbT/sK+y/56dnv+joqP/o6Kl/66tsP+xsbP/vby9/8LCxP+1tbb/raut/66tsP+joqT/vr3A/7q5u/+ysbP/qKep/6+usP+3trj/oaCi/6qpq/+2tbf/qqmq/6Wkp/+enZ//qKip/66tr/+rqqz/tbO1/66srv+wr6//wL6//7W0tf+sqq3/s7Kz/62srv+urbD/rq2v/7Kwsv+wrrD/s7K0/6emqP+1tLb/sbCx/6upqv+zsrT/vby+/83Mz//e3d7/g4KF/xkYHf8+PD7/QkBC/3Bvcv9DQkT/U1JU/z07Pv84Njn/Ojk9/ycmKv8aGB3/Hx4h/8HAwv/BwMP/sK+y/66tsP+rq63/rKut/6qpq/+rqqz/qqmr/7Cvsf+xsLL/sbCy/6+tsP+2tbf/sLCx/6elpv+rqqz/qaep/6SjpP+ioKL/o6Kl/6Kgov+lo6T/p6Wm/6yrrP+Ylpr/kI+R/6Wkpv+joqT/jYyO/5eWmf+Rj5H/mpiZ/56cnv+WlZb/pqWm/4yKi/+Zl5f/lZOT/5ORkv+Uk5T/pqSm/5qZm/+Qj5L/lZOV/5STlf+Ihoj/ioiK/46Njv9/fX7/hYSF/4iHiP+OjY3/lZOV/3RydP+CgIH/e3l6/4GAgP+HhYb/dXN0/317fP+Fg4T/h4WG/3t5e/98env/i4qK/3p4ef+Ni4z/cW9w/21qa/+bmZn/hoSE/1VTVP+Mior/l5WU/3RwcP+MiYn/bmtr/3Nwcf+hn5//a2hn/4B9e/95dnP/X11c/4mHhv9PTU3/gX59/2RhYP9PS0r/eXZ2/z48PP9RTk//bmxu/zAvMf+DgYL/MC4w/318ff/////////////////////////////////////////////////////////////////////////////////8/Pz/IB4h/4KBhP+Ylpj/VVNV/4F/gP+PjY7/fnx9/2hmZ/+kpKX/rayu/7++wf/Dw8T/y8vM/8/P0P/Q0NH/1tXW/9nZ2v/Y2Nn/4eDh/+Hg4f/i4uP/4+Lj/+Pj5P/j4+T/5OTm/+Pj5f/h4eP/4eDh/+Dg4f/f39//5OPk/+Li4v/k4+P/5OPj/+Tj5P/l5OT/5eTk/+Pi4//j4uL/5eTl/+bl5f/u7e3/6unq/+Tk5P/k4+P/6Ofn/+vq6v/r6ur/5uXl/+jn5//m5eb/5ubm/+bm5v/n5uf/6unp/+Xk5f/j4uP/5OTl/+Li4//l5eb/4ODh/9/e3//h4OH/5OPk/+Tk5f/h4eH/4eHh/+Dg4P/i4uL/5eXl/+Tk5P/l5OT/5eTl/+Li4v/i4eH/4eDh/+Hh4v/i4uL/397e/97e3v/g4OH/3d3d/+Dg4f/f3uD/3t3e/9bW1v/f3t7/3t7f/9/e3//i4eL/4eHh/+Li4v/j4+T/5+fn/+zs7P/BwcL/Gxof/ysqMP9TUlX/SkhL/29tb/88Oz7/QUBD/zc2O/81Mzf/NTQ4/xgXHP83Njn/6Ofp/+Pi5P/f3t//29rb/9nZ2f/X1tf/2tnZ/9ra2v/X19j/1tXW/8vKy//Kycr/0M/Q/9jY2f/Y2Nn/2NjY/9XU1f/T0tP/0tHS/9rZ2v/c293/3dzc/9rZ2v/X1tf/3t3d/93c3f/X1tf/1NPU/9va2//a2dr/3Nzc/9za2//V09T/3t3e/9jY2f/b29z/2dja/9fW1//V1NX/2dna/9va3P/Y19j/3Nvc/93c3f/X19n/2NfZ/9jY2f/X1tf/0dDR/9fX2f/Fw8T/yMfI/8rJyv/CwcL/19bY/9LS1P/Nzc//u7q8/8zLzP/Y19r/0tHT/6+trv/Kycr/zMvN/87Oz/+8u73/zMvM/8/Oz//V1Nb/ycjK/7Oxsv/Kysr/0M/Q/66srv+sqq3/xcTG/5ybnv+pqKr/trW3/4iGif/CwcX/qqmq/5WTlP+7urz/ZWNm/7m4u/+Mi43/j46R/2tpaf+bmZz/VlRW/0lISf97eX3/Liwv/4SChP8xLzL/fXt9//////////////////////////////////////////////////////////////////////////////////z8/P8gHiD/iYeJ/5+dn/9aWVv/b21s/3h1dv9fXVz/VFFR/2VjY/9WVFX/ZmVn/2FgYf9ZV1b/cG5t/25sbP9oZWT/c3Bv/3Nxcf92c3P/dnRz/4J/gP+CgID/mZeY/4iGh/+UkpP/hoSF/46Mjv+UkpT/o6Kk/6Siov+Ylpj/iIaH/5SSlP+fnp//nJqb/6upq/+SkZL/oZ+g/7Oys/+mpab/kY+R/5+dnv+qqar/lJKU/6qoqv+Zl5n/mJeZ/6alpv+PjpD/j46Q/4yLjP+Yl5n/nJuc/6qpqv+dnJ3/2tnZ/6yqqv/Ix8j/rKut/5qZm/+gn6H/rKuu/5ubnf+Yl5r/np2g/8XExv+enJ//rayu/5qZm/+OjY7/kpGU/5GQk/+RkJL/m5qc/66tsP+hoKP/kpCS/4qJi/+QjpD/l5aY/5qYmv+SkJL/o6Kk/5qYmv+ysLH/p6Wn/5aVlv+Ylpf/m5mc/5aVl/+amZv/nZye/5+dn/+ioKH/4uHh/+rq6v9VVFf/FRQa/0VDRf9SUVX/RURH/1BPUv9PTE//Ozk9/zAuMv8ZGBz/FhUZ/5GQkv/g4OD/p6ao/8C+wP+ysbH/s7Gy/5+dnv/FxMT/o6Gj/6SipP+em53/qKao/7m4uf+wr6//m5ma/5qYl/+Vk5L/npyc/6yqqv+Qjo7/kI6P/5WTlP+Uk5P/mpia/5qZm/+LiYz/kI6Q/5GRk/+WlZf/j46P/4mHif+DgYL/hoWG/4iGh/+AfX3/iYeH/42LjP+DgYH/kpCQ/5KRkv+lo6T/gH6A/56cnP+Vk5T/h4WG/4eGh/+LiYr/d3V1/4aEhf93dXb/f319/3p3eP9pZ2f/hIGA/4aEhP9oZmb/cW9w/3l3eP96eHn/bWps/3JwcP9xbm//cW5u/21ra/9dWlv/Y2Bg/2poaf9kYWP/X1xb/29tb/9qaGn/dHJ0/1RRUv9saWn/amho/2NhYv9IRUT/ZWJi/0tJSP9jX1//ZWNj/0RCQv9pZ2f/T0xL/zk1Nf9qZ2f/PDo7/1RSUv82NDX/MS4t/1hVV/82NDX/RkRF/19eX/8uLC3/d3V1/zY0Nv97env/////////////////////////////////////////////////////////////////////////////////+/v7/x8dH/+Eg4T/nJqc/25sb/+GhYb/qaip/4yKi/+Fg4X/t7W3/8LBwv/X19j/09LU/8fGx//NzM3/z87Q/8bFxv/Pzs//19bW/8/Ozv/R0ND/19bX/8fGx/+8u7z/3Nvb/9TT1P/FxMX/09LS/9TT0//X1tf/1dTV/9LR0f/a2dr/1dPU/9bV1v/a2dr/2NjY/9PR0v/T0dL/0tHR/9va2//S0NH/1tXW/9TT1P/Pzs7/19bW/9fW1//Q0ND/19bX/+Tk5P/T0tL/19bW/9/d3v/Y19f/2tnZ/9nX2P/U09T/2NbX/9nX2P/U09T/19bX/9bV1f/g39//3Nrb/9jX2P/X1tb/29ra/9TT0//Y19f/1tXW/9bV1f/d3N3/3Nvb/9va2//d3N3/3t3d/9bV1v/d3Nz/5uXk/9vZ2v/Y19f/2tnZ/9XU1P/X1tf/2NjX/9XU1P/Y19f/397e/93b2//T0tL/09LT/83Mzf/S0dL/y8rK/8/Pz//s6+z/5OTl/8zLzP8tLC//FhUZ/y8uMf9LSk3/Pjw//zc2Of8rKSz/IB4j/xcWGv9cW13/6unq/9DQ0f/Pz9D/0dDR/+Pi4//U09T/zszN/83MzP/W1dX/19bW/9HQ0f/T0tL/09LT/9XU1P/W1db/zMvM/8/Nzf/NzMz/0M/Q/8/Ozv/NzMz/z87P/87Nzv/Lycr/y8rL/8jHx//Kysr/x8bH/8fGx//Hxsb/y8rL/8fGx//GxcX/yMbH/8jGx//Hxsb/x8XG/8jHx//Mysv/ysnJ/8vKy//Ix8j/y8rK/8nIyf/JyMj/ycjI/8vKyv/JyMn/y8rL/8TDxP/CwcH/xsXG/8vKy//Ew8P/vby8/8vJyv/Ly8v/ycjI/8nIyf/NzMz/v76+/8PCw//Kycr/ycjJ/7m4uf++vb3/w8PE/8fHyP+3trb/ubi5/8fGx//Gxcb/vby9/56cnf+0s7T/xsXG/7Szs/+fnJ3/ube4/7W0tP+rqar/vbu8/5yamv+fnZ//s7Kz/4yJiv+Zl5j/b2xu/5mXmP9iX1//kY+Q/2RjZf9fXmD/hYOF/zAvMP+Cf4D/MC0v/3t7fP/////////////////////////////////////////////////////////////////////////////////8/Pz/IR8i/39+gP+gnp//Y2Fi/2tpaf+Rj5D/YF5e/0ZERP96eHn/bmxt/4WEhf+NjI7/iomK/4OBgv+Ni4z/jo2P/4OBgv+Uk5T/l5aX/4eGh/+dm5z/m5mZ/5+dnv+dnJz/oJ+f/6SjpP+fnp//n56f/6moqf+pqKn/npye/6qpq/+ioKL/p6ao/7Cvsf+trK7/rq2u/6qnqf+7ubv/ycjJ/7i3uP+4trf/uLa4/7CvsP/EwsT/wsHC/7y7vf++vb7/2dfY/8LCwv/Hxcb/zczM/8C/v//Ixsf/xsTF/7q4uf/Hxsf/x8XG/768vv/Bv8H/ubi6/8zLy//Bv8H/v76//7i3t//Lycr/u7m6/7y6u/+7ubv/rq2u/8PCw/++vb//s7G0/8/P0P/Pzs//xMLD/8rJyv/c29z/wsDB/728vf/BwMH/s7Gz/727vf++vL3/uLa2/8bExP/S0dH/zMvM/8G/wP/FxMT/vLu8/8TDxP+8u7z/wcDC/+vr6//h4OH/8fDx/8jHyf9JSEv/FhUZ/xkXHP8aGR3/GBYa/xcWGP8jISX/f36A/+bm5v/s7Oz/x8bH/8LAwv/CwcP/3Nvb/8TDxP+4t7j/r66v/7q5uv+6ubv/p6ap/7i3uv+pqKn/rq2u/7+9v/+2tbb/sK6w/6+usP+1s7X/rKqs/66tr/+wrrH/trW3/66trf+1s7X/rayt/7SytP+sq6z/rayu/6+trv+1tLX/trW3/7Gwsv+tq6z/raus/66trv+urK//sK+x/7Cvsf+ioaP/oaCj/6Kgo/+joaT/rKut/56dn/+Xlpj/mJeZ/5iXmf+enJ7/n56g/5SUlv+Xlpj/j46P/5uZmv+WlZb/jo2P/5GPkf+KiIr/iYeJ/4yKjP+Qj5H/kY+S/4SDhf+TkpT/kI+S/4qIiv+Pjo//fnx9/4KBg/+Xlpf/gH5//4aEhv+HhYb/lpSX/39+f/91c3b/i4qL/3Bubv+Afn//d3Z2/399fv+UkpP/g4CC/4SDhP9fXF3/i4mK/3Ryc/97eXv/aWdq/0RBQ/9ubHD/QD5B/0NBRP94dnj/NjQ1/4WDg/8zMTP/fHt8//////////////////////////////////////////////////////////////////////////////////39/f8hHyH/fHt9/6akpP9pZ2r/fHt8/5qZmv99e3v/bmxt/5CNjv+DgoP/jYyN/4F/gf+Hhob/iIeI/318fv+FhIb/jo2P/4iHiP+Eg4P/joyM/5GPkP+KiIj/joyN/4+Nj/+OjI3/j42O/5GPkP+WlJb/nJuc/6Gen/+tq6v/tLO0/6Wio/+koaH/qaeo/6Shov+6ubr/np2d/6Ohof+npab/q6qq/6akpf+sqqr/w8PE/7Sys/+2tbb/vbu8/6akpP+0srP/rKqs/7GvsP+6uLn/r62u/66srv+wrrD/pqWm/6qoqf+npqj/q6qr/6+ur//FxMX/qqio/6upqv+sqqv/rKqr/62rq/+5uLn/u7q6/8PBwv/Ix8n/xsTG/6Wjpf+opqn/qKao/6CeoP+npaf/raus/6GfoP+qqKn/p6Wm/6imqP+opqb/pqSk/62rq/+wrq//t7W1/8LBwv+3tbf/uLe5/7y7vP+3tbf/09HT/7i2uP+vra7/y8nK/+Hg4f/Av8D/1tXW/+bl5v+3trj/hIOG/21scP9ycHP/j46Q/9DQ0P/U09X/t7W2/7i3uP+sq6z/rayt/7CvsP+qqar/q6mr/728vf+lpKb/p6ao/6Oio/+mpKb/sbCx/6imp/+ioKL/m5mb/6Kgov+amZr/j42O/5iWl/+amZr/n52e/5qYmf+Xlpf/lpSV/5iWl/+OjI3/mZaX/5COj/+Rj5H/lpSV/5COkP+SkJL/mZia/42Mjf+Qj5H/k5KU/4uKjP+Ihoj/hoSG/42Ljf+Mi4v/jIqL/4yLjP+Ih4j/f31//399f/+Eg4T/hIOF/4aFh/9+e37/fHp9/358f/9/fYD/fnx+/358fv+AfoD/gX+C/4KBhP9/foD/fHp8/318ff+Bf4H/fHt9/3x7ff9/fX//cnBy/25sbv9wb3D/cXBx/3t6ff90cnX/b21v/2VkZf9qaGr/bWxu/2RiZf9jYmT/ZWNl/2dlaP9lZGb/WVdZ/2NgYv9aWFj/XFpb/19cXf9IRkb/WlhY/1xZWv9JR0f/R0RC/2RiY/9IRkf/UE1P/2lnaP8xLzD/g4GE/zQxNP98e3z//////////////////////////////////////////////////////////////////////////////////Pz8/yAfIf9+fH//pqWm/25tb/+Bf4D/nZub/3Z0df9iYGL/rayu/6akpv/Qz9H/19bZ/9jX2P/a2tv/3dze/9/e3//h4eL/4ODh/+Df3//l5eX/5+bm/+fm5v/n5+f/6Ojo/+fm5v/n5uf/6unp/+vq6v/q6en/6ejo/+np6f/p6en/6ejo/+no6P/q6en/6ejo/+rq6v/q6Oj/6unp/+jn5//r6ur/6ejo/+vq6v/r6en/6enp/+vq6v/q6er/6enp/+rp6f/o5+j/6Ojo/+jn5//o5+j/5+bm/+fm5v/p6en/6unp/+rq6v/r6+v/6+vr/+vq6v/o5+f/6Ofn/+jn5//o5+f/5+bn/+fm5//n5uf/5+fn/+bm5v/m5ub/5eXl/+fm5//n5ub/5uXm/+fn6P/n5+j/5+fo/+fm5//m5eX/6Obn/+fm5//p5+f/7Ovr/+fm5v/o5+j/5+fn/+jn6P/o5+j/6Ofn/+no6P/q6ur/6enp/+no6f/o5+j/6ejp/+np6f/q6er/6enq/+np6v/s7O3/6unq/+7t7v/p6en/5+bo/+jn6f/p6On/6Ofo/+fm5//n5uf/5uXn/+bl5f/m5eX/5uXm/+bl5f/m5eb/5eTl/+Tk5P/m5eb/5uXl/+Xk5f/l5OX/5uTk/+rp6f/q6en/7ezt/+vp6f/t7Oz/7ezs/+vq6//n5+f/6ejp/+Xk5P/o5+f/5+bn/+bm5v/l5OT/5eTl/+Lh4f/i4eH/4+Li/+Df4P/h4OH/4uLi/+Hg4P/g39//3dzc/+Hg4f/i4uP/39/f/+Hh4v/g4OH/397f/+Lh4v/i4eL/4N/g/9XU1f/e3d7/4eDh/9/f4P/a2Nn/397e/+Df4P/c2tv/3Nvd/9zb3P/d3N3/29rb/9rZ2f/b2tv/2dfY/9rZ2f/a2dn/2NbX/9jW1//W1NX/2tna/9zb3P/g3+D/2dnZ/9jX2P/Z2dr/2Nja/9nX2f/U09P/1NPU/8bFxv/Qz9D/09LT/7Kwsv+8urr/19bX/8vKyv+npaX/v72+/7Oys/9TUVH/rKuu/1JRUv9jYWP/nZud/zUyNP+Ni4z/LSst/319fv/////////////////////////////////////////////////////////////////////////////////8/Pz/IR8h/358f/+koqP/a2ps/3Jwcf+Ylpb/a2lq/1xaW/98env/b25w/4GAg/+PjpD/jYuO/42Mjv+SkZT/lJKV/5aWl/+WlZf/mJaX/52bnP+gnp//n52e/5yanP+mpaf/nJqb/6Cen/+ysLD/uLa3/7Kxs/+hn6H/qaeo/6qoqv+joaL/pqSm/66srf+qqKr/uLe4/62rrP+2tLX/p6Sm/7i3t/+ura3/u7m6/7WztP+urK3/vLq8/7a1tv+3trf/trW1/6emp/+rqqv/qaip/6uqq/+ko6X/o6Gj/7Oxsv+1tLX/urm6/8PCw//Ew8T/u7m7/6imp/+tq6z/q6qs/6yrrv+pqKn/p6an/6Wkpf+op6n/pqWm/6Kho/+hoKH/qKep/6inqf+opqj/rq2w/66tr/+sq63/rayu/6uqrP+xsLL/r66w/7Gwsf/DwcL/qKeo/66tsP+op6n/r66v/66tr/+qqKr/r66w/7y6vf+zsrX/tLK1/6yrrf+1tLb/tLO0/7q6vP/AwML/vLu+/9jX2P/DwsT/2djZ/8PCxP+2tLf/tbS2/7q5vP+1tLb/rKut/6uqq/+qqav/p6an/6Sjpv+lpKb/o6Oj/6SjpP+ioaL/np2e/6Khov+ko6X/o6Gj/6Oho/+op6j/wsHD/8C/wf/X19j/wsDB/9DP0P/Pzs//xcTG/7Kxsf+6uLr/q6qs/7i3t/+0s7T/raut/6Wkpf+qqKr/paOk/6inp/+npqb/qqmq/6emqP+lo6X/paSl/6alp/+lo6T/q6qr/6emp/+jo6P/pKOk/6alp/+ko6X/oaCi/6Ghov+koqT/np2e/6Cfof+amZv/nJuc/5ycnP+cm53/nJuc/5ubnP+dnJ7/n56g/6Kho/+bmpz/nZye/5uanf+Yl5n/m5qb/5ybnf+ZmJn/mZiZ/5mYmv+WlZf/lJKU/5aVlv+Yl5j/mZia/4yKjP+ZmJr/mpmb/5qZnP+YmJr/lZSX/5OSlP+CgYP/f36B/4OChP9/foD/c3Jz/3Jwcv9mZGX/TEpK/zYzMv9lYmP/RkNE/05LTP97d3j/MjAx/4iGiP8qKCv/fXx9//////////////////////////////////////////////////////////////////////////////////z8/P8iICP/f31//6inqf93dnf/fXx8/6alpf+LiYv/b21v/6qoqP94dnb/j42N/4+Nj/+Ni43/lJOV/5STlP+Uk5X/nZuc/5mYmf+Yl5j/mJeY/5mXl/+lpKT/paOj/6akpf+opqf/o6Kj/62rrP+sqqv/q6mr/6Wkpf+npqf/pqSm/6alpv+mpKb/ubi6/7y6u//S0dP/uLi6/8TDxv+7urv/u7m5/7GvsP+zsbL/tLO1/8XExP+wr6//rKus/7CusP+trK7/w8PF/6+usP+goKH/q6qs/728vf+3trj/rayu/6qpq/+trK//0dDR/6yrrP+mpaf/qqmq/6akpv+npqb/r66w/6moqf+pqKr/pqSm/8LBw/+zsrP/r66x/8rJy/+xsLL/uLe5/7Cvsv/S0dL/rKuu/9HQ0v++vL//pqWm/8XExv+pqKn/qaiq/7OztP+pqKv/y8rN/7u6vP+qqar/urm8/8rJzP+xsLL/qqiq/6inqf+op6r/rKut/7W0tv+lpKf/q6qs/6Wkpv+rqqv/p6an/6inqf+lpKX/qqmr/62tr/+mpqj/q6qs/7a1uP+sqqz/p6ao/7y7vf+trK7/srGz/6yrrf+ura//nZyd/6Kho/+op6n/qKep/6moqv++vb//qams/9DP0f+mpab/q6qr/6akp/+ioaP/oZ+h/6Wkpf+bmZv/oqCi/6OipP+npaf/o6Ki/6GfoP+bmpv/p6Wm/5aUlf+Zl5n/k5CR/5aUk/+TkZH/l5WX/4uJi/+QjpD/lZSV/4uJi/+Ni47/i4qM/5iXmP+KiIr/kpGU/5ORlf+RkJL/joyP/5SSlf+TkZP/l5WX/6Ggof+OjI3/lZOV/46Mj/+Ylpj/iIaI/4yKi/+Zl5j/i4mL/5ORk/+GhYf/f36B/4aFiP+Egob/g4GD/4GAgv+Fg4b/g4GD/4SDhv9/foH/hYSF/4B/gP+Afn//eXd5/3V0dv9zcXP/c3Fz/3Vzdf9raWz/aGZo/3BucP9wbnH/ZmRm/2tqa/9vbW7/cW9v/399fv9vbW3/SEVF/46Mj/9UU1b/XVte/5ORk/83Njf/joyN/y0qLf+Af4D//////////////////////////////////////////////////////////////////////////////////Pz8/yQjJf+Eg4X/q6mr/3Z1d/+BgIH/qaep/358ff9nZWj/r66v/728vP/Qz9H/0dDS/9XU1f/Ozc7/1dTW/9LR0f/V1dX/1dXW/9nY2f/Y19j/19bX/9TS0//V1NT/19XW/8LBwv/JyMn/zczN/9LR0f/Lycr/1NLT/9XU1P/RztD/19bX/9HQ0v/V09X/2NfX/+Lh4v/a2tv/2djZ/93c3f/c2tv/2NbX/9rY2f/a2dr/3dze/9zb3P/Y19j/1dTW/9bV1v/V1NX/3Nrb/93b3P/g3+D/4N/g/9bV1f/Ix8j/yMfI/9LR0v/f3d7/z87P/9za2//d3N3/xcTF/727vP/Gxcf/v76//8C/wf/CwcP/zczO/8rJy//MzM7/y8rL/9fW1//Ozc//xcXI/83Mz//T0tT/zMvM/+Hg4v/X1tf/19bY/8XExf/R0dL/1tTW/8bGx//Ix8n/29vd/9bV1//X1tf/2tnb/8fGx//W1db/zMvN/83Mzv/NzM7/2tna/83Mzf/Pzs//0M/R/9HP0f/T0tP/1dXW/9HQ0f/Ozs//0c/R/8vKy//JyMr/0dDR/8TDxP/My8z/1NPU/8jHyf/My83/1dTW/9ra2//V1Nb/1NPU/9fV2P/W1Nb/1tXV/9zb3P/a2dr/2NfY/9XU1f/c293/393f/9PS0//b2dr/3tze/9rZ2v/Y19n/4N/h/9bW1//W1db/19bX/9PS1P/Jycr/3Nvd/9TU1f/Qz8//29ra/93c3f/e3d3/19bX/9bU1f/X1tf/2tna/9va2//U09T/0dDS/9PS1f/S0dL/09HT/9HQ0f/U09T/2NfY/9LQ0v/X1tb/3Nvb/9bU1f/Rz9D/0dDR/9TT1f/FxMb/1NPU/87Nzv/FxMX/xMPF/83Nzv/U09X/y8nL/8/O0P/FxcX/vr2+/8C/wf+/vr//xsXG/728vf++vr//xMPF/8LBwv/Hx8j/xsbH/8rJyf/Qz8//0dDR/8/Oz//NzM3/ube4/8TDxP/My83/ycjJ/8rJy/+xr7L/kY+Q/5COkP9MS0v/l5WY/1JRVP9gX2H/ioiK/zAuMP+Jh4n/MS8w/359fv/////////////////////////////////////////////////////////////////////////////////8/Pz/IyEk/4KBg/+pqar/dnR2/4OChP+sq6z/g4GD/19eX/+Pjo//d3Z2/5STlP+bmpz/paSl/6CeoP+npaf/raut/7Sztf+2tbf/vr2//7m5uv+xr7H/wL/A/7Szs/+3t7j/ubi5/728vf/Kycv/vr2//7m4uf/IyMn/xsXH/769vv/V1NX/29rb/87Nzv+7urv/urq7/8LBw/+9vL3/vb2+/8zLzf+/vr//vby9/7++wP/PztD/4N/g/9HR0v/Kysv/vr2//7m4uv+1tLT/tLOz/7Oys//NzM7/0tLT/8nJyv/My83/z87Q/93c3f/Ozs7/5uXm/+Lh4v/U09T/0tHS/9bV1//My8z/1tXW/+Lh4f/j4uP/5+bn/9LR0v/i4eL/2NbX/9TS1P/U09T/19fY/9vb3P/S0dL/2dja/9jX2f/S0dL/zs3O/8jHyP/S0tP/zs3O/8/O0P/l5OX/1NTV/8XExv/Ozc//4ODh/9fX2P/R0NL/1dTV/+Hg4f/k5OX/2tnb/9XT1f/W1db/29rb/9va2//q6ur/4N/g/9HR0v/X1tf/09LU/9LR0v/b2tv/2tna/8nIyf/Pzs//yMfJ/8bFxv/CwcP/xsXG/8fFxv/FxMX/zczO/7y7vf+9vL3/uLa3/8bFxv+5uLn/t7a3/7i3uP+7urv/vry9/7m3uP+2tbb/zMvM/8TDxP+/vsD/wL/B/8HAwv++vcD/w8LE/7e2uP/ExMX/s7Gz/6WjpP+al5j/qKan/66trv+qqKr/pKOj/6mnqP+npqf/qqmq/6qpqv+rqav/r66v/7CvsP+xsLH/q6mq/7W0tf+1tLX/srGy/66trf+tq6z/sK+w/6upqf+vra7/tLO0/7SztP+7ubv/tbS1/7OytP+0s7T/ubi5/7m3uf+0s7P/wL/A/7a1tv+vrq//rKus/62trv+trK7/oqCi/5uZmv+TkpP/h4aH/4SDhf+Bf4D/e3p7/3p5ev93dXf/dnV2/3p4ev95d3r/bWtu/2dlaf9oZmr/Wllc/11bX/9YVlj/TElL/0I/QP+PjZD/WFda/2NhZP+Ylpj/MS8x/4eEh/80MjT/fn1+//////////////////////////////////////////////////////////////////////////////////z8/P8jIiX/fXx+/6yrrf+CgIP/goGC/7Cur/+EgoP/YmBi/9nY2v+Fg4b/hYOG/3l3ef95eHr/eXh6/3V0dv9xb3H/bGtt/2xqa/9tbG3/bWxt/25tbv9wb3H/bmxt/25sbv9wbm//bm1u/25sbv9ramv/bWts/21rbP9wb3H/cG5w/3BvcP91dHb/eHd5/3Z1d/90c3X/c3Fz/3Nyc/9xcHL/dnR2/3Z1d/9ycXP/dHN0/3BvcP9ycXP/dXR1/3RydP91c3b/dnV2/3Ryc/91dHX/dHJz/3h2d/94d3j/eXh6/3t5ev94d3j/e3p8/3l3ef91dHb/cnBy/3Z0dv92c3X/c3Jz/3Rzc/90c3P/c3Jy/29tb/9wb3H/bGts/2poaf9raWv/a2ps/2tqa/9samz/bmxu/2tqbP9ramv/a2lr/2tqa/9ramz/amhp/2hnaP9qaWv/amhp/2hnaP9ubG7/bGps/25tbv9wb3H/bWxu/2xrbf9sa2z/aWdo/2lnaP9oZ2j/aGZn/2dlZv9paGn/aGZm/2tpav9qaWr/aWdp/2lnaf9sa2z/bGpr/2ppav9ramv/aWhp/2tpav9qaGr/bGpr/2xqa/9raWr/a2lq/2poav9ubG7/bGps/2lnaP9oZmf/Z2Vm/2hmZ/9lY2T/ZmRk/2dlZf9mZGX/ZmRl/2NiY/9hYGH/ZGJj/15cXv9ZWFn/XFpc/15cXv9eXF7/YF5g/19dX/9eXV//YF5f/2NhYv9dXF3/W1lb/1RTVf9UUlT/VlRW/1NRUv9OTU3/T01P/1FPUf9PTU//T01P/09NUP9JSEr/REJF/0NBRP9CQUL/QD4//0RCRP9GREX/REJD/0RCRP9DQUL/QkBC/z48Pf9AP0H/QD9A/z89P/88Ojz/PDo7/z89Pv89Ozz/Pjw9/zw6O/89Ozz/PTs8/zs6O/8+PD7/PTs9/z08Pf9EQkT/Pj0//0A+QP9BQEL/QkFD/0NBRP9CQUL/R0ZI/0ZERv9EQ0b/Tk1O/1FRU/9WVFf/bm1u/7GvsP+urK7/T01O/7Gwsv9ZWFv/Z2Zp/5yanf8zMjP/iIaI/zEvMP99fH7//////////////////////////////////////////////////////////////////////////////////Pz8/yUjJf99fH7/p6ap/4GAgP+DgYL/rKqr/4yKjP9raWz/oJ6g/xsZG/82NTf/NjU4/zQzNv82NDf/Ozk8/zo4PP85ODv/OTg6/zo4O/8+PD7/PTs8/z07Pv8/PUD/Pz5B/0E/Qv9EQkX/REJG/0VER/9IRkn/SEZI/0dFSP9GREf/QkFE/0NCRf9DQUT/RUNG/0hGSv9IRkn/SEdK/0xKTf9LSUv/SEdJ/0xLTf9JR0n/R0VI/0tKTf9KSUr/SkhK/09NUP9OTE7/Tk1Q/0hGSf9MS0//TUxQ/0tJTP9IRkn/TEpN/0pIS/9IRkr/TEtN/01MT/9NTE//T01Q/09NT/9NS03/UE9Q/1FQU/9MSk3/UE9S/1BPU/9OTE//T05R/0pJTP9NTFD/TEtP/01MT/9PTlL/Tk1Q/09NUP9QT1L/UE9S/1BOUf9UUlX/U1JV/1NRVP9TUlX/UU9R/1JRVP9SUVP/U1JU/1JRVP9RT1L/UFBS/1RSVf9TUlT/UlBT/1JQU/9UUlX/UlFT/1FPUf9QTlD/T01Q/1JRVf9RUFP/TkxP/05NUP9NTE7/TUtO/05NUP9QT1H/T05P/1FPUv9SUFP/TEpN/01MT/9OTE//Tk1Q/09NUP9OTU//TUtO/09OUv9QT1L/TkxP/05NUP9LSUz/S0pM/0xLTf9MS07/Tk1Q/01MT/9IR0r/UE9T/1BOUf9NTE//Tk1Q/0pIS/9GRUj/R0ZI/0tKTf9JSEv/SEZK/0ZFSP9FQ0f/RkRI/0ZFSv9DQUX/Q0FG/0JBRP9CQET/QkBD/0NBRf9APkH/QkBF/0NCRv9HRkr/QkFE/0ZFSf9IRkr/QkFE/0JARP9JR0r/Q0JG/0FAQ/9HRkr/SUdJ/0hGSf9HRUj/RURG/0dFSf9DQkX/RURH/0RCRv9FQ0f/REJF/0NBRP9EQ0b/Q0FE/0RCRv9GRUn/R0ZJ/0RDRv9DQUX/REJG/0VESP9CQET/Q0JG/0JBRf9APkL/QD9D/0VDR/9APkH/REJE/0hGSP8wLzP/IB4h/7i4uf9SUVT/rqyt/1VUV/9ramz/mZaX/zc1N/+OjY7/Ly0v/39/gP/////////////////////////////////////////////////////////////////////////////////7+/v/IyEk/399gP+qqaz/gH5//4WEhf+vra7/iIaI/25tb/+DgYT/MjE0/yUkJ/8lJCb/KScq/yYlJ/8oJij/JyUn/yknKf8nJSf/KCYn/yspKv8pJyj/KSco/ykoKf8rKSz/KScq/yopK/8rKSv/Kikr/ysqLP8sKiv/LCos/yknKf8qKCr/KScp/yooKv8rKir/KCYo/yopKv8qKCn/LSst/y0rLP8nJif/Kigp/yopKv8rKSr/Liwu/yspK/8rKiz/MC4w/y0rLf8uLC//LSsu/yopK/8sKy3/Ly0w/ysqLP8wLi//LSst/ywrLf8uLC7/LCss/y4sLv8tLC7/LCst/y0sLf8vLS7/Ly0v/y4sLv8uLS//Ly0w/y4tL/8uLS//Kyks/y4sLv8tLC7/LSww/y4tMP8tLC//MC8x/y8uMP8wLzH/Ly4x/y8uMP8vLS//Ly0v/y4tLv8wLzH/Liwv/y8uMP8vLi//MC8x/y4tL/8tLC7/MC4x/y8tL/8vLjD/Ly0v/zAvMP8wLjD/Ly0v/zEwMv8uLC//MC8x/zAvMf8tKy7/Li0v/y0sLv8tLC3/Li0v/y8tL/8tLC3/Li0w/zAvMf8sKy3/Liwv/y4sLv8sKi3/LSst/y0rLf8sKy7/Li0v/y8uMP8tLC7/Li0u/y0rLf8uLS//Ly4w/y4sLv8uLS//LSwu/y0rL/8vLjH/Ly0w/y4sL/8tKy7/LSwu/ysqLf8qKCn/LCst/y0sLf8uLC7/Li0v/yooK/8rKS3/LCot/yopK/8rKSv/KScq/ykoKv8pJyn/Kykr/yopK/8pKCv/KScq/yooK/8nJif/KSgp/ykoK/8oJyr/KCcp/ykoKv8pJyr/KSgr/ygmKf8qKSr/Kikr/yopK/8oJij/KSco/ykoKf8oJij/KScp/yknKP8oJyn/KSco/yooKv8oJyn/KCcp/yooK/8oJyr/JyYo/yclJ/8pKCv/KScp/yknKf8pJyn/KSgq/ygmKP8nJSf/KSco/yclJ/8qKCn/LCss/1JRVf8wLzL/iIeL/1BPUv+0s7X/XVtf/2xrbP+enZ3/NzQ1/4eFhv8wLjD/gH+A////////////////////////////////////////////+fn5//n5+f/6+vr/+/v7//39/f/8/Pz//Pz8//r5+f8iISP/gX+B/7Gwsv+CgID/hYSE/7GvsP+OjY//b21w/4B/gf8/PUD/FxYY/xkXGv8tKy7/HBsd/xwbHv8ZFxr/LCou/xcWGP8fHSD/HRse/xsaHf8oJir/JCMn/yAfI/8xLzT/IB8i/zQyOP8uLDD/MS8z/ygnLf8wLjP/QUBE/x8dIP85Nzr/Ozk8/yEfIv84Nzr/R0ZJ/yEfIv81NDf/JCIk/0VDR/8qKCr/NDI1/zk4PP8oJin/NTM2/z08P/8wLjH/PDo9/0dFS/8qKC3/PDtA/z48Qf8kIib/QT9E/x8eIf86ODv/NTQ4/yIgJP9MSk//JCIl/ygmKf9APkH/LCos/yUjJf9FQ0f/MjE0/y0sL/9IRkr/HRsd/0tKTP80MjX/Hx0g/z48Qv8qKSv/MS8z/0A+QP8iICL/REJG/zIwMv8sKi7/Tk1R/yIgIf8pKCv/Ojc5/yMhJP9YVln/Ly0w/zU0OP9HRkr/JCMn/zc1Ov8vLTD/MS8y/zUzOP9CQUX/IiAj/zMxNf8zMDL/Hx0g/z49QP8iISX/JCMn/1RTWP8mJSj/LSsu/0A+Qv81MzX/HBoe/0E/RP84Njr/IiAl/0VESf8hICP/MjAz/zo4O/8jIST/KCYq/y0sMP8gHiL/NzY6/ykoK/8dHB//PTtA/yUkJ/8jISX/PjxA/x8eIf8mJCj/NTQ4/yUjKP8rKS7/Kyks/yUkKP8tKy//ODc8/x4cHv89O0D/IR8h/yAeIf8WFRj/Ozo//yIhI/8oJyr/ODY6/x4dH/8hHyD/OTg7/xsZHf8kIiX/Kykt/xsaHP84Njr/MS8z/x0bHv8+PUL/JiUp/yAeIP8uLDH/IiAl/x4dIf8sKzD/IiEl/xkYGv8mJSn/HRsd/xwaHP8eHB//Kikr/xsaHP8gHyL/Ghgc/yEgI/8dGx//IB8j/ywqLv8qKS3/IiAj/yclKP8dGx7/MzE0/x0bHf8hHyL/HBoc/ysqLf8mJCj/Kikt/xoZG/8lJCf/Gxkb/yMiJf8eHSH/IR8j/09OUP91c3b/WFZY/8LBwv9dW13/cnBx/5iVlP9GQ0X/kY+Q/zIwMv97env///////////////////////////////////////////+hoaH/o6Kj/66trv+6ubn/5ubm/8PCw//T0tL/3dzb/yEfI/9/foH/rq2t/4OBgf+EgoP/qaep/4uKjP9zcnT/fn1//0JAQ/8bGhv/Gxkb/xsaHP8bGRv/JiUo/xwbHf8tKy3/Ghkb/x8dH/8fHR//Hhwf/xsaHv8hHyP/IiAj/x0cIP8kIyb/IyIl/xgWGf8oJyv/HRse/yIgI/8bGhz/Ly4y/yQjJf8dGx7/Kyou/x8eIf8jIST/Kiot/x4cH/8uLTP/Hhwf/ygnK/8pKCv/Hx0g/zQzOP8qKCv/MC80/zU0OP8eHSD/QT9F/yooLP8hICP/ODc8/ykoLP8eHB//PTxB/yUjJ/8mJCf/OTg7/x0cH/82NTn/JyUp/x4cH/8zMjb/Kyot/x8dH/8vLjL/Ly4x/xwaHP9KSk//Hhwg/ywrLv82NTr/FxYZ/zAuNP8jIib/Hhwf/zg3O/8hHyL/Pj1B/x0bH/8qKCz/NzY6/yAfIv82NDn/MjE1/xoZGv89O0D/NTQ4/xoYG/9IR03/Gxod/0NCRf8rKi3/IiEk/zw7P/8cGh3/OTg8/xsZHP9EQ0j/IiAj/ywqLv88Oz//Hhwf/z8+Q/81NDj/Gxkb/zY0OP87Oj3/Ghgb/zMyNv8uLTH/Gxod/0FARf82NTj/HBob/zQzN/8wLzP/Hh0h/0xLUf8iISX/Liwx/0lITf8cGx3/JyYp/0pJTv8YFxr/SEdM/y4tMv8eHCD/UlFW/yAfI/8iICT/QUBF/yEgI/8fHiD/U1FW/yAfIv8dGx7/RkVI/z08P/8XFhj/Pj1A/0lITP8ZFxr/MzI2/0E/RP8WFRf/QkFF/zMxNf8ZFxn/TUxQ/yMiJf8qKCz/RkVJ/xUTFv8uLDD/TEtQ/xYVGf82NTr/SEdM/xgXGv8vLjP/QkFG/xYUF/9DQUX/MTAz/yAfIv8/PkH/JiQp/yEgIv9MS0//IB4h/zg3O/8qKS3/HBse/05NUf8fHiD/NTQ4/yYkJ/8rKSz/IyEk/zg3O/8iICP/MS8z/x8dIf9AP0X/HRsf/zg2O/8bGhz/Ojo+/xsZHv8cGh7/TEpO/3Bwc/9bWlz/vr2//1pZXP9ubG3/jYuL/z06O/+Vk5T/LSsu/3p5e/////////////////////////////////////////////39/f/9/f3////////////////////////////9/f3/JSQm/4OChP+vra7/hYOE/4WEhf+wr7D/kI+Q/318f/9/foD/PTs//x8eIf8bGRz/JiQo/xgWGP8fHiH/Gxkc/y0sMf8pKCv/KSgs/yEgI/89PD//Hx0h/y8uMv83NTf/Gxkc/zAuMv81MzT/FxYY/z8+QP8lIyX/Kykr/x4cHv9CQEP/LCos/xwbHv83NTj/IyEj/yIhI/81Mzb/HBod/zU0N/8hHyL/LSwv/zg2OP8ZGBv/MC8y/zIwM/8kIiX/OTc5/xoZG/83Njf/LSst/yEfIv86ODn/ODY4/xoZG/82NDf/MzE0/xkYGv9FQ0X/JiUo/ycmKP8+PT//GRca/zw6PP8tKy3/IR8h/yYkJ/9AP0P/GBcZ/zIxM/8sKi3/IB4h/zw6Pf8cGx7/JiUn/y4tMP8cGx7/NDI0/yYkKP8uLS//KCcq/xwaHP8xLzL/JCMm/yQiJP8wLjH/Hhwf/x4dIP8yMDT/HBod/ysqLf8mJCj/JiQn/y8uMf8fHiL/Li0w/yYlKP8tKy3/HRsd/ykoKv8yMDT/Hx4h/zc1N/8lIyb/LCot/z8+Qf8dGx//Ly0w/0A+QP8ZFxn/KSgr/zY0OP8bGh3/JyYo/zw6PP8cGhv/IiAi/zw7Pf8YFhr/Ly4y/ygnK/8XFRn/OTg7/yUkJv8dHB//Ozo+/xUUF/8mJSj/LCsv/xcWGf81NDf/Kigr/x0cH/81NDb/JyUo/xgWGf84Njn/IiEk/xsZHP8mJCf/Ojg6/x4cH/8hICP/ODY6/ycmKv8eHSH/MjE0/xkYG/8pKCr/LCsu/xwbHv8tKy7/IB8i/xsaHf84Njj/HRsf/xsZHf8yMTX/IB8j/xsaHv81NDf/IB8j/xgXG/8vLjH/HBsf/xoZHP8rKi7/Gxkd/yQjJv8hICP/GBca/y0sLv8cGx7/Hh0h/yYlKf8WFRn/KCYq/xsaHv8ZGBz/Hh0f/xoZG/8WFRf/IiEk/xgWGf8hICL/GBca/x8eIf8YFhn/HRwe/xQTFv8aGBz/FxYa/xkYGv9SUFX/cG5y/1dWWP/FxMX/Wllc/3Z1dv+bmJj/Ozk7/4yKjP8sKi3/e3p7/////////////////////////////////////////////v7+//7+/f////////////////////////////39/f8lJCb/gX+B/7Gwsv+Fg4P/hoSE/7a1tv+UkpP/goCD/39+f/9APkL/Hhwf/xoYG/8jIib/IR8i/zg2Ov8iICL/PDtA/xgXGf8tLDL/NTM3/yAfIf9DQkf/IB4i/ywrMP9VVFr/PTs9/yclKP9nZWv/NDI0/zc1OP9YV1v/VlVa/z07Pf83Njv/amlv/y8tMf9HRkr/X15h/z07P/9bWV3/IiEk/2tqcv9HRUn/MS8y/3BvdP9IR0r/RENI/2NiZv8mJCf/dXR3/zw7Pf85ODv/enl+/zk3Ov8tLC//bmxw/ygnKf89Oz//Z2Zq/yAeIP9WVFf/WVhc/yYkJv90c3X/LSst/z07P/9bWV3/MzI0/zQzN/9cW1//JSMm/1dVV/9HRUf/IB4h/2hmav8uLC3/MzE0/2xqbf8gHR7/NjQ4/0E/Q/9HRUj/YV9i/yQiJP9jYmX/SUdJ/zQyNf9sa3D/MjA0/0JBRf9xb3P/LCot/1BPU/9LSUz/LSwv/2FfY/8dGx3/TUxP/0JAQv82NTf/S0lM/y0sL/9kYmX/Hx0f/1tZXf8wLi//Hhwe/2Vkaf8rKi3/JyUo/2VkaP89Oz7/Kyot/3V0eP8vLC7/NjQ3/2xrb/9OTU7/JiQn/3h3e/83NTn/Pz1B/3l3fP8fHiD/UE5S/21rcP8cGx//Z2Zr/0dGSf8hICT/eXh9/xoZHP9APkL/bGps/yUiJf84Nzv/gYCE/ycmKP84Njn/gH+C/xoYGv8nJij/fHt+/zc1Of8cGh3/ZWRn/0hGSf8aGBz/ZGNp/y8tMf8qKSz/goCD/y0rLv9AP0P/WVhd/xYUFv9iYWX/W1ld/xgXGv9paGz/SEdK/yAeIf9ta27/Q0JF/xsaHf9oZ2v/Pj1B/yspLv9vbXL/Kykt/zQzN/9wb3P/GBcZ/0ZFSf9APkD/MzI2/1xaXf8eHB//Pj1D/0FARP8bGh7/RkRI/ygmKf86OT7/IR8g/y4tMf8iISP/NTQ4/xgWGf8zMTb/Hx4g/zIwNP8dHCD/Ghkc/1FPVP9ycXX/XFpd/7+/wP9lZGf/d3V3/4+Njv8+Oz3/k5GS/zIwM/97enz//////////////////////////////////////////////////////////////////////////////////f39/yYlJ/+CgIH/sbCy/4aFhf+GhYb/tbS1/4+Oj/+AfoH/gYCC/0RCRf8ZGBv/FxUY/xoZG/8WFBb/Gxkc/xYUFv8aGBv/IR8j/xcWGP8eHB//GBcZ/yAdIP8hICP/GBYZ/xcVFv8aGBr/FRMV/xsZG/8ZGBn/Ghkb/xwaHP8cGhv/GRgZ/xcVF/8VFBb/JSQo/xcWGf8iICT/KCYq/xgXGf88O0D/FhUY/xwbH/8vLTP/FRMW/yoqLf8nJir/Gxkc/zc2PP8ZFxr/Li0w/yQjJf8hHyL/Gxkb/zMxNf8YFxr/Ojg+/yQjJ/8XFRf/Ozo+/xsZG/8gHyL/Ly4y/xgXGf82NTr/Hh0g/xoYGf81NDj/IiEj/xUUFf87OT//IB8h/ygmKf9IRkv/FxUX/zk4O/8nJSj/KCcq/z89Q/8oJyr/LCsu/zQyNv8YFhf/OTg8/yAeIf8oJir/RENH/xgXGP88Oz//Kyov/xoZG/8+PUH/Hx0g/z48QP8+PED/HRse/zQyN/8mJSj/QD9C/01LTv8oJyn/QD5C/xoYG/8/PkP/JSQm/zk4O/83NTr/FxUX/zc1Ov8xMTb/FBIT/zY1OP8rKi//Hhwe/y4sMf8gHiH/GRcZ/ycmKv85ODz/FRMW/z08Qf8sKzD/FBMW/01MUP8kIyX/GBcZ/0ZFSf8hICT/Hhwg/0RDSP8cGhv/NzY8/yopLP8XFhj/TUtR/x8eI/8ZGBz/Pz5D/yclKv8WFRf/Q0FF/zQzNv8VExX/PDs//zk5Pf8YFxn/Li0x/0FBRf8ZFxr/Ly4z/zw7QP8VFBb/Pz5D/yAfIv8jISX/VlVa/ygnK/8nJSj/VFRY/x8eIf8hICP/S0pQ/yQiJf8eHSH/SklP/xgXGv8pKCz/QD9D/xUUF/88OkD/MTAz/xcVGf8+PUH/Hhwg/yclKf86OD3/FhQW/zg3PP8vLjP/Ghgc/zc2PP8gHiH/ISAk/zY1O/8bGRz/LCov/xoZHf8vLjL/FxYZ/zAvM/8aGBv/KCcr/xwbHv8cGh3/VlVa/3Z1ev9kY2T/u7q8/1hXWf9xcHH/mpiZ/zY1N/+TkpP/MjA0/3x8ff/////////////////////////////////////////////////////////////////////////////////9/f3/JyUo/4SCg/+xsLH/hoSD/4SCg/+3trj/k5GS/3p3ef+Bf4H/QT9C/yIgJP8dGx//JyYp/x0bHv8oJyn/GxkZ/0ZESP8cGx3/NTQ5/yAeIv9LSk//KCcq/z08QP9TUVT/HRse/1VUW/9DQUb/Q0FF/yMhJP9CQEX/PDo8/y8sMP9ZWFz/XVtc/xsZG/9QTlD/PDo9/yYkJ/9VU1T/Kykr/0lISv9KSEv/IB8j/19dYf9IRkn/IyIl/2FfYv8gHyH/XVtf/zIwMv8rKS3/XFpb/z89QP8pJyr/RURH/z07P/8pKCz/WVda/xkXGv8+PD//Q0FC/yAeIv9OTVH/MS8y/zg3O/9ZV1r/HBoc/zUzNv9NS0z/IB8i/y4sL/9RT1H/Gxoc/z08P/8uLC//JiQm/0E/Qv8bGRv/Ojg7/zs6Pf8dGx3/REJE/yIhI/8+PD7/Pz0//xsaHf9EQ0b/Kigr/ywqLf9APkH/FxUY/zs6Pf8yMDL/HBsd/09NT/8vLS7/JyUo/0dGS/8cGxz/Liwu/x8dH/8vLjD/Pjw//yIhJP9APkH/Hx4h/1FPUf8dHB7/Kyks/0hGSf8fHSH/Kyks/1xaXP8kIiT/Hx0g/2NiZf8qKCr/HRwf/2JgY/8fHSD/LCsv/1ZUVv8cGx//Pz1A/0lHSP8bGRv/Pjw//0lISf8aGRz/Tk1O/y8uMf8gHiL/TUtP/xwaHv8xLzL/NzY5/xsaHv86ODv/Ozk7/ygmKf8kIiT/QT9A/xwaHf8mJCf/T01P/x4dIP8aGRz/TEpM/yEgI/8eHCD/TUtO/x0cH/88Oz3/Ojg8/xoZHP9DQkX/JiQn/x4cH/8/PT//IiEk/xkXGv9DQUT/MS8x/xcVGP8+PED/KCYp/xkYG/9JR0n/IR8i/yQjJv9APkH/HBse/zMyNP8tKy7/Hx4i/0A/Qv8cGh7/Kigt/zs5PP8VFBj/MzE2/yUjJf8XFhr/NjU5/xgXGv8tLDD/Hhwe/y0sMf8XFhj/JyYq/xcWGP8cGx3/IB4i/xsaHf9YV1v/dHR4/2BeX/+3trf/Xlxg/3Jxc/+Qj5D/Ozk8/4+Njv8wLjL/fXx+//////////////////////////////////////////////////////////////////////////////////39/f8mJCb/hIKE/62srf+Ihob/goCB/7Kxs/+UkpP/f35//4OBg/9EQ0b/HRwf/xoYG/8qKCz/HBod/zQyNv8fHR7/MC4y/yMhI/8hHyH/Ly0x/yEgIv8tLC//NDM3/xoZHP9QT1X/PTxA/zAvNP88Oz//MS80/zk4Pf8wLjP/R0ZM/zw7Pv8mJCf/bm1z/zEvM/88Oj//ZmVq/x4dIP9eXGH/OTg6/x8eIf9ranD/MS8z/1VUWf9lZGn/Liwu/3Vzd/86ODn/PTs//11bX/8rKiz/WFZb/z07QP88O0D/PTxB/1BPUv8hHyP/Z2Zr/zUzN/8oJir/ZWRp/x8eIv9IRkv/WFZZ/yIhJP9ta2//Pj1A/zUzN/9NTFP/NTQ3/yQjJf9MS07/PTw+/zY0OP9bWVv/Kigq/2dlaP86ODv/QkFF/1tZXf8tKy7/TEtQ/zEvM/8mJCj/UVBV/ysrLv9SUVT/VFJU/yooK/9paGv/KCYo/0RCRf9ZV1r/IyIk/zc2Ov9LSk//Liww/09NUv85Nzj/RkRG/zMxNP8wLzH/Z2Vm/ywqLP9ZV1n/JiQm/0hHSf9IRkr/Hx4h/09OUv9GRUj/JyUp/zIwNf9ubXL/KScp/z07P/9ram7/JyUo/zs5Pf9fXWD/KCYo/2RiZv9JR0n/IiAj/2hna/81NDf/MC4w/3h2ef8oJin/REJG/2VjZ/8gHyP/YF5k/zY0OP8hICT/dnV6/y4sMP8tKy3/enh9/zIwM/8jIiX/ZmVo/0xLT/8gHyP/Y2Jn/1BPVP8ZGBz/a2lu/0tKTv8oJin/fn2B/zg2Of8/PkH/fHp+/yMiJv9BQET/YV9k/x4cH/9CQUT/enl9/yMhJf9BP0L/dnV4/yIhI/87Oj//Xl1h/xwaHf9KSU7/S0pQ/yIhJP9sa3D/NzY6/y8uMf9wb3L/LCsv/0tKT/9KSU3/GBcb/1taYP8rKSz/MC80/0xKT/8eHSD/IB8i/z49Qf8ZFxr/MjE2/xYUFv9GRUn/Hhwf/zAvNP8jIiX/IyEk/19eYv9zcnb/Y2Fj/728v/9vbXH/d3Z5/6Khov86ODr/kpGS/zQyNv99fH7//////////////////////////////////////////////////////////////////////////////////f39/yclKP+Bf4L/r66v/4aEhf+Eg4P/wL/A/5WTlP9/fYD/goGD/z49QP8eHSD/Ghkb/yEfIv8aGBr/Hx0f/xcVF/8bGRr/JSMm/yAeIP8eHB//IyEj/xoZHP8mJCj/FhQY/ycmKf8rKiz/Ghkc/ygnKv8cGx//HRsf/xoZHf8cGh7/IB4g/yAfI/8jIiT/Ly0w/x8eIv8kIiT/Li0x/ygmKv8jIiX/ODc8/yUkJ/8lJCf/HRse/yUkKP8nJSr/Ih8g/zo4O/8bGhz/JyUn/y0sL/8gHyL/JiUp/yUkKf8gHyT/JiQn/ycmKv8fHSD/Li0x/xsaHv8gHiH/MTA2/xoZHf8lIyX/IR8j/xwbHv8jIiX/HRsf/yclKP8fHR//IiAj/x4cH/8lJCb/GRga/yEfIf8qKCv/IB8h/ysqLv8ZFxr/IR8i/xgXG/8bGh3/IyEl/xoYHP8hHyL/ISAj/xcVGP8lIyb/IyEl/x8dH/8hHyH/KCcp/yEgIv8gHSD/IB4g/yEfIf8rKS3/HBoc/ywqLf8sKi3/LCkr/zs5PP8gHiD/Ojk7/yUjJf8iICP/Hhwe/x8dH/8mJSj/Gxoc/yEgI/8oJir/Ghkc/yEgIf8dGx7/HRwf/yooKf8hHyL/FxUX/yQiJP8yMTT/HBoc/yooK/8sKy//Gxob/zEvMv8lJCf/Hhwf/zs6Pv8hHyL/Hhwf/ygnK/8ZGBv/Ly4x/zAuM/8bGRv/MC8y/ygmKv8ZGBr/KScq/yYlKv8YFhj/JCIk/xwbIP8XFRn/IR8i/y8tM/8bGhz/JiUo/xsZHP8cGx3/JCMn/xgWGf8fHh//LSsv/xcWGv8pJyv/ISAk/xMSFf8mJSf/LSsw/x0bH/8lIyX/JSQn/xgWGv8fHR//Ly0y/xcWGf8mJSn/Kigt/xkXG/8rKSz/KCYq/xsaHf8tLC//FRQX/yUkJ/8bGh3/Gxkc/xgWGf8bGh7/HBse/xoZHP8WFBb/Hx4h/xgWGP8aGRz/FBIU/yAfIv8aGBv/IiAj/xsZG/8dGx7/XVxh/3Jxdf9jYWL/vby9/2FfYv96eHr/pqWm/zc1Nv+QjpD/NTM2/318fv/////////////////////////////////////////////////////////////////////////////////9/f3/JiQm/4F/gf+tq63/hIKB/4KAgf/CwcL/l5WX/3Rzdf+CgYP/PTs+/yIgI/8fHiH/Pjw+/ygmKf87Oj7/JCIl/1taXv8lJCX/QD9E/0E/Qv8sKy//T01Q/zAvMf9gXmL/Pz09/z07Pv9NS0//LCou/0VDSP88Oj//ODc9/0dFSv80Mzj/R0ZK/zIxNf8vLjL/UE5S/yknK/8mJSn/QD9D/x8eI/8pKC7/NDM4/z89Q/9MS0//RENI/0VESf9APkL/NDE0/4WDh/8/PUL/Ly0y/0VDSf8pKC3/QUBG/0JBRf86OD3/Pj1D/zY1Of8nJir/SEdO/ykoLv8+PUP/NzY8/zg3PP84Njz/Li0x/ykoLv9GRkz/IyEn/0A+Q/8yMTT/ODY7/yEgJf87OT7/LSsx/yMhJv82NTn/Kykv/0RDSP8pKC3/TUtQ/ygmK/8sKzD/MjA2/0FARv8lJCn/NjQ5/zY1Of9GRUr/IyIm/zMzN/8vLjP/LSsx/yMiJv83Njv/Kyot/yEfI/8+PEL/JyUq/y0sMf8lJCj/JiUo/ykoK/8oJin/LCkt/zEwNP87OT3/Pj1A/1hXW/8qJyn/VVNX/zQyNP9iYGP/T01O/zIwNP9wbnP/Kykr/1JPUv9iYGT/RUNF/0hHSv9WU1b/JCIk/2pobP9ZV1v/IB8i/4B/gf9gXmH/JSQm/2lna/9WVFf/U1FU/1NRVf81MzX/VVNV/0hGSv9DQUb/TUxP/2BfY/8qKCr/f32B/1pYWv8rKCz/cG9x/3FwdP8nJSf/a2pt/3JxdP8oJin/e3l9/ysoKv9hYGL/YmFk/xwaHf9sa2z/dHJ0/xoZHP93dnr/dnR4/xgWGP9NTE7/f36A/x0bHf9jYGL/gH+C/yAeIf9oZWj/cG5x/yAfIf95d3n/REJF/yAfIv9gXmD/MjAz/1NRU/9UUlP/NTI1/1hWWf88OTz/Q0JG/1JRVv8rKSz/R0VL/zMxM/8vLjH/IiEl/1taX/8cGhz/ODY8/x8dIP81NDj/IyEj/yEfIf9cW2D/d3d7/2RiYv+/vb7/Z2Vo/3l3eP+opqb/QT9A/5STlP82NTf/enl7//////////////////////////////////////////////////////////////////////////////////39/f8lIyX/iYiJ/62rrf+Miov/hIKD/728vf+enJ3/cW9x/4SDhP88Oj3/Gxod/xkXGv8kIyX/Ghkb/yIgI/8YFhf/LCot/yMhJP8kIiX/Ly4y/zMyN/8kIiT/NzY4/yAfIf8lJCf/HBsf/yYlKP8lJCj/JCMn/yEgJP8gHyL/IiEk/yQiJf8kIiX/IyIm/yMiJf8kIyf/JSQn/yUjJ/8jIib/JCIn/yQjJ/8kIyb/IyIl/yQiJf8jIib/Gxkd/0A/Qv82NTr/HBod/zMyNv8dHCD/IyEm/ygnK/8oJyv/JyYq/ygnKv8nJir/JyYq/yclKv8oJyv/KCYq/ycmKv8nJir/JiYp/ygmKv8nJin/JyYq/ycmK/8oJyv/KCcr/ygnK/8pKCz/KCcr/yYlKf8nJir/KCcq/ygnKv8pKCv/Kigt/yknK/8pKCz/Jycr/ygnLP8oJiv/KScs/ygnK/8oJir/JyYp/yclKf8nJSn/JyYq/ygnKv8oJyv/JiUp/ygnLP8qKS3/Kikt/ykoLP8qKC3/Kigt/yopLv8sKy//LCsv/y0rL/8uLTD/FxQX/ywqL/8fHR//JSMm/zY1Ov8eHB//Q0FG/yopLP8gHiD/VFNX/yIgI/8rKi7/Liwv/yEfIf8wLjL/Liwu/zQyNv8+PUP/JSQo/yMiKP9MS1P/IyEl/ycmK/9OTFP/IyIm/ycmKf8/PkP/KCcr/zUzN/89PEH/JyUn/zo4Pv82NTr/IiAk/0dFS/8qKCv/LCou/0tJT/8iICT/IyEl/0VESv8gHiL/JCIl/zIxNf8fHR//PDtA/yknKv8pJyv/Q0JG/yEgIv8eHB7/VlVb/ygmKv8kIyf/UE9U/ygnKv8bGhz/Wlle/zEwNf8iICP/T09U/ygnKv8dGx7/REJI/yYlKP8gHiD/SUhM/yooK/8hHyL/PTw//x0bH/8qKCv/KCcq/zEwNP8gHyH/NzY7/yEgJP8pJyz/GRca/ywqLv8cGx3/KSgq/xYUF/85ODz/HBse/zk3PP8hHyL/IiEk/1hXXP90c3j/Y2Fi/8TDxP9oZ2n/e3p7/6qpqv88Ojn/lJKU/zc1OP9+fH7//////////////////////////////////////////////////////////////////////////////////f39/yclJ/+Fg4X/sK+w/4uKiv+Eg4T/wcDB/52bnf93dXj/hIKE/z89Qf8hHyP/HBoe/yknK/8iISP/LSwv/xwaHP8uLC//LSsu/ygmKf8wLjL/Q0FG/yAfIf8yMDL/NTM2/yMiJv83Njn/0M/Q/8vLzP/My8z/ysnK/8jHyP/Kycr/y8nL/8zLy//My8z/y8rL/8zLzf/NzM3/ysnK/8rIyv/Kycv/zczO/8rJyv/Hxcf/ysnK/8fFx/9MS03/IB4h/0lITf8xLzL/Liwv/y0sMP+enaD/kI6Q/5OSlP+Mi4z/h4aI/4qJiv+OjI3/j42O/4+Njv+Qjo//joyN/42LjP+OjY7/kI+R/46Njv+Ihof/ioiJ/4uIiv+LiYv/jIqL/42Mjf+OjY//jYuN/42Mjf+OjY7/j46P/5OSk/+TkZP/kY+R/5GQkv+SkZP/kpCT/5COkf+Rj5H/lJOV/5SSlP+PjZD/jYuO/5CPkf+Qj5D/jouN/5CPkf+Uk5X/kpCT/5SSlf+Xlpj/lpSV/5SSlP+TkJL/lJKU/5iXmf+bmZr/m5ma/8nIyf8aFxv/JSMm/zAtMP8gHh7/SUdI/zc1OP88Ojz/WVdX/yIgI/82NDX/TUtN/yclKP8+Oz3/JiQm/zg2OP8rKSv/MS8w/0E/Qf9APkH/HBsg/zw7P/89PEH/Gxkd/z07Pf9RTlH/FxYZ/z8+Qv8zMTX/IB4h/0tJS/83NTf/IB8h/09OUP8oJyn/KScq/1VTV/8jISX/MzE1/1FPU/8lJCj/PDs+/z89QP8kIib/R0VI/yQiI/83Njj/R0RG/x0cHv9OS03/PTs9/x8dH/88Ojz/MzE0/yAfIv87OTv/TkxP/xwbHv8sKi3/TElN/x0cIP85ODr/Q0FE/yAfI/85Nzr/WFZY/x4cH/8uLC//U1FU/xoYHP9CQEH/Kyks/zc1OP8fHSD/S0hL/zEvMf81MzX/MzI0/zg2Of8cGhz/NjQ3/yknKf88Oj7/GRga/zAvMv8cGx3/IyIk/xsZHP8bGRz/XFpf/3Bucf9nZWX/vbu8/2JgY/92dXf/rq2t/zg2N/+UkpP/NDI0/39+gP/////////////////////////////////////////////////////////////////////////////////9/f3/KCYo/4OChP+wr7D/iYiI/4aFhv/DwsP/l5WW/3d1d/+Eg4T/QD5A/x0cH/8aGRv/MjA0/y4tMP8rKi7/Hh0f/1xaX/8kIiT/RkRJ/zIwM/8qKCv/aGZt/zMyNv8oJyr/RURK/zY1Of/Kycv/i4qM/5OSlP+TkpT/kI+Q/5GQkf+SkZP/k5KT/5eWmP+WlZf/mpmc/5ycnv+pqKv/nZye/52cnf+npqf/l5aX/5CPkP+Qj5D/oaCh/15cX/9AP0P/Ozo//yopLP9LSU7/IyIm/9XU1v+vrrH/v77A/7Kxs//Ixsf/tbS1/7Sztv+zsbX/rKut/7e1t/+urbD/sK+x/7Kws/+npqn/qair/6qprP+ysbP/qKeo/6uqrP+8ur3/0M7Q/7y6vv++vb//qqmr/6qpq/+ura//rq2w/7q5u//JyMr/y8rM/7e1t/+6uLr/xcTF/8jHyf/Kycz/sbCx/7u6vP+1tLX/qqmr/66srv+zsrT/q6mr/6yrrP+vrq//q6qs/6akp/+ura//rKqs/66sr/+op6j/p6Wn/6Ggov+fnqH/1NPV/xkYHP8mJSj/MzE1/0NBRf9HRkv/MC0x/1tZXP8wLzH/amlu/2BeYv8lIyb/dnR7/y8tMP9mZWn/Q0FE/2BfZf9WU1f/MS8x/1tZX/+Egof/PDs9/01LT/9hX2L/PTw+/yclKP9mZGz/TUtQ/zc2Ov91c3f/OTc5/0JBQ/97en7/JiQn/1FPVP9ram7/KCYo/1VUWf90c3f/JCIm/2Rjaf9oZmn/MjA2/0ZESf9dXGH/REJF/2JhZf8wLi//Y2Fn/0pITP9DQkr/a2pz/1RSVv8sKy//gH+G/1BPU/8mJCn/ZWRs/1NRVv8kIiX/XFtg/2BfY/8kIiX/XVxf/1hXW/8hHyL/YV9k/0hITP86OTz/bm1x/zEwM/86OT3/ZGJo/1JRVv8rKi3/W1pg/0xLT/8pJyr/U1FX/yopLP9EQkb/IiAk/0FARf8fHR//PTxC/xwaHf84Njz/IiEl/x8dIf9ZWF3/dXR5/2JfYP+/vr//ZGNl/3d2d/+dm5v/Ozk7/52cnf83NTf/e3p7//////////////////////////////////////////////////////////////////////////////////z8/P8mJCb/jYyO/7W0tf+KiYj/goCB/8bFxf+hn6D/eXd4/4SDhP9BPkH/Ghkb/xkYG/8dGx7/GhgZ/yMhIv8XFRf/JSMk/xsaGv8kIyX/Liwu/xkYG/8gHyH/JCMn/xoYG/8gHiL/MzE1/83Mzf+WlZb/oJ6f/6Kgof+qqan/w8HC/7OztP+opqf/uLe4/7Sztf+Yl5j/srGz/6inq/+xsLP/paSn/6alp/+mpaf/n52f/6Sio/+enaD/YF9i/xwaHP9FREn/TEpN/ywqLv8vLjL/0tLT/7++wP/Hxsf/x8bH/8jHyP/NzM7/wMDB/8PCxP/Ix8n/v77A/7++wP/Av8H/ubi5/7y7vP/Hx8j/vLu8/7m5uv/Lys3/z8/Q/8TExv/PztD/ysrL/8zLzv/e3d7/y8rL/9rZ2//T0tP/y8rM/+Dg4f/Kycv/2tna/8jHyP/Z2dr/v7/A/9fW2P/a2tv/wsHB/8TDxf/JyMr/y8rM/8jHyf/S0tP/29rb/9LR0v/CwcL/u7q7/7m5uv+3trf/urm6/7e3uP+xsLH/s7Ky/7Gwsf/W1df/GBYZ/yclKf8pKCv/HBsc/zY0Nv8gHiD/Kigo/zAtMP8bGRv/Ly0v/yYkKP8dGhz/ISAj/xsZG/8dGhv/HBkZ/xwaGv8dHB3/HBod/xoZG/8nJSn/FhUW/yQiJv8cGhz/JiUo/xsaHf8mJSb/IyIl/yUjJP9KR0n/JSMn/ygmKP8mJSn/Gxkc/zo4Of8iISX/FxUY/yIgIv8gHyP/GRgb/yQiI/8XFhn/FxYZ/yUiJP8cGxz/Hhwd/yQiIv8cGxz/HRsc/xgXGP8dGxz/Hx0f/xcWGf8cGh7/JiQm/xsZHf8aGR3/List/xwbH/8XFhn/Ly0u/xoZG/8aGRv/IiAi/xoZHv8bGR7/Kyos/xcWGf8fHSD/JyYp/xgWGv8dGx3/KSco/xcWF/8aGBv/IB8h/xkXGf8fHR//FxUX/yIgI/8YFhn/HRwd/xQTFP8cGx7/FRQW/x0cH/8iICX/Ghkc/1FQVP95eH3/WVdY/8LAwf9lY2b/dHJ0/6qnqP82MzT/mJaX/zg2OP9cXF3/t7a3/7m4uf++vb7/vr6+/8C/wP/CwsL/v7+//8HBwf///////////////////////////////////////Pz8/yYkJ/+Ni43/srGy/5CPj/+GhYb/w8LD/6KgoP+CgYP/hoSG/0A+QP8gHiH/IB4i/ywqLf8tKy//MS8y/x8dIP8+PUP/Pz5B/z89QP8wLjP/bm1x/yMhJP9SUFb/PDo//yMiKP82NDf/4eDh/8nIyv/Kycr/wsHC/8/Nzv/Lysv/2dja/9XU1v/c293/19bX/9/e3//Qz9D/09LT/87Nzv/S0tT/z87P/8/Oz//Lycv/v76+/7a1t/9gX2P/IiAi/zk3O/8yMDT/Ojg8/yQjJv/S0dP/srGz/8PCw//DwsT/vLu9/9LR1P+9vL//u7q+/8HAw/+9vL//wcDC/8LBw/+7u7z/vr3A/8LBw//Ew8X/wL/B/87N0P/S0dT/vLu9/769wP+/vsH/ycnM/83Nz/+9vcD/urm8/87Nz//Av8H/1tXX/8LCxP+9vL//xcXH/8nIyv/Ew8X/x8bI/8zLzv/JyMv/ysrM/7m4uv+9vcD/wcDD/8zMzv/Jycv/1dXW/8nIyv/DwsT/wsHE/8HAwv/Ix8r/wcHD/8HAw/+8u73/rKut/9DP0v8ZFxr/Kigs/zQyNf9UUlT/JyUn/1NQUf9dW17/PDk8/2dlZv8xLzL/ZWNm/0hGSv9IR0z/Xlxf/1pYXv89Oz//TkxS/1JQUv9JR0r/TUtQ/1dVWf86ODv/TkxQ/z47Pv8+PED/end4/zAuMf9PTlD/amhr/x0bHv9jYWL/ODY5/zIwMv+DgYT/ODY6/1NRVv9zcnb/HRwg/1pZXP+DgYT/Hx0g/2hmav9kYmb/LCov/2pobv9tbHH/MjAz/1JRVf9PTVH/QD9G/1taXv8yMDT/dHN5/3l4ff8fHiH/Z2Vq/25tcv8cGh3/aWds/3d1eP8mJSf/ZGJk/2BeYf8kIiX/jYuP/0hHSv8sKi//cXB2/z89Qf8zMjT/g4GE/z07Pv85ODz/cXB1/zQxNP8zMTT/SUhL/0A/Q/85Nzr/PDs//y4tL/9GRUv/HBob/0tKUP8eHB//SEdM/xwbH/8ZGBz/Tk1R/318gP9jYWL/wcDC/2VkZ/9/fX//rKqq/zw6Ov+Ylpf/PDo8/11cX/+zsrX/sbC0/7Sztv+2trj/urm8/7i3uv+8u73/uLe4///////////////////////////////////////8/Pz/JCMl/4iGiP+ura7/kpCR/4WEhP+8u7z/oZ+g/4B+f/+Fg4X/QD5A/xsZHP8YFxn/JSQn/yAeIv8vLTH/HBse/z49Qv8rKi3/LSsv/0NCRv8bGh3/SkhN/zQzN/8zMjf/JiUs/zo5Pv/U09T/oJ+g/6imqP+xr7H/ube5/7Oys//DwsP/xMLE/9fV1v+6ubr/1NPU/8PBw/+6uLr/uLa4/8G/wf+2tbf/sa+w/7Kwsv+hoKL/rq2v/11bXv8kIib/Kykt/1dVWv8sKi7/Liww/9DQ0f+ZmJn/y8nK/7W0tf+6ubr/vr2//6qoqv+wr7H/wcDD/7Gwsv+ysrT/trW4/6moqf/Jx8j/v77A/7a1tv/Pzc7/urm7/8fFx/+wrrD/trS1/9bV1f++vL3/xMLD/8/Nzf/T0tT/vLu9/7m4uf/W1df/rKut/9PT1P+vrq//ubi6/7Gvsf/KyMn/s7Kz/8C/wP+wrq//vby9/8fGyP/Lysz/wsDB/8vKy//Ozc7/trW1/7++wP+sqqv/pKKi/7Oxsv+zsrT/tLK0/6CfoP+SkZL/0dDT/xoYHP8oJyv/Q0FG/yknKf9HRUj/MC0w/zEvMP9JR0v/Hx0g/zs4Pf86ODz/Kyot/1RSV/8qKSv/LCot/0JARP8kIiT/JSMl/zIwNP84Njr/MC0w/zs6Pv8+PED/KSgr/0tKTv8nJij/QD9D/0ZFSf8gHiD/SkhM/zk4Ov8xLzP/RkVI/xcWGP8yMTP/Ojg9/xkXGv9aWV3/JiUq/yEfIv9OTVP/HBse/yQiJv9CQUf/Ojk9/x0bHf81NDn/IB8i/yYlKP8xLzX/Hhwf/zU0Of8kIib/Kikt/z49Qv8lJCf/IR8i/zw7QP8dHB//NDEz/0NCRv8bGh3/MjA0/0tJTv8hHyP/LSsu/zk4P/8cGx//LCov/0A/RP8YFhj/NjU6/y8uM/8eHB//Liww/yclKf8aGBr/NTQ4/xoYG/8iICP/FxUX/yclKP8XFhf/ODY7/xoZG/8tLDH/HBsf/xcVGP9ZWF3/dXR5/2RjZP/CwML/XVtf/3d2d/+wrq7/MjAx/5GPkf81MzX/Wlha/6Oiov+hoaL/p6ao/62srf+oqKn/qqqq/6+ur/+op6j///////////////////////////////////////z8/P8nJSj/i4mL/6+ur/+Qj4//h4WG/8G/wP+mpKT/gH5//4WEhv85Nzn/ISAj/xsZHP8sKi7/IB8h/yUjJv8aGRv/NjQ2/yooK/8kIiX/Kygq/y0rLv8kIyX/Pz5C/x4dIP8dHCL/OTk8/9XU1P+Ni47/mpic/6imqv+tq67/s7G0/8HAwf/DwsT/v76//8/Nz//b2t3/1tbZ/9DQ0//U09b/w8LE/8TExv/Ix8n/xsXH/8C/wv+1tbn/YV9j/yAeIf87OT3/Kyks/z49Qf8mJCf/yMfJ/5COkP+dm5//p6ap/6Gfov+ko6X/qaiq/6inqf+koqb/pKSm/6inqv+sq63/rauu/6imqf+sq63/rKuu/6uqrf+tq67/qKeq/6emqP+pqKv/qKiq/6alqP+lo6b/oJ+g/6Kgov+lpKb/paSm/6Sjpf+ko6b/pqWo/6qprP+np6n/pqap/6Cfof+ioaT/oJ+h/5uanP+dnJ//oaCj/5ybn/+dnJ//nJue/6OhpP+qqaz/p6ao/6Cfov+cm57/mpmc/56doP+enJ//oqGk/6Ggov/S0dP/GBcb/yknLP8fHiH/QD5C/x0bHv84Njj/KCcq/zEwMv9HRUj/GBca/zw6Pf81NDb/KSgr/1dVV/8eHR//R0VI/y8uMP8oJyn/OTc5/yEfIv9GQ0X/HRsd/1RSVP8yMDH/JiQm/1pXWf8XFRj/SUdJ/0pISf8fHR7/TktK/yclJ/9JR0n/UU9R/yUkJ/9eXF7/JSQn/z89QP9UUlX/GRcc/0A/Q/87OTv/Gxoe/0E/Q/9PTE7/HBsd/1tZXP9GREb/Hhwf/2RiZv8uLDD/RUNH/25tb/8gHyL/VlRX/1hXWv8dGx7/UE9S/01LTv8eHSD/WVZY/1NRU/8eHB//V1Za/2BfYv8fHiL/W1le/0tJTv8eHSH/XVte/ysqLf8uLDD/VVJW/xwaHv8qKCv/WFdc/yUjJ/89O0D/OTc7/zc1Ov8oJin/OTg+/x0bHf8tLC//GBcZ/zEwNf8dHCD/Gxkd/1hXXP9xcHX/amhq/8TDxP9eXWD/e3p7/6Ohof87OTr/lJKT/zc0Nv98e33//////////////////////////////////////////////////////////////////////////////////Pz8/yYkJv+PjY//sa+w/4+Njf+DgYL/xcTF/6Cenv9/fYD/h4aJ/0A/Q/8fHSH/IB8j/yQiJf8kIib/QD9E/xwbHv9jYmn/IiEj/0tKUP81NDn/NzY7/1NQU/8tLC//W1hd/yUkKP8yMDP/vr2+/7u6vP+7ubv/vLu9/7++wP/EwsT/tbO1/62srv+xr7H/sK6w/6Wkpf+pqKn/qKep/6moqf+mpab/qKao/62rrf+rqqz/rKus/8TDxv9gX2L/IR8k/zQyNP9TUVX/IR8i/yclKP+Ihoj/oaCh/6CfoP+enJ7/m5qb/56dnv+amZn/n52e/56dnv+enZ//m5uc/5qZmv+gn6D/oqGh/5mYmf+Ylpf/l5aW/5ycnf+cm5z/nZuc/6GgoP+hoKD/oqCh/6Ggof+gn6D/oaCg/6GgoP+enJ3/nZuc/56cnf+bmpv/npyd/5+dnv+enZ7/nZuc/6GfoP+enZ7/oJ6f/5+dnv+gnp//m5qb/5iXmP+Yl5j/m5ma/5qZm/+XlZb/m5ma/5aUlv+RkJL/k5KT/5COkP+OjY7/jYuN/4+Oj/8ZFxr/JCMn/1BOUv8uLDH/c3F1/zk3Of9XVVn/WFZZ/xsZHf+Ni43/NzQ2/zs5PP9xb3H/IB4g/3p3ef82NTf/W1lb/2ZjZ/82NDj/aGZp/yopLP9pZmf/Ozo7/1VTVv9XVVb/Hhwf/5COkv80MjT/KSco/1JQVP8vLjD/Wlha/z89P/8nJin/bmxx/x4cH/9hYGP/V1ZY/yUjJv97eX7/MS8z/zMyNv+bmp//TUxQ/ycmKv9qaW7/Kyot/y8tMv9fXmX/JiQo/0hHTf9QT1T/JCMm/3Jxdf8oJir/Liwx/3h3fP8kIiX/Pz1C/2Rjaf8nJir/JSMn/29udP8nJin/JiUo/2trcP8iICX/RURI/1hWWf8iICX/UlBV/0lITP8bGR3/X15i/zU0OP8uLDD/Pj1C/z8+Q/8dHCD/PjxC/ygmKv9WVVz/HRwf/09OVP8aGBr/NDM5/ygmK/8oJyv/VVRY/3d3fP9lY2X/xsbH/2JhZf94d3n/trW2/0I/Qf+Zl5j/NjQ0/3l4ev/////////////////////////////////////////////////////////////////////////////////8/Pz/JiQm/4uJi/+ysbL/jYuM/4aEhf/Fw8X/oJ6g/4OBg/+Dg4X/QT9C/xwaHf8aGBz/HRwe/xsaHf8jIiX/FhQW/ywrLf8eHSD/IiAj/yclKP8lIyb/JyUm/zk4PP8nJSj/Li0z/yUjJv8cGRv/HRob/yYkJv8dHB3/IB4g/xwbHv8iISP/HBoc/x4dHv8bGRv/JiQl/yMhI/8cGh3/HBod/xgWGf8iICL/GBYZ/x4dIP8dGx3/GRgb/x0bHf8yMDX/NTM2/ywqLv9OTVL/JyUo/yUjJf8mJCX/Hx0g/yspLP8fHSD/LCsu/yYkJ/8lIyX/Kigq/yAeIf8uLC//IiAi/yYkJf8uLC3/JyQl/yUiJP8vLS7/HRsb/yspKf8mJCb/JCMl/ysqK/8gHiD/MS8y/yQiI/8oJyj/JSQn/yooKv8hHyH/JyYp/yspLP8mJSf/Kikr/yMhI/8wLTD/IR8h/yclJ/8lJCb/JCIk/yMhIv8nJSb/JSMm/yMhI/8qKSv/KScr/yknKv8jIST/Kigr/yQiJP8uLC//IR8h/ygmKf8jISL/IiAh/xcVGP9QTlL/HRwf/0tKTv8mJSj/Q0JE/z48Pv8dHB7/XFpd/x4cH/8/PUH/QkFD/xwbHf9PTU//JSIk/z07P/83NTf/KScs/0hHS/8cGh7/V1ZZ/yUkJv9KSEv/MzE0/yspLf9dW1//IR8h/0A+Qf9HRkn/IR8g/0hGSP8xMDL/SEZI/zc1Of8zMTP/REJG/yMiJf88Oj3/JSQp/yEfIP82NTf/HRwg/yYlJ/84Njj/ISAk/zIxM/9CQET/IB8j/y8tMP8pKS7/IiAk/0JBRP8nJir/LSsu/0VDR/8gHyP/NzQ3/zQyN/8fHiL/TEtM/zg3Ov8gHyL/Ozk7/0xKTf8lJCf/ODY4/zEwNf8cGh3/MjE0/yopLf8iIST/NDI1/yAeI/8pJyj/NjQ3/yEgJP8bGhz/ODc7/x4dH/8iISP/Hh0g/x0bHv8XFRf/MzE2/xwaHP89PEL/HBod/xwaHf9WVVn/dXN4/19dXv/BwMH/ZWNl/3Z0df+0s7P/MzEx/5aUlP82MzX/eXh6//////////////////////////////////////////////////////////////////////////////////z8/P8mJSf/h4WI/7S0tf+PjY7/hIKD/8XExf+gnqD/hIKF/4SDhf9BQET/Hhwg/x4cIP8vLTH/IyIl/zs5Pf8cGh3/WVhc/ywrLv87OTz/LCot/2NgZP8lJCb/Pz1B/0tJT/8jISX/V1Za/yAfIf9GREf/IyEk/zw5PP8lJCb/Ozk8/zMxM/8mJCX/KCYo/zw6Pf8pKCr/Pzw9/yUjJv9CP0L/Hhwf/05MT/8oJyv/KSgr/zg2Of8mJSn/REJE/yspK/9ST1H/NDM2/y4tL/9GRUj/LSsv/0JAQv8rKS3/ODc6/ysqLv83Njr/Li0v/ykmKf9EQUP/IR8i/zs5PP8rKiz/NTM1/yMiI/8/PT7/JSMk/z07PP8nJCf/LCos/zc2OP8iISX/PTw+/yYlKP82NDb/JyYo/zIwMv8oJyr/MjAy/yknKv8zMTP/OTc6/y8tMP82NDf/MzE1/zIwM/8sKy7/Ly0x/zc2Of8sKy//Ly4x/zY0Nv8qKS3/LCsv/zc1Of8rKS7/NTQ4/ysqLf8wLzT/NTQ4/zMxNv8uLDD/MTA1/yooLP8sKi3/MzE1/zEvMf8sKy7/MzE2/zw7P/8xLzP/Pzw9/y8tMP81MzT/Kigq/y8tMf9BP0H/JiUp/zY1N/8/PUD/MS8y/zc0Nv8xMDT/ODY6/z49Qf88Oj3/MS8x/zEwMv87OT3/Li0x/zUzNv8zMTT/Hx0f/z47PP9HRUn/JCIm/1NQU/89Oz//T01Q/0VDRf8fHiL/bmxw/yUkJ/9eXWH/YWBj/zc1OP91dHb/NDI1/zg2Of+Ihon/ISAk/1dVWf9paG3/Hx4i/3h2e/9OTFD/JCMn/3d1e/8xMDT/Ozk9/2tpbf8xMDT/RENH/4WEiP8lIyb/UlFU/4aFiP8iIST/QD9C/4F/g/8eHR//Q0FF/2xqbf8jIST/ZWJl/zw7P/8rKi7/ZWNp/zQyNf8mJCj/ZWNn/zo3Ov9APkL/RENE/z48P/8mJSf/RENH/x4cHv8vLjH/Gxkb/ysqLf8dHCD/IB4h/1xbX/93dnr/ZmRl/8TDxP9hX2H/dHJz/66trf87OTr/lJKT/zc1N/95eHn//////////////////////////////////////////////////////////////////////////////////Pz8/ygmKP+KiIr/rq2v/5SSk/+CgIH/ysnK/6Cen/+Ihoj/g4KE/zw6Pv8iIST/HRwf/yMiJP8hICP/Kigs/x4cH/9TUlX/HRwe/z07QP8+PUD/IB4f/1pYXf81MzX/NDI3/3Nyd/8hHyP/YF9l/zY0N/9aWVz/IyIk/1BOU/8vLjH/VFJV/0A/Q/8/PUH/MjE0/1lXW/8hHyH/U1FV/ysqLf9NS0//IB8i/1RSV/82NTn/Hx4h/2hmav8pKCr/SkhL/yQiJP9ZWFz/SkhL/y4rLv9cWmD/IyEl/0ZESP8wLjD/NzU7/zg2PP8zMjb/R0ZK/zY0Nv9AP0P/Liwu/0E/Q/87Oj3/PDo8/ygmKf9OTFH/NTM2/zs6Pv9DQUX/Kyou/0lITP8oJyr/RURL/zY0Of80Mzf/NjU5/zQyNv8yMDP/MzE1/zw6PP8xLzL/SEZK/zEvMv8sKi3/OTg8/zQyN/81NDj/Kiku/zg2PP8mJSn/QUBH/y4tM/8vLjP/LCsv/zQzOP8uLDD/ODY7/y4sMP8rKi7/SklO/y8tMf89O0D/Liww/zs4PP8kIyb/R0ZJ/zQyNv8yMTX/IyEl/1hWWf8qKCz/RUNH/zUzNf8qKSz/QT9D/y8uMv9GREr/NjQ3/zQyN/9IRkr/Ly4z/0VESP89PEH/Ojk8/0lGSv8vLTD/SkhM/zg2O/9BQEP/MC40/zUzNf87ODr/Liww/yspLP9MSk//JiQn/z47Pv9MSkz/List/0xKTv8oJyj/Q0FG/y0sMP8zMjT/XFpe/yIfIP9WVFn/RURJ/yAeIP9fXWL/LSww/ykoK/9SUVj/IiEm/zQyNf9bWl//IB8j/2Zlav9PTlH/IiAj/2FgZP81NDj/JCIl/11cYP8qKCv/Kigp/1dWW/8kIyj/IR8h/1hXWv8gHiH/MjE0/0tJTf8eHB//QUBE/y0sMP8rKi3/Q0FG/xsZHf8zMjX/Li0x/y4tMf8eHB7/NjQ3/ywrLf82NTj/GBYZ/09NU/8dHB//RENH/yMhJP8kIyb/VVRY/3l4fP9pZ2n/xsXF/2VkZv9ycHH/o6Kj/z06O/+Vk5P/Pz0//319fv/////////////////////////////////////////////////////////////////////////////////8/Pz/JyYo/46Nj/+op6n/kI6P/4qJiv/Ix8f/paSl/4SChP+FhIb/RkRI/x0cH/8bGRz/Gxkb/xgWGP8iICP/FhUX/zo5O/8YFhn/GRcZ/ygnKf8XFRf/IyEi/zw6Pf8bGRv/JSMm/0hGSv8jIST/JyUn/xwaHf8wLzT/Ghgb/y0rL/8mJCf/HBod/yQjJv8uLTT/Ghgc/zw6QP8dHB//Kikt/yEgIv8wLjP/Gxod/yclKP85ODv/Hh0h/zY1OP8lIyb/Y2Jm/x0bHP8zMTP/NzU5/x4cH/9KSU//Gxkd/y8tMv8uLDD/Hx0g/ygmKv8nJir/JyUp/yMhJf8gHiL/IyEj/zY1Of8gHiD/KSgr/yAfIv8rKS3/Kyou/ysqL/8oJyv/JyYq/yooLf8pJyz/IR8j/yUjJ/8kIiX/NzY6/x8fIv8xMDX/Hhwf/zAuMv8mJCf/JiQn/ycmKf8uLTL/IiEj/ygnK/8jISb/IiEl/ysqMP8kIib/MzI4/yIhJP8mJCf/JSMm/zEwNP8mJCb/IB4i/ycmKv8kIib/Kikr/x8dIf8rKS3/ISAk/ycmKv8mJCj/IR8i/x8eI/8+PUH/FxYZ/y8uMv8mJCj/Ghga/y8uMv8fHiH/KCcr/yAfIv8eHSH/LCsv/xsZHP8fHiD/Hx4j/zY1OP8oJiv/Gxkc/yUjJ/8ZGBv/Lisu/x4dIP8yMTb/JSQo/x4dIf8rKS7/JCMn/x4cH/8uLTH/Ghkb/ywqLP8rKSz/MC0u/zAuMP8mJCf/b25x/xYUFf9fXV3/LCot/x8dH/9KSEr/HBoe/zk3Of9cW13/GBYb/zk4PP9APkL/HBod/0tJS/8nJin/LCsu/ywqLf8jISX/IB4g/1tZW/8XFhj/NjQ3/1pYWv8cGh3/NjQ2/15bX/8aGBv/Pzw8/0RBRP8eGx3/VlRV/yspLP8nJSj/SkhK/yAeIf9OTE7/SEZJ/x4cH/8uLC//KCYq/yknKf8iICL/HRsd/zw6Pf8XFhf/Kyot/xYVF/8tLDH/Ghgb/x0cHv9XVlr/dHR3/2poav/Nzc7/aWdq/3Fwcf+ura3/QT9B/5uZmf8/PT//enl7//////////////////////////////////////////////////////////////////////////////////z8/P8nJSf/jYyO/66tr/+SkZH/hYSF/8fGxv+joqP/hoSG/4SEhf9BP0H/IyEj/x4cHv8xLzL/LCsu/0A/Q/8gHiD/ZWNp/y8tMf9gXmH/Ozk7/3Fvc/80MTT/QkBD/2RhY/8mJCf/JSMn/xsaHf8aGBz/Hx0j/xoZHf8dHCL/Ghkd/xsaHv8bGh7/Gxkd/xsZHf8fHiL/Hx4i/x4cIP8dHCD/HRwg/xwbH/8dGx//HBod/xwbHv8cGh//GRgb/0E/Qv8rKSz/Wlhc/zY0N/9BP0L/JSQn/x8dIf8jISb/IiEl/yAfIv8gHiL/Hx4i/x0cIf8fHiL/IiAk/yEgJP8iICX/ISAj/yUjJ/8kIif/IiEl/yIhJv8gHyT/IB8k/yQiJ/8nJir/ISAk/yEgJf8iISb/JCIn/yIiJv8lIyf/JyYr/yUkKP8iIST/JSQo/yQjJv8jIib/IiEk/yQiJ/8kIyf/IyEl/yYlKf8oJiv/IyIl/yAfJP8hICX/IyEl/yclKf8nJSn/KCcr/yMhJf8kIyf/JSMn/yMhJv8oJir/JCMn/yYlKf8oJyv/JiQp/yUkKP8lJCj/JiQp/yQjKP8nJSn/KCcr/ycmK/8kIyb/IyEm/yIgJf8kIyj/JCMo/ycmKv8mJSn/JyYr/yIhJv8lJCn/IyIm/yQjJv8mJSn/JSMn/ygnK/8mJSn/LCsu/yMiJ/8lJCj/JSQo/yMiJf8kIyb/IyIl/x4cHv9BQEX/Ojg8/zs5PP81Mzf/d3Z7/0xLTv8nJSj/c3J3/yclJ/9KSUz/aWhr/yUjJf9wb3T/TEtO/yQiJf91dHn/Kikt/zk4Pf+DgYb/Hx4h/2poaf9NSkz/Kigq/4eFif9MS07/Hx0g/5STlv81NDf/Kyks/5WUl/80MzX/ODY4/3l4e/8hHyP/QD5A/2JhZf8dGx//amlt/0lITf8fHSD/b25x/zU0N/8lIyb/XFpe/yEfIv9MSk//NzY6/zw6P/8pKCv/Li0x/xwaHf9CQUX/HBoc/0RDRv8cGx3/Hx0g/11cYP96en3/ZGJl/8jHyP9ubHD/eXh5/7Sys/84Njb/lpSU/zs5O/96eXv//////////////////////////////////////////////////////////////////////////////////Pz8/yclKP+QjY//srGz/46Njf+GhIT/zMrL/6impv+Jh4r/hIOF/0NCRv8fHSD/Gxoc/yspLP8hHyL/JyYp/xkXGf8+PUD/HBoc/yspLP85ODr/IyEj/1hYXf83Njr/KScq/0A+Qv8lIyb/p6ap/5mYmv+bmp3/l5aZ/5iXmf+Xl5n/lZWX/5aWmP+Ylpn/mpmb/5ybnP+cm53/nJqd/5qZnP+Ylpn/l5aY/5aUlv+WlZf/lpSW/6Kho/9OTU//IB4i/01LUP82NTj/NzU4/zIwNP93dnj/oaCh/6Cfof+joqX/pKKl/6Gfov+dnJ7/nZyf/52cn/+enJ//npyg/52cn/+gn6H/oaCi/5+fof+enaD/oJ+i/6Cfov+ioaP/pKOl/6Oipf+hoKP/oaCj/6Kgo/+joqT/paSm/6emqf+npqj/p6ap/6emqf+npqn/paSn/6Wkp/+joqX/paSn/6emqf+lpaf/pqao/6Wkp/+ioaT/o6Om/6Oipf+joqT/pqWo/6alqP+kpKb/o6Kl/6Wkpv+kpKX/o6Kl/6enqf+npqj/p6ap/6alp/+mpaj/pqWn/6OipP+ioaP/oaCj/6Wkpv+koqT/o6Kk/6Ojpf+ioqT/o6Kl/6Wkpv+mpaf/qaiq/6alqP+ioaX/oqGk/6inqv+op6n/p6ap/6moqv+op6n/p6ap/6Wlp/+np6j/qKeq/6elqf+npqn/qair/6Wkpv+qqKv/h4aI/xoYG/8tKy//Ly4y/xwaHf86ODz/MS8y/yQjJ/82NDb/Xlxh/yIhI/88Ojz/VVRX/yYkKP9YV1v/OTc8/yQiJv9VVFr/KScr/zUzNv9mZWz/IyEk/01KTP9KSUv/IyEk/1lXWv9HRUn/Hx0f/1RSVP87Oj3/KCYo/1dVWP86OTv/JSMm/2hnbP8cGx7/TkxN/1lXWv8eGx3/cG5x/y4sL/8eHB3/QT5B/yYkKP84Njj/Ly0x/yAeIf8sKiz/JCIl/x4dIP9AP0T/Ghkc/0NCR/8gHyL/QUBE/yIhJf8hHyL/W1le/3l5fP9samz/xsXH/3BucP9zcnP/u7q7/zMxMv+Vk5T/QkBB/3h3eP/////////////////////////////////////////////////////////////////////////////////8/Pz/JSMm/46Mjv+trK7/j42O/4mIiP/NzMz/p6Wl/4yKjf+DgYT/Pz5B/yIhJP8cGh3/IiEk/x4cH/8wLzP/HRsd/0A+Qv8oJin/JyUo/1BOUP8cGh3/NzY5/zo4Pf8aGR3/NTQ3/y8tMP/b2tv/0tHT/9LS1P/d3d7/vby//9TT1f/Ozc7/ubm7/9ra2//T0tT/0tLU/8TDxP/R0NL/zMzN/8zLzf/Lysv/xMLD/8zKy//DwsL/oZ+h/2ZlZ/8uLDD/JiUo/1lYX/82NDn/KCcr/6inqf/Kysv/0tHR/9DP0f/Rz9H/1NPU/9PS0//V1NX/09LT/9DP0f/Qz9H/0dDS/9TT1P/QztD/zczN/8/Oz//Ozc7/0M7P/9DQ0P/Ozc//zMrM/8nIyf/Ny8z/0M/P/83LzP/T0dL/y8rM/8zLzP/Kycv/xcTG/87Nzv/GxMb/ysnK/8zKy//Lycv/y8nK/8zLzP/My8v/z87O/8zLzP/Kycr/ysnL/8TDxP/GxMb/ysnK/83Mzv/Ozc//0dDR/9HQ0f/V09T/0tHS/9DOz//T0dL/09LT/9HP0f/R0NH/zczN/9PR0v/W1NX/1dXV/9PR0v/X1db/2NfY/9bV1v/W1db/2NfX/9nY2f/Pzc7/29vb/9jX2P/V1NX/29ra/9XV1v/X1tb/1tXW/9TT1P/Y19j/19fY/9bV1v/W1db/tLO1/9TT1P+rqqz/ycfI/7e0tf+rqqr/Gxka/y0rLv82NTf/ZWNn/yQiJv9EQ0b/jo2Q/y8tL/85Nzr/lZOW/zg2Ov9DQkP/i4mL/yAfI/9KSUz/cnBz/ywqLf+Vk5X/RkVI/ysqLf9vbnP/KCcq/25sbP9IRkn/IyEj/4B/gf9APkH/LSss/3Nxcv86ODv/MS8y/3NydP9OTVD/JSQn/15dZf8oJyv/ODY4/4B+gP8gHyH/Wlha/1xaXf8jISL/eHZ6/yooLP88Oz//VlNX/y8tMP9HRUj/Ojg7/zMyNv8aGBv/KCYp/xkYGv8jIib/Gxod/xoZG/9hYGT/eXh7/25tbv/Ozc7/cnF0/21sbf+4trf/REJF/5uanP87OTv/fHt9//////////////////////////////////////////////////////////////////////////////////z8/P8kIiX/jo2O/62srv+TkZL/jIuM/83MzP+koqP/jo2P/4OChP9DQkX/JiUp/yEfI/9CQEX/Kyot/z08QP8jISP/Wlhd/yMhI/9bWl//MzE0/1hXXP9ZV1r/RURI/3Bub/8rKS//NDI2/9DOz/+amZr/2Nja/46Mj//j4uP/i4mK/97d3/+zsbP/s7O1/9PT1v+lpKj/6ejq/5KRk//Z2Nr/nJqd/9fW2P/Ew8X/pKOk/9zb3f+Vk5T/Z2Zo/yUjJv9YV13/HBod/0VDSf83Njz/p6ao/728vf+npqf/qaeo/5qYmf+koqP/o6Gi/52cnf+bmpv/oZ+g/5mYmf+Qj5D/o6Gj/5+en/+enZ7/u7q8/6mnqP+koqP/r62v/5mYmP+cmpz/paSm/7m3uP/b2tv/sa+w/6+usP+dnJ3/qqmr/6Kho/+gn6D/lpWX/6Ggov+ioaL/oqCh/8LAwf+ioKH/l5WX/5+eoP+bmpr/oqCi/6Oiov+pqKj/o6Gj/6Kgov+npaf/tLKz/6moqf+sqqv/raur/7WztP+sqqz/srGx/7m3uf+7urv/x8XG/+3s7f/Kycv/5uXm/5+eoP/Lysv/1dTW/6alqP/q6er/j46R/9jY2v+2tbj/u7u9/+Df4P+enJ//2trb/8TCxP+op6r/7Ozt/6imqf/T09X/29vc/5GQlP/l5eb/oqCk/8HAwf/Fxcb/o6Kj/8C/wP+enJ7/oZ+g/6qpq/8YFxn/RkVJ/y4sL/8gHiL/ZWNo/zUzN/8uLTH/eXh8/y4tMf8hHyH/b210/ywqL/8bGRz/amlu/yopLP86ODv/UVBU/xkXGv9TUVT/NjQ3/xwaHf93dnr/Hh0f/0E/Q/9hYGT/GBYX/1lXXf9RUFf/FxUW/2JhZv9CQET/Gxod/1tZXP8vLTH/IiEl/1xbYf8iICT/LCos/2JgZP8ZFxn/NjQ4/11cYP8YFxn/Q0JH/y8tMf82NDn/Ozo9/ygmKf8iICT/RURI/xsaHP9qaW7/Gxod/2dmbP8hHyP/Gxoe/2FgZP96eX3/bmxu/8vJy/95d3v/dHN1/7q5uv80MzT/mZiZ/zs4O/97env/////////////////////////////////////////////////////////////////////////////////+/v7/yQjJv+KiIn/sbCy/4+Ojv+Jh4j/zs3O/6Kgof+LiYv/hIOG/0dGSv8dHB//GBca/yMiJf8ZGBr/JCIl/xgWF/88Oj3/FhUX/yAeIP8oJyr/IR8h/ywqLP8sKi3/Kigr/zk3Pv8wLjL/ycjJ/7q5u/+LiYr/zMvM/6Ggov/b2tr/jYyN/9nY2P+6urv/tLO0/9HQ0f+pqKr/4eDi/6mnqf/k4+T/m5qb/8nIyv/V1dX/p6Sm/6Oio/9oZ2r/JSMm/zIwNP9VU1j/Liwv/yspLf+pqKr/zMvN/6WjpP+vra7/rayu/8PCxP+urK7/srGy/8PCw/+6ubr/u7m6/728vf+vra//tbS3/7e1t//FxMb/vLu9/8C/wP+4t7n/ubi6/87Nzv/My8z/u7m6/8fHyP/CwcL/xsTG/9jX2P/W1db/4+Li/8fGx//Kycr/urm6/7m4uf/BwML/yMfI/8HAwP+/vr//0dDR/87Mzf++vb3/uLa3/7++v//j4uP/zMvM/7W0tf+9u73/t7W2/7q5u/+ysbP/vby9/8HAwf+0s7T/4N/h/8LBw//Qz9H/yMfJ/+zs7f+6ubv/19bX/8HAwv+5uLn/09LS/6OipP/q6er/p6ao/8nIyf/Lysz/np2f/+Dg4P+WlJb/0M/Q/8TCw/+Yl5n/5ubm/6Oipf+4t7n/3t3f/6Wkp//m5ub/mpia/8LCw//S0dL/jYuN/8fGx/+dnJ7/q6qr/xkXGf8sKi3/SEZJ/z08QP8sKiz/VFJT/y4tMf8yMDL/bWtt/yUjJ/8uLDD/dHJ1/ygmKv85Nzj/ZWNk/x0cH/9QTlD/MzE0/ykoK/9dW1v/MjA0/zY0Nv9dW17/KSgr/0ZERv8+PED/JCIl/0JAQ/8/PkL/JiQm/1lXWf9IRUj/JCIl/5iWlv84Njn/MC8y/3d2e/8lIyf/X1xd/0hHTP8aGBv/WldZ/zw6PP8yMDL/QD0+/yIgIv81MzX/NzU4/ygmKv8qKCv/FhUX/yQiJf8WFBf/JiUo/x0bHv8eHB//XFtf/3d2ev9ycHP/xMLE/2hnaf92dXb/tLOz/zc1Nv+enZ3/Pz0//3p5ev/////////////////////////////////////////////////////////////////////////////////8/Pz/JSMl/4WDhf+zsrP/lZOT/4iHiP/NzM3/pqSk/4mHiP+DgoT/RENF/yUkKP8gHyP/PDo//yUjJ/8+PED/IiAh/1hWWv8vLS//MzE1/05NUP9MSk3/LSwu/1NSVf8xLzP/QD9E/zIxNf/R0NH/lJOV/769vv+bmpz/zs3O/62rrf/d3N3/lpSW/8nIyf/DwcL/rKut/9XT1P+wr7H/1dTV/7Cusf/CwMP/r66w/6inqf/Fw8T/jYuN/2poa/8iICP/Q0FE/ykoK/9PTU//JiQm/6yrrf+8ur3/ycjL/8C/wf/CwcL/xcTG/769v//Ozc//xMLE/8HAwv+8u7z/ysnL/9za3P/Fxcf/xsbI/8bFx//Hx8j/w8LE/8PCxP/My83/xsXH/728v//a2dr/ycjJ/8XExv/Y2Nn/0M7Q/8rJyv/T0tP/397f/9/e3/++vL7/vby9/8jIyf/BwML/397f/87Nzv/Nzc7/3t3e/9fW1//Mysz/ysjK/9jX2P/Kycv/zMrM/8HAwv/My83/wcDB/8/Nzv/My83/19fY/8zLzf/QztD/0M/Q/+Pj5P/V1Nb/0tHS/9bU1f/Ix8n/09LU/9bV1v/Lysz/0dHS/6inqf/k4+T/t7a3/7y7vf/Z2Nn/oJ6f/9nY2P+ura//vLu9/9rZ2/+npqj/4+Pk/8G/wf+op6n/4N/h/6CfoP/f3t//qqmq/66trv/W1df/p6Wn/4mHiP+sq6z/HBod/zMxNv8nJiv/SUhK/1VTVf8iICT/enh7/0NCRv8ZGBv/g4GG/z89Qf8lJCf/bmxw/zw7P/8mJCj/hYOE/yooK/9JSEr/Pjw+/yUkKP9ycHH/NTM3/zw6Pv9fXWH/IiEl/2FfYf9MSk3/HRwf/2JgYv9SUFT/IyEl/1JPUv9qaGz/HRsd/2loaf9RUFT/ODc6/3Jwdf8mJSr/Pz1A/3d1d/8jIST/RkRJ/0lHS/8nJin/YV9i/zQyNv9APkP/Ly0x/1dWW/8gHyH/U1JY/yIgI/9XVlr/Gxod/x4cH/9aWVz/eHd6/21sbv/Ozc7/bGps/3Nxcv+ysbL/NzY3/5qYmf9BPkD/enl7//////////////////////////////////////////////////////////////////////////////////z8/P8mJCf/iIaI/7Gwsf+Zl5f/jIqL/8/Nzf+ko6P/hIKE/4KBgv9CQUP/Hx0g/xwaHv80MjX/JiUo/zY1Of8bGRz/Wlle/yIgI/9FREj/Pzw//ycmKv9ZV13/NTM2/1xbYv8gHiP/MTAz/8fGx/+npqn/wL/A/9HP0v+/v8D/wcDB/7++v//Hxsf/t7a4/8HAwf+2tbf/wL/A/8C/wP+6ubr/vby8/7m5uv/Gxsf/ubm6/8TDxP+dnJ7/a2pt/zQzNv8pJyn/aWhs/zw6Pf8tLC//q6ut/8jHyv/b2tz/09LU/9PS1P/W1df/09LU/9va3P/U1NT/1NPV/9HR0v/a2dv/5OPl/9bW1//X1tj/19bX/9jX2f/W1db/19bX/9zb3f/X1tj/1NPV/+bl5v/Z2Nn/19bX/+Li4//c293/2tnZ/9/e3//m5eb/6+rr/9TT1P/U09T/2tja/9XV1v/o5+j/3Nvc/9va2//k4+T/4+Lj/9zb3P/b29v/4+Hi/9nZ2v/c29z/1dTV/9zc3f/W1db/397e/93c3v/k4uP/3dvc/97d3v/g3+D/6urq/+Pj4//g3+D/4uHh/+3s7f/i4eL/4N/g/8PDxf/h4OH/2tnZ/6+usP/X1tj/u7q7/7OytP/e3t7/sbCx/9jX2P+/vsD/zMvN/9va3P/BwMP/6ejp/8jHyf/Jycv/2dna/6inqf/r6+z/wL/B/7i3uv/k4+X/p6ap/62sr/8ZFxr/NjQ4/0RDSf8oJir/Pz1A/4aEh/8kIyX/Z2Vn/zc1Of83Njf/XVtf/zg3Pf8iIST/bGps/zc1OP8qJyj/W1la/yIhI/83NTf/WFdY/xkYG/9raWr/Ojg7/yMiJv97eXz/Hh0g/zUzN/9jYWT/HRse/1hWV/9TUVT/IB8i/0JAQ/87Oj7/IiAh/1xaXP8mJCb/Hhwe/1BOVf8lIyj/Lywt/z49Qf8fHSD/JyUo/z07QP8bGhv/KCUn/yknKv8kIiT/LCsu/xcVF/80Mjb/FxYY/zo5Pf8bGRz/HRwg/1xbX/95d3z/amps/87Nzv9sam3/cnBy/7Oys/85Nzj/l5WW/0A9Pv99fH7/////////////////////////////////////////////////////////////////////////////////+/v7/yMhI/+Ihoj/s7K0/5eVlf+Ih4j/zMrK/6impv+GhYb/goGD/0RCRP8gHiH/HBod/yAeIv8cGh7/KCYo/xkXGf8yMDT/GBYY/yQjJf8iICL/FxUY/yspLP8hHyH/JiUo/zc2PP8vLTD/4N/g/83Lzf/Lysv/09LU/8nIyv/Av8D/wL/A/7++v//BwML/v76//769v//Av8H/vr6//7++v/+7urv/vLu9/7q6vP+7urz/u7u9/8jIyf9vbnD/IiEl/11bYP82NDn/UU9V/zIwNP+pqKr/ubi6/6OipP+mpaj/o6Kj/56cn/+joqX/paOm/56cn/+ioaT/pKOm/6Sjpv+joqT/m5mc/6KhpP+ioKP/qqir/6akp/+cm57/mZib/52cnv+cm57/l5WY/5qZnP+cm57/m5mc/56doP+cm57/mZia/5ybnf+dm57/nZue/5mXmv+Vk5b/lpWX/56dn/+dnJ7/oaCh/6Khov+hoKH/oqGj/6SjpP+joqP/qqir/6+usf+rqqz/rKut/6alp/+opqj/p6an/6alp/+lpKb/oJ+h/6KhpP+lo6b/p6ao/6moqv+jo6X/q6qs/76+wP+1tLb/sK+x/6yrrf+trK//q6ms/6Wkpv+gn6L/paOl/6Kho/+fnqD/oJ+h/6alqP+op6v/pKOm/66srv+qqq3/rKuu/6WkqP+urbD/ubi6/7W0tf+0srX/uLe6/7Oytf+1tLj/qair/xoYG/87OTz/MjA3/3Z1e/84Nzz/Kyos/3Z1ev8lJCf/dHN3/1BPVP8fHSH/hoSH/1RSWP8qKCz/kZCS/0lIS/8tKi3/pqSm/z48QP84Njn/fn2A/x8d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///8/Pz/JCMl/5GPkf+9vL7/l5aW/42MjP/Hxsb/srGx/5SSk/+DgoT/S0lL/y4tMf8mJCn/JSMl/yooKv8wLjH/IiAi/zAuMP8cGhz/JiQm/xwaHf8yMDL/NzQ3/yEfIf83NTf/MjA2/yQjJ//My83/oqCi/6uprP+qqav/tbS2/6+usP+rqq3/tbS3/62sr/+rqaz/srGz/728vv+rqqz/r66x/7OytP+wr7H/tLK2/7W0t//Jycv/ycjL/2loav8iICT/JiUo/2hmbf8oJin/IB8h/8/Oz/+tq6z/raus/7CvsP+3tbb/0dDS/7q4uv/Rz9H/tLO1/7m4uv/CwML/vby+/7i3uv+op6j/uLe5/6Wjpf+ko6b/o6Km/66trv+vra//vr2//6+ur/+ysbL/sa+x/7u5u/+0s7X/trW3/66tr/+xsLH/ube5/769v//Av8H/tbS1/7i3uf+5uLr/u7q8/729v/+6ubv/vr2//7q5u/+5uLn/ubi6/7m5u/+7urz/urm7/7m4uv+7urz/ubi6/7y7vf+9vL3/vr2//7y7vf+/vsD/wsHD/7++wP/BwMP/ysrM/8bFyP++vb7/3dzd/0NBRf8YFxv/PDs+/ywrL/8yMDL/S0hK/ysqLf9GREb/TktN/x8eIv9ZV1j/TUtO/xoYG/9ZV1r/Kikt/zk3OP9tamz/HBsd/25sbv88O0D/Lisv/15bXP8qKC3/QD9B/09OU/8gHiL/a2hq/1tZWv8cGhv/hYKC/1JQUv8gHiH/a2lq/zk3O/8jIiX/VlRU/0RCRv8gHiH/amhq/yQiJv9EQkT/Wlha/xkXG/93dXf/PDtA/yEfI/93dXT/Kiks/zAvMv9vbXP/Hhwh/1NQUf9ubHD/HRwg/2ZkaP8yMTX/JSQm/25tb/8jIib/QUBD/3V0eP8ZFxn/gX+A/1dVVv8nJSf/enh5/z88PP8vLC3/kY+Q/yspKv9JRkf/ZGJl/yknKv88Oj7/NTQ4/0lITP8eHSD/SkpQ/x0cHv9BQEX/HBof/yEfJP9eXWH/cW9z/3d1d//NzM3/enl7/3Z1d/+8urz/Qj9B/56dnv85Nzj/f36A//////////////////////////////////////////////////////////////////////////////////39/f8jIiX/kI6Q/728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Uf8yMTX/WVhc/yIhJf9GREj/MjE1/z08QP9IRUf/MC4y/0tJS/8+PD3/OTY3/0pISf8tLC//TUtO/zY0Nv83Njn/RkRH/zY0OP9eW17/QT9A/zw6PP9cWVr/Ly0v/1JQUv8yMDL/V1VX/ygnK/9pZ2j/NzU3/1xZW/9IRkj/QT9C/2RiZP8rKi7/cnB0/ykoLP9oZWf/UlBT/z07Pv92dHb/Kykt/21rb/8zMjX/W1pd/15bXf80MjX/dnR3/yUkJ/9jYWT/ODY6/1xaXv8pKCv/bGpu/zY1Of9WVVn/REJF/z08QP9dW1z/LCos/0hHS/9HRkn/Pj1A/2xqa/8mJSj/X11e/0lGSv8yMDL/bGlp/ywqLf9LSUv/QD5B/zs5Pv9APkD/aGZq/yopLf92dHf/Q0FD/yknKv9paGr/Kyks/1JPUf83NTn/U1JV/1pYWf8jIST/XFte/z49Qf88Oz//YmBi/yAfIf9ua2r/QD5A/yknK/9oZmj/MjE0/0dFSP9hYGL/MC8z/zc1OP9WVFf/KSgs/01LTv9FQ0b/JyUo/0A9Pv85Nzr/SUZI/0pHSv9JR0r/SUdK/yYlKP9TUFP/VlRY/yYlKf9WVFf/QkFG/y8uMP9samv/PTxA/0E/QP9XVln/NjU5/1JQUv9DQUX/MTAz/0tJSf8mJCX/QT9B/zc2OP8sKi3/MC4x/zY1Of8/PUL/IyIl/z08Qf8cGh3/UlBW/xoYHP8gHiL/Y2Jm/318gP9ubXD/ycjK/3h2eP9wbnD/w8HC/0JAQf+Pjo//PDo9/1pZW/+xsLH/ubm6/76+vv+/v8D/vby9/7++v/+0s7T/tbS1///////////////////////////////////////7+/v/JSQn/5aUlv+5ubr/npyc/5qZmv/S0dL/tLKy/5GPkf9/foD/RUNG/yIgJP8cGh7/IB8g/yMhJP86ODz/MC4y/1JRVv8oJin/Xlxj/ysqLP99fIH/W1tg/z08Qf+Af4X/JSMl/1pXXP9DQkX/OTc7/zo4O/8zMTb/Ojg+/0A/Q/9JSE3/IyEl/1taYP8nJSj/WFZb/yQiJP9QTlL/LCou/1VTWf80Mzb/RkVI/1RTV/8vLTD/WFZZ/zo4O/87ODv/SUdL/0pITP8tKy7/YF5k/zQzNv9kYmj/KScq/z48QP8pJyr/YF5i/ycl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Iv9KR0n/JCIm/ygmKP9LSkz/GBca/ysqLf8wLjH/Ghga/0NCRv8aGBv/JiUo/ygmK/8ZGBr/HRwf/ycmLP8dHB//MS8y/yEgJP8eHSH/MC8x/xsaHP8bGRr/Ghkc/ykoLP8aGh3/Hx4i/yEfIv8cGx7/MzI2/xYVGP8aGBv/UlFV/3p5fv9XVlj/x8bI/2lobP9kY2X/xMPE/1hWWP99fH3/NDM1/4KAgf/////////////////////////////////////////////////////////////////////////////////6+vr/IyEj/4eEh/+/vr//kpCR/42Mjf/Mysv/qKen/4+Nj/95d3r/RENG/x4cH/8eHB//Ghga/yYkKP8iICP/JiQn/zs6Pv85OD3/QkBF/zIxM/9ZV1z/PDs+/z07P/9ubHL/MzE2/ysqLf/Hx8j/tbS2/62srv+vr7H/tLO1/66tr/+wr7L/s7K0/7KytP+trK7/sK+x/62tr/+srK7/sK+y/7Cvsf+wr7H/r66w/6+ur/+xsLH/vby9/19dYf8iICT/SEdM/zg3Ov9EQkf/Kigs/2BeYv+5uLr/rq2v/769v/+5uLr/sbCy/7SytP+vrrH/urm7/7a1t/+vrrH/sa+y/66tr/+sq63/qqmr/6yrrf+trK7/rayu/62sr/+ura//sbCz/7OytP+1tbf/tbS2/7e2uP+8u73/v77A/769v/+9vL7/vr2//7++wP/BwML/vby+/769v/++vr//urm8/7u6vP+8u77/urm8/7W0t/+2tbj/tLS2/7S0tv+5uLr/urm7/7q5u/+5uLr/ubi7/7i3uf+4t7n/uLe5/7W1t/+3trn/tbW3/7S0tv+0s7X/s7K1/7e2uP+8u73/uLe5/7a1t/+4uLr/t7a4/7i3uv+4t7n/vby+/728v/+1tLf/u7q8/7i3uv+4t7r/tbS3/7Sztv+ysrX/s7K1/7S0t/+zsrX/s7O1/7Sztf+xsLP/tLO2/7Sztv+xsLL/tLO2/7a1t/+zsrT/srK0/7KxtP+ysbT/sK+x/66usP+vrrH/rayv/62tr/+srK7/r66w/66usP+tra//r66w/66ur/+vr7H/rq2v/6+usP+sq63/urm8/0NCRf8eHB7/ODY7/yQiJv86OD3/RENH/yMiJv99e37/MC4x/1dV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Ov8rKSz/OTg6/xsaHP8yMDP/JyUn/yclJ/8yMDH/JSMm/ywqLP8kIyX/NDM2/yMhI/8wLjL/KSgr/yQiJv8tLC//IB4h/ygnKf80MjT/JSMl/ywrLf85Nzr/HBsc/zs5PP8lIyX/JCMl/0FAQ/8lIyT/IiEl/zY0N/8oJir/PTs9/yAfIf8xLzL/KCYp/zAuMf8vLC//JSMm/y8uMP8hHyH/MjAy/x8dH/83NTn/Hhwe/zQyN/8oJij/Hhwe/zU0N/8jISL/JCMm/ygmKP8jISP/MjAz/yQiI/8jISP/MC4x/y0qLP8eHB3/MjAy/yYkJf8qKCv/List/x0bHv8lIyb/LSsu/yMiJP8iISP/PTs9/yknKv8jISX/Kykr/x0cHf81NDb/Hx0f/yQjJf80MjP/HRse/zk3Ov8eHR7/Liwv/x0cHv8qKCr/IiAj/yEfIf8eHB7/JSMm/yAdH/8fHSD/Kykr/xkXGf8mJCj/IR8i/ywqLv8fHiD/KSgr/yYkJf8lIyb/LCot/yAeIf8bGRr/KCYo/yMhI/8hHyH/Gxkc/zc1OP8dGx7/HRse/zEwM/8kIyX/HRwf/xsaHv8ZGBz/Kyks/+fn6P+qqKr/7u3t/9bV1v/W1db/3Nvc/97e3//T09P/0tHS/9va2//g39//7+7v/9bW1v/y8fH/5+fo//Ly8v/u7e7/8O/w/15cX/8bGR3/Hx4g/yAeIP8iHyL/HRsd/3Ryc//y8fH/8O/v/+3s7f/r6uv/3t3e/8nIyf/S0dL/uri6/6uqq/+lpKb/nJud/5WTlP+GhIT/YV5f/3x6ev9YV1n/S0pN/5uanP8hHyL/Liwx/317fP/////////////////////////////////////////////////////////////////////////////////4+Pj/GRcZ/42Ljv+/vsD/hYSE/4OCg/+4trf/mJaX/318fv9ta27/Li0w/xgWGf8YFhn/GBYZ/xgXG/8XFhn/GBYa/xgWGv8YFhr/GBcb/xgWG/8XFRr/FRMX/xcWGv8YFhr/FxYZ/xYUF/8WFBj/GBYa/xYUF/8XFhr/FhUZ/xgWGv8XFhr/Gxke/xsZHP8bGh3/IyIl/x0cIP8kIyf/Hh0g/x4cH/8iISb/Gxod/xsaHf8mJSj/HBod/x0bHv8aGBv/JSMo/x0cH/8hHyP/IiEl/x8eIf8oJyv/IB8i/ysqLf8cGx7/JiUp/x0bHv8oJyv/Gxoe/yMiJv8rKi//JCIl/x4dH/8mJCj/Liwv/x4dIP8pKCz/JCIk/ycmKf8fHiL/JyYp/yMhJv8pKC3/ISAk/yUkKP8WFRf/Li0z/xwbHv8qKC3/Hh0h/x4cH/8rKi7/Hhwf/yMhJf8kIyf/ISAj/yEfI/8eHCD/HRwf/x0bHv8iISX/Hh0g/xsZHf8dHB//IR8k/x4dIP8fHiL/Hx0h/yYkKP8iICP/Hx0g/yIhJP8aGRz/IR8k/yMiJf8bGRz/JiUp/xoZHP8cGx3/Hh0g/ysqLv8eHB7/Ghga/yYkJ/8iICP/IR8i/xsaHP8eHB//Kikt/xcVGP8cGh7/ISAj/x4cH/8aGBv/Hhwg/yIhJP8YFhn/IB8i/xoZHP8cGh3/HBsf/xsaHf8aGBz/HBsf/x8eIv8bGh7/HBse/x8eI/8aGBz/ISAk/x8eIv8dHB//HBoe/x8eI/8hICT/HBoe/ykoLP8gHyL/Ghgc/x4dIf8iISb/IR8j/yknK/8dHB7/Hh0h/xcWGv8vLTD/6ejp/7GvsP/r6ur/vby+/7a0tv+5ubv/xcXG/8zLy//g3+D/6unq/93d3f/w8PD/7+/v//Ly8v/v7u//8vHy/+fm5v/w8PD/W1pc/x0bIP8oJyz/NjU7/yknKv8wLjH/dnV2//Lx8v/V1NX/29rb/+Dg4P/j4+T/1tXX/+jn6P/o5+f/1dTW/9XV1v/Hxsj/xMPF/8G/wf9zcnT/tbS3/2VjZf9WVFj/nZud/yQiI/8vLjH/fnx+//////////////////////////////////////////////////////////////////////////////////j4+P8bGh7/j46Q/8HAwv+DgYL/dnR1/7GvsP+RkJD/eXd5/21sbv8wLzL/FxUY/xYVGP8WFRj/FhUZ/xYUF/8VFBf/FhQY/xUUF/8VExf/FhUY/xYUF/8VExb/FhQX/xcWGP8XFRj/FhQX/xYUF/8WFBj/FRQY/xUUF/8WFBj/FhQY/xYUGP8WFRn/GBYa/xYVGP8WFRn/FhUZ/xcWGv8YFxv/FhUY/xYVGf8WFBj/FRQY/xUUGP8VExf/FhUX/xcWGP8YFxv/FhUY/xYVGP8WFBj/FRQX/xcVGP8XFRj/FxYZ/xUUF/8UExb/FhUY/xgXGv8WFRn/FRMX/xYUGP8VExf/FhUX/xUUF/8WFRj/FRQX/xQTFv8WFRn/FxYZ/xQTFv8UExb/FRMW/xcWGf8WFRj/FRQX/xUUF/8UExb/FhQX/xcVGf8WFRf/FhUX/xQTFv8XFRj/FhQX/xgXGv8YFxr/FxUY/xUUF/8XFhn/FxUY/xUUF/8VFBb/FxUY/xcVGP8VExb/FRQX/xgWGf8XFRn/FxYZ/xcWF/8XFhn/FhUX/xcVGP8WFBj/FRMW/xcVGP8XFhn/FxUY/xgXGf8XFRn/GBca/xcVGP8XFRf/GBYZ/xgXGf8WFRj/FhQX/xYUGP8WFBj/FRMW/xYUGP8YFxn/FhQX/xYUF/8WFRj/GBYZ/xUUF/8WFRj/FRQW/xYVF/8XFRj/FxYZ/xcWGP8XFhj/FRQX/xcWGP8WFBf/FhQY/xUUF/8WFRj/FhQY/xQTF/8VFBb/FRQX/xQTFv8WFBf/FhUY/xcVGP8XFhn/GBYa/xYVGP8WFRj/FRQX/xYUF/8VFBj/FhQY/ygnKf/n5uf/uLa3/+rp6f/Rz9D/2NfY/9va2//t7Oz/4+Lj/9PS0f/k4uP/ycjJ/+jn5//d3N3/8PDw/+Li4//x8fH/6Ofn//Hx8f9ramz/Ghkd/ykoLf8nJSn/Pz1C/yYkJ/+Qjo//8vHx/+Hg4P/g3+D/397e/9jY2f/u7u//zczN/7++v/+2tLb/lpWW/42Mjf+Jh4j/eHZ3/1VTVv95d3r/T01P/0VDRv+enJ7/IyEj/ywqLf99fH3/////////////////////////////////////////////////////////////////////////////////9/f3/xoZHP+Mio3/ubi6/4KBgv9vbW3/qqmq/4iGh/90c3X/hoWH/yclKf8lIiT/Lisu/yknKP8pJin/LCos/y4sLf8vLS//Ly0u/zUzNf85Nzr/NDEz/z07Pf82Mzb/OTY5/zYzNv86Nzr/PDo8/zMxM/89Oz3/NzU3/zUzNf83NTf/Ozk7/zg2OP84Njn/NDI0/zg2Of8yMDL/MTAy/z06Pf8zMTT/NzU3/zQyNP87OT3/NjU4/zMxM/8yMDP/NjQ2/zUzNf85Njn/QT9B/z07Pf88OTz/PDo9/z07Pv85Nzn/OTY5/zg2OP89Oj3/PDo8/zw6PP9APkH/ODY5/z48QP87Ojz/Pz5B/zw6Pf87OTz/QkBE/z89QP86Nzr/REJE/0NBQ/9CQEL/Ojg7/0FAQ/88Oj3/Pj1A/z89QP9DQkX/QkFE/0E/Qf9DQUT/RUNH/0RDRv9BP0P/Q0FF/z49QP9BP0L/QD5B/0JBRP9DQUX/Q0JG/0VDRv9EQ0b/QT9D/0NBRP9BQEL/REJF/z48P/9EQ0b/QkBD/0A/Qv9APkH/PDs9/zw6Pv87OTz/QT9C/z07Pf88Oz7/Q0FE/0VERv8+PD//QkBD/0FAQv9AP0H/QUBC/0FAQv9CQEL/QkFE/0JBRP9CQEP/Q0JF/0FAQ/8/PkD/RENF/z8+QP8+PUD/QD5C/0E/Q/9CQUP/Ozo8/z89QP85ODr/PTs+/z8+P/9APkH/Pz1A/z48P/85Nzr/QD9C/zs6Pf88Oz//PTw//zw6Pf84Njv/ODY5/zQyNv8yMDX/Ojk8/zc1OP82NDj/MS8y/zAuMf8jISP/KScq/yAeIv8bGR7/JiQm/+fm5/+2tbb/6urq/9DP0P/X1tf/3Nvb/+/u7v/y8fH/8O/v//Py8v/y8fH/8/Ly//Lx8v/x8fH/7Ovr//Hx8P/l4+P/8fHx/42Ljf8XFhr/OTg//yknLf85Nz3/IB4h/6yrrP/o5+j/7+/v/+/v7//w8PD/7+/v/+bl5v/u7e7/7u3u/9bV1v/T0tP/xcTG/8C/wP+8urv/cnBy/6moqv9iYGL/TkxO/5yam/8mJCb/MjA0/3t6e//////////////////////////////////////////////////////////////////////////////////39/f/Ghkc/4+Nj/+5uLn/gYCB/4KBgv+7urv/l5aX/3x6fP/f3uD/q6qt/6Wlp/+mpaj/p6ep/6qpq/+pqav/pqWo/6Skp/+npqn/qKer/6WkqP+joqT/oqGk/6Ggov+gn6L/oqKk/6Sjpf+mpaf/paSm/6Kho/+ioaP/o6Kl/6Kho/+joqT/oqGk/6KhpP+joqX/oqGj/6Ghov+hoKL/oKCi/5+fof+hoaP/oqGi/6Kho/+gn6H/oaGj/6Oipf+hoaL/n56g/56dnv+fnp//np2f/52cnv+bmpz/mpmb/5qZnP+ZmJv/m5qd/5qYnP+bmp3/nJud/5ybnv+ZmZz/lpWZ/5mYm/+bmZ3/mZmc/5eXm/+WlJn/lJOX/5SSlv+Vk5f/kpGV/4+Okf+KiY3/jIuP/46NkP+JiIz/hoWI/4WEiP+Dgob/f36C/4B/gv9+fYD/enl8/3l5fP9+fYD/fXt//318gP9+fYH/e3p9/3l5fP99fH//f36B/4B/gf9+fYD/e3p9/318f/98e37/e3p9/3x6fv96eXz/d3Z6/3h3ev93dnn/dXR3/3V0eP93dnn/eXh7/3l4e/97en3/fXx//3t6ff97en3/fHt+/3x7fv96eXv/eXh8/3t6ff96eXz/enl9/3p5ff97en3/eHd7/3d3ev94eHv/d3Z5/3V1d/92dXj/d3Z5/3d2ef92dXj/eXl8/3l4fP91dHf/dnV4/3Z1eP9zcnb/c3J1/3V0eP91dXn/c3J1/3Fwc/9zcnb/c3J2/3JxdP91c3f/d3Z6/3V0eP9ycXT/Z2Zq/3Rzd/94d3v/enl9/3V0d/9SUVT/YF9i/0dFSf8rKSz/5+fn/7W0tf/p6Oj/sK+x/62ssf+ysbX/u7m8/7q4u/+5uLr/2djY/8HAwv/l5eX/y8rL/+7u7v/s7Oz/8O/v//Hx8f/w8O//t7a3/xcWG/8rKS7/NDM4/zMyNv8eHSD/0M/P/9zb3P/t7e3/5eXl/+Hg4P/o5+f/0M/Q/+Pi4v/Y19j/1NPU/9TT1P/OztD/vby//7y7vv9ycXT/sbCz/2xqbP9YVlj/nJqb/yYkJv8uLDD/e3p7//////////////////////////////////////////////////////////////////////////////////f39/8aFxn/h4WG/6yqqv9mZGP/U1FR/2dlZf9KRkf/VlRU/2FfYf9tbG//g4GD/4qIiv+JiIr/jYuO/4iHiv+RkZT/lJOX/5GQk/+QkJT/nJue/5uanv+Tkpb/nZyg/5qZnf+Qj5L/oJ+i/6inqv+cmp7/np2g/6Ggpf+urbD/rayv/6Oipf+npan/qqqt/8XEx/+wsLT/y8rM/6+usf/CwcL/ubi5/7u6vP+rqqz/tLO1/6emqP/DwsT/sK6v/7Kwsv/Hxsj/yMfJ/8PCw//CwcL/uLe4/7+9v/+0s7T/urm6/6elqP+pp6n/qqiq/6uprP+koqT/oZ+g/6Wjpf+koqT/pKKk/6OipP+lpKb/pqWo/6Kho/+hoKP/nJqc/5aUlv+Uk5X/k5GT/5SSlf+WlZf/l5aY/46Nj/+Liov/kpCS/5CPkf+Pjo//j46P/4+OkP+NjI7/i4qL/42Mjf+MjI7/jYyO/4yLjf+RkJH/lpWX/5GPkf+TkZL/kI+Q/5SSlP+TkZP/k5KT/5aVl/+SkZL/kI+Q/5eWl/+TkpP/kpGT/5WUlf+WlZb/kI6Q/5COj/+Rj5H/kZCR/5GQkv+Tk5P/kZCS/4yLjP+Ni4z/mpia/5GQkf+OjY7/kJCR/46Njv+Lioz/i4qM/4yKi/+Mi4z/iomK/4uKi/+Mi4z/iomJ/46Njv+KiYr/i4mK/4iHiP+Lior/j42O/4+Njv+LiYr/i4mK/4uKjP+Ihoj/iomK/42Mjf+Qj5H/i4qM/5CPkf+SkZL/i4qL/4uKi/+Hhoj/jYuN/4iHif94dnj/gH6A/4OCgv97eXn/W1hY/01LS/9hYGL/S0lM/yspK//o5+f/v72+//Py8f/x8fL/8fDx//Ly8v/y8vL/8vHx//Ly8v/y8vL/8vLy//Ly8v/x8fH/7u7u/9zc3f/q6uv/7+/v/9TT1P/S0dP/IyIn/y0rMP8pKC3/NzU5/y4sLv/f3t//z83O//Hx8f/Qz9D/6urq//Dw8P/h4OD/8O/v/97d3v/Ixsn/z87P/5eVl/+Ni47/goGD/1NRUv91dHX/RUNE/0hHSf+Mioz/KScq/zEvM/95eHn/////////////////////////////////////////////////////////////////////////////////+Pj4/xsZG/+GhIb/raus/29tbf9yb2//k5GQ/3JwcP+lo6T/pqSl/728vv+9vL3/2NfZ/97d3//i4eP/1NPV/8/Oz//OzM3/0M/Q/9PS0//Pzs7/1dXV/9bV1f/b2tr/4eHi/9/e3v/T09P/zs3O/9HQ0P/Rz9H/29rb/9HR0v/S0dH/2NjY/9va2//e3d7/3t3e/9bV1v/V1NX/1dTU/9XU1f/c29z/1dTU/9LR0v/V1NX/3Nvb/9XV1v/h4OH/3Nzc/9fW1//a2tr/1tXW/9XU1f/a2dr/4ODg/+Li4v/r6uv/5OPk/+fm5//V1NX/3dzd/+Df4P/c29z/19bX/9fX2P/Z2dr/1NPU/9HQ0v/R0NL/1dTV/+Lh4//W1tf/2NfX/9DP0P/Q0ND/0dDR/9PS0//T0tT/1NTV/9XV1v/W1db/1dTW/9jX2P/Z2Nn/19fY/9jX2f/Y19j/2NfZ/9nY2f/Y19j/2NfX/9ra2v/b2tv/2tna/9rZ2f/Y19j/2djY/9nY2P/n5uf/4N/g/9zb2//b2tv/2tnZ/9fW1//X1tb/1tXW/9jX2P/V09P/2NfY/9fW1//W1db/1tXV/9jX1//W1dX/09PT/9TT1P/T0tP/0c/Q/9PS0//T0tP/09LU/9DP0P/W1NX/1dTV/9bV1v/U09X/09LT/9TT1P/S0dH/1dTV/9fW1v/U09T/0M/Q/8vKy//Lysv/xsTF/8fGyP/BwML/v76//7Kws//Av8H/w8LD/8HAwv+6ubv/uri5/8HAwv/BwMP/x8bI/8LBwv/DwsP/srG0/7q5vP+xsbT/mZic/7OxtP+Nioz/cG5w/42Mjv9ZWFv/Ly0v/+jn6P+xr6//4uHh/6elp/+lpKb/sbCy/8nIyf+6ubr/4eDg/9XU1f/JyMn/6enp/9va3P/u7u7/7u7v//Dw8f/w8PH/6unq/+Pi4/83Njr/Li0z/ygmKv82NTr/Pjw9/+fm5v/t7Oz/7u3t/+rp6v/k4+T/7+7v/+bl5v/v7u7/3d3d/9bV1f/Pz9D/y8vL/8PDwv/BwMH/eHZ4/7Sys/9raWv/XVxe/4OChP8pJyr/MTA0/3x7fP/////////////////////////////////////////////////////////////////////////////////4+Pj/Gxkc/4qIiv+lo6P/gX5//3Fvbv+vra7/jIqK/62srf+7u7z/vb2+/7y7vP+BgIP/R0ZJ/0xKTP+Qj5H/xcTG/8XExv/Ix8j/y8nK/8PCw//My8z/u7q7/25tb/9LSUz/VlRW/6urrP/Ly83/yMjJ/8vKzP/S0dL/xcXG/8fGxv+4t7j/amlr/0pISv93dXf/w8LD/8zLzP/Jx8j/ysnK/9PS0//Kycr/xcTF/8nIyf/S0tP/ysnK/9va2//V1NX/zs7P/9PS0v/Kysv/ycjK/8/O0P/Y19j/29rc/+jo6f/b2tz/4uHi/8nIyf/V1NX/2djZ/9PS1P/Lysz/y8rM/83Mzv/FxMb/w8LE/8LCxP/IyMr/2trc/8jHyf/Ix8n/vr2//769v/+/vsD/wsHC/8HAwf/DwsT/xcTG/8XExf/CwsP/xMPF/8PCxP+9vL//vby//7e3uf+8u73/t7W3/7W0tf+7ubz/sbCz/7Gvsf+1tLb/tbW2/7y7vf+9vL3/yMfJ/+bm5v/CwcP/s7O1/7i3uv+vrrD/qKiq/6qpq/+rqqz/srGz/7Kwsv+zsrP/srGy/7Sys/+zsrP/tbO0/7q4uv+5uLr/ubi5/7q4uv+4trn/t7a4/6+usP+1tLX/trW3/6qpq/+rqqz/qqmr/6uqrP+trK7/q6ms/6inqf+npaf/pqWn/6emqP+opqj/p6ao/5+eoP+gn6L/p6Wo/5qYmv+bmpv/qKap/5ybnv+ZmJr/oJ+h/56dn/+ZmJn/mpia/56dnv+Ylpj/jYuN/5yanP+Uk5X/eXd5/4B/gf+Hhon/bGpr/21rbP9MSkz/bWtt/1FQUf8wLi//6Ofo/8TCwv/x8PD/8fDw//Hw8f/w7+//8fDw//Lx8f/y8fH/7u7u//Hw8f/y8fL/8vHy/+Dg4f/l5OX/3t7f/+vq6v/k4+T/zc3O/ywrLv8gHiL/JCIl/zAuNP85Nzf/3dzc/+Df4P/l5eX/5OTl/93c3f/t7O3/397f/+3s7f/S0dP/ysnK/8C/wf+1tLb/q6us/7Kxsv9raWz/mZiZ/2RjZP9MS03/hYSF/yspK/8wLzP/fXx+//////////////////////////////////////////////////////////////////////////////////f39/8WFRf/kI6Q/6Cenv9gXV3/Uk9P/3d1df9TUVH/bGlq/4iGif+1tLX/bm1v/xkXGv88Oz7/ODc6/xgXGv93dnf/0dDR/56dn/+koqT/sbCy/9DP0P84Nzn/IR8i/0ZERv8mJCb/KSgp/7i4uf+2tLb/rKyt/6SipP+xsLH/wsHC/zAuL/8nJSf/SUhK/yEgIf8/PT//2tna/6akpf+pp6f/sa+v/7Cur/+joaH/qaeo/6mnp/+joaH/o6Kj/6Oiov+mpaX/pKOj/6upqv+rqqv/qqiq/5+en/+lpKX/t7a3/62rrP+joqP/qaep/6qoqv+npqb/npud/5+dnv+ioKL/nZud/52cnv+hoKH/pKOk/6CeoP+gn6D/mJeZ/6Gfof+koqT/rKqs/6Ggov+cmpz/mZiZ/5ybnP+VlJb/lZSW/5mYmf+XlZf/k5KS/5OSk/+VlJb/lZSV/5mYmv+Vk5X/mpma/5STlP+RkJH/k5KT/5OSlf+TkpT/lpWX/5aVl/+Xlpj/mZiZ/5+eof+lpKb/09LT/7e1t/+SkZL/k5GS/5mXmP+cmpz/nZqb/5eWl/+Qjo7/n52e/5uZmv+TkZP/lJKU/5aUlv+UkpP/mJaY/5eVl/+TkpP/lpSW/5SSk/+LiYv/jYyO/5STlP+TkZP/hIOF/4eFh/+OjY7/kI6Q/4qJiv+LiYr/jYuM/4aEhv+EgoP/h4aH/4iHiP+Eg4T/c3Fz/4SDhP+Jh4j/iomK/3l2eP95d3n/hoSF/4WEhf+Ihof/dXN1/4KBgf+Ni43/dHJ0/3Ryc/+KiIr/YmBi/2lmaP91c3X/RUND/0NAQf9VU1T/SUdK/y4sLv/o5+f/t7a2/+7t7f+8u7z/tbS1/7u6uv+0s7P/x8XF/87Nzv+0srP/w8LD/+fm5//f3+H/7e3t//Hx8f/w7+//8vHx/9/e3/89Oz7/GBca/xoZHf8oJyv/Ly4z/zc0Nv9DQUL/5+fm/+jo6P/q6ur/0dHT/+vr6/+3trj/y8rL/9XU1v+sqqv/r62u/52cnf+Mi4z/g4KD/1JQUf9/fH7/TkxN/0hGSP+Fg4X/JCIk/y8uMv99fH3/////////////////////////////////////////////////////////////////////////////////+Pj4/xcVF/+Vk5T/np2e/3p4ef99env/ko+Q/5aUlf+enaD/srGz/76+wP8fHiL/npyf/6yqrP+TkZP/bWxu/xMRE/++vb7/x8bH/9PT0//k4+T/c3N1/zMyNf+urK//fn1//42Mjf9WVVj/PTw+/9bV1//h4OH/4N/g/+jn6P9YV1n/V1ZZ/8XExf+QjpD/mpmb/y0sMP9vbW//7u7v/97d3v/n5ub/2djY/97d3v/g4OD/6+rr/+Xk5f/m5eX/4uLi/+jn6P/i4eL/5uXl/+De4P/i4eL/5+fn/+Lh4f/Z2dr/6ejp/+fm5//j4uP/5+bm/+Lh4f/n5ub/4uHi/+Tj5P/i4eL/4+Lj/+Xk5f/n5uf/5OTk/+Lh4v/k5OX/5uXm/+Xk5P/n5ub/6urq/+7t7v/v7u//6urr/+jn6P/o5+j/5+fo/+jn6P/o5+j/5+bo/+fn6P/m5eb/5ubm/+Tk5P/m5uf/5eXm/+bl5v/m5uf/5uXn/+fm5//m5eb/5uXm/+Xl5v/m5eb/5eTl/+bl5v/k4+T/5+fo/+Xl5f/n5+f/6Ofo/+fn5//o5+f/6Ofo/+jn5//p6Oj/5+fo/+rp6v/q6er/6unq/+no6f/q6en/6Ojo/+jm5//o5+j/6Ofo/+bm5//m5ub/5uXm/+bl5v/l5OX/5eXl/+Pj5P/h4OH/5OPk/+Tj5f/l5eX/5OPl/+Li4//b2tv/1NLT/+Df4P/W1db/sbCx/9bW1v/Qzs7/2NfY/9LQ0v+pp6f/zs3N/97d3v/Z2Nj/npyd/8C+vv/i4eH/o6Gh/6ajpP/a2dr/nZ2f/6Ohof+UkpL/VlRV/5qYmf9ZV1n/Kyks/+fm5//Mysr/8PDw/+vq6//p6en/7Ovr/+7t7f/r6ur/8vHw//Ly8v/v7+//8vLy/+/v8P/w7/D/8fHx/8vKyf/y8fD/cXBy/xkYG/81Mzj/ISAk/1tZYP8tLDD/Qj9C/yspK/+Af4D/8PDv/+/u7v/u7e3/8O/v/+vr6//r6+v/5eTk/9rY2v/Mysz/wsHD/8HAwf+8u7z/dHJy/5KQkf9cWlz/UE5Q/46Mjf8pJyn/NzY6/359fv/////////////////////////////////////////////////////////////////////////////////6+vr/HRsd/46Njv+enJ//aGVm/3t5ev+Fg4X/b21u/6Oho/+op6r/gYCC/0pJSf/EwsH/jIqM/8C+vv+LiIj/MC8y/4iHiP/e3t//3Nvc/9zc3f88Ojz/goGC/7Kxsv+in6L/hIKB/5GPkf8fHSD/ycfI/9XU1f/Q0NH/z87Q/y4tL/+enJ7/lZKU/5yam/99eXr/d3Z5/y8tMf/w7/D/1dTV/9/e3//Ix8j/zc3O/9HQ0f/e3d7/2tra/9LR0f/a2dr/3t3e/9PS0//Pzs7/1dTV/8zLzP/ExMT/xsXG/8TDxf/NzM3/xcPF/7++v//Gxcb/xMTF/768vf+sq6z/sbCx/7Gwsf+opqf/rayt/7CvsP+tq63/q6qr/6yqqv+vra7/p6an/7Oys/++vb7/09LT/9vb2/+4trj/pqWm/6Sjpf+lpKb/q6ut/7CusP+trK7/rq2v/6Oio/+np6n/oJ+h/6akpv+fnp//oJ+g/6Sjpf+ioKP/pKOl/6Kho/+gn6D/oaCi/6OipP+ioqT/r62v/66trv+ko6X/oJ+h/6Kho/+ioaL/np2f/56dnv+fnp//oJ+f/6Sio/+mpKX/rqut/6uqq/+qqar/qaeo/6qoqf+hoKH/pKKi/6Ohov+mpab/m5mb/56cnP+bmZr/mpia/5aVl/+Yl5n/m5qb/5uam/+bmZv/mpmZ/52cnP+XlZf/lpWW/5eVlv+VlJX/kI+Q/5aUlf+ZmJr/lJOV/5KRkv9ycG//gX5//5yam/+Miov/amhp/46Mjv+enZ//e3l5/2NgYP+fnZ7/gH5//21sbf+TkpP/c3Fy/1ZTUv9DQkT/U1JT/01LTf8nJSf/5ubm/7y6u//n5uf/wL7A/66srv+3trj/zMvL/7e2t//n5ub/7u7u/9jY2f/x8fH/19bY/+zr6//y8fH/8vHx//Lx8f8lIyf/Ghkd/ycmK/8eHSD/RkVL/zk3Pf81Mjb/REJF/0dGSP/x8fD/5ubm/+Lg4f/l5OT/y8rL/9LR0v/DwsP/vLu8/727vf+8u7z/sa+x/7SztP9pZ2n/p6an/15dXv9TUlT/iomK/yYkJ/8uLDD/gH+A//////////////////////////////////////////////////////////////////////////////////7+/v86ODr/gX+B/4yKi/9WU1P/YFxb/2hlZf9samr/dnR1/6+usf+Egob/QD0//7e2t/+qqar/i4mJ/5ORkf8rKiz/k5GT/93d3v/Ozc7/397f/0dGSP9xcHL/qaip/7Kwsf+Sj5D/l5WX/yMhJP/T0tL/4uLi/83Mzf/d3N3/NTQ3/6moq/+sq67/p6Wl/4mHiP9xcHT/NTM1//Hw8P++vb7/1dPU/7++v//Lysv/u7q7/7e1tv/f3d7/wb/B/7Oxsv/KyMn/sK+v/7WztP/DwsT/1NPU/83Mzf/Qz9D/tLO1/9HQ0v+7ur7/wL/C/7u5u/+xsLL/ycjJ/7Sztf+urbD/wL/A/6yrq/+1tLb/q6qs/727vP+6uLr/rKqq/769vf+9u7v/rq2u/6alpv+mpaf/q6mr/62srf+1tLb/ubi5/8PCwv+6uLn/r66v/62rrP+qqar/srGz/7u5u/+zsrT/uLe4/8TDxP+8urv/srCx/7q5uv+5uLj/wL/A/7q6uv+zsbL/tbS1/7a1tv/Av8H/tLK0/7SztP+0s7T/trW2/7W0tf+1tLb/s7Kz/7a1tv+zsrP/trW2/66srf+0s7T/tLKz/7Cur/+8urv/sK+w/7Oxs/+rqav/nJuc/52cnf+ioaP/oaCh/6elpf+op6j/nJqb/52cnf+hoKH/n52e/5qZmf+Ylpb/mZiY/5SSkv+cm5r/mpeW/5yam/+Nior/jIqK/5qYmf+Yl5j/kpGR/5qYmf+Gg4P/fHl4/5aUlf+Rj5H/cW9x/4yLjP+fnp//end3/3p3d/+TkpL/eHZ3/2RiZP+FgoH/Z2Rj/0VDRf9raGr/QkBC/yYkJv/m5ub/wb+//+7t7f/Z19j/y8rL/9fW1v/a2Nn/19bX/+Lg4P/KyMn/1NPU//Hw8P/l5OT/7Ovs/+3s7f/v7+//8O/w/xgWG/8XFhr/JSQo/x0cIP9EQkb/MC80/0A+Qv8yMTb/QT9C//Dv7//b2tr/3dzd/9rZ2f/DwsP/ycfH/7Kwsf+opqf/np2f/42Ljf+Hhoj/fXt9/1ZUVv9/fX7/TUxO/0lISv+Ihon/JCIm/yQjJ/+VlJX//////////////////////////////////////////////////////////////////////////////////////3t6e/9JSEr/r66u/2dlZ/+IhYT/m5mZ/5eUlP+lo6X/ysjJ/8XFx/8kIib/enl7/7y7vP/FxMX/amhq/x4cIP/Z2dr/5OTl/+zr7P/v7+//n5+i/yIhJP+joqX/vr2//6yqrf87Ojv/YmBj/+/u7v/x8O//8PDv//Dv7/94d3n/R0ZJ/7u6vf+oqKv/oaCj/yYkJ/+Bf4H/8/Ly/+7u7v/x8PH/7+/v/+/v7//r6+v/7Ozt//Ly8v/x8fH/7+7v//Dv8P/r6+v/7+7v/+3t7f/u7u7/7+7u/+rq6v/q6ur/7Ovs/+fm5//l5eb/5+bn/+bl5f/r6ur/4+Pj/+Lh4v/n5ub/4uHh/+Li4v/i4eH/4uHh/+Lh4v/i4eH/4uHh/+Lh4v/k4+P/4+Li/+Lh4v/i4eH/4eDh/+Hg4f/g4OD/5OPj/+Df3//i4eL/4uHh/+Hg4P/f3t7/4N/f/9/e3//e3d7/4eHh/+Df3//f3t7/3dzc/93c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2//d29v/6ejo/+fm5v/g39//4eDg/+Tk5P/s6+v/3dvc/+fm5v/V1NT/2djY/9XU1f/b29z/19XX/8/Oz//Z2Nr/z87P/87Nzv/NzM3/ysnK/8bFxv/Gxsf/yMjJ/8LBwv+urK3/yMjI/8vKyv/My8z/y8rL/8fGxv/Ew8T/vLu8/8fGx//Kycr/w8LE/8TDxf/ExMT/n52d/8C/wP+/vr//nJqa/5aTkv/Hxsb/m5qa/4+NjP+6ubn/raus/4uJif/BwMD/joyM/4uIiP+5uLf/aGVl/29sbf+Afn//W1lb/yUjJf/l5eX/uLe4/+jn6P/CwsT/wcDB/8fGyP/f3t//3t7e/9va2//Kycr/wsHC/8rJyv/Q0NH/zczO/8bFxv/c29z/5OTl/+zr7P9zcnX/Hx0i/xgXHP8bGh7/GBYa/yIgJP+Qj5H/8PDw/+vr6//R0ND/1NPU/9/f4P/Av8D/u7q6/728vv+tq6z/nZuc/46Nj/+Hhof/iIeI/1RSUv9zcXL/SUZH/0dERv+BgYP/EhEV/3V0df/8/Pz////////////////////////////////////////////////////////////////////////////////////////////a2dn/MzEz/2VkZf/W1db/e3l5/1lWVv+SkJH/p6Wk/3x6e/+gnp//p6am/7m4uf/c29z/zc3O/8rJyv/X19j/0M/Q/9XU1v/c29z/1NPU/9PS0//T0tT/ysrL/9vb3P/V1db/1NPU/9DP0P/W1dX/29vb/+bm5v/T0tP/4eDh/9PT1P/i4uP/6Ofp/+Xk5f++vr7/1NPU/8jHyP/U09T/x8bH/7m3uP+8urv/w8LD/8LAwf/DwcL/v76//93c3f/Mysz/y8rM/9nY2P/My83/2djY/768vf+/vb//wcDA/8rJyf/Av8D/v72+/8jHyP+7urr/vr2+/7m4uf+0s7T/wb+//7u6uv/EwsP/vry+/9XV1f+8urv/0c/P/7y7vP/Hxsf/r66v/83Lzf/Ix8j/t7a3/7e1tf/W1NX/uLe2/7e2t/+4t7f/u7q7/7Sysv+ysbH/tLKy/7u6uv+zsbH/uLe4/7WztP+7urr/t7W1/728vP+2tLT/srCw/8jHx/+ysbL/wcDB/7e2tv/DwcH/wL6+/7u5uf/R0NH/y8nL/727u//Ixsf/u7q8/9va2v+9vL7/1NTU/7Kxsv+4t7j/urm5/7q5uf+/vb7/pqWm/8C/wP+qqar/p6an/7CvsP+ysbL/tbS1/5+en/+pp6n/q6qr/7SztP+bmZn/npye/6upq/+zsrP/qaep/6yrrf+ioaL/npye/5aVlv+ko6P/rayu/5ybnP+sqqv/oJ+g/6emqP+hoKH/nJqb/4+Njv+hoKH/mJaY/4WCgv+bmpv/m5ma/3t5ev+KiIr/pKOl/25sbP90cnP/VVNV/3Nxcv9QT1H/JSQm/+Xl5f+5uLr/7Ozt/93d3v/g3+D/5OTk/+/u7//w8PD/8O/w//Hx8f/w8PD/8fHx//Lx8f/z8/P/8vLy//Hx8v/w8PH/8PDx/+3s7P+9vL//e3p9/2VjZ/97eX3/w8LE/+7u7v/w7/D/7+/v/+3s7P/r6+v/7e3u/+7t7v/n5uf/2dnb/8zLzP/Hxsf/w8LE/6+ur/+vrrD/cG9x/6Wlp/9jYWL/VlRV/318gP8jIST/2djY//////////////////////////////////////////////////////////////////////////////////////////////////7+/v/DwsP/Kigr/0lISv+8u7v/srGy/29tb/99e3v/gX+B/4WDhP+AfoD/hIKE/4iGiP+Rj5H/lZSV/5aVl/+TkZP/kpCR/4+OkP+UkpT/paSl/5ORk/+al5n/l5aY/6moqv+cm53/q6qs/6imp/+xr7H/oqCj/6Oho/+hoKL/kpGS/5qYmv+fnqD/nJqc/6Gfof+gnqD/o6Kk/5uanP+hn6H/mJeZ/5aUlv+amJr/o6Kk/5yanP+gnqD/w8LD/8TDxf/DwsT/w8LE/8HAwf+mpaf/p6ao/6Ggof+ZmJn/oJ+h/5uanP+op6n/o6Kk/6CfoP+joqT/nJud/5+dn/+joqL/sbCw/6upqv+sq6z/trS2/7Kxsv+npab/qKeo/6Ggof+ko6X/raut/6+ur/+trK7/srCy/7W0tf+xsLH/xcTF/6uqq/+3trj/r62v/6moqv+xr7H/qKao/52cnP+ioaH/pqWm/6Ggof+fnp//r62u/8bFxf+trK7/r66w/7i3uP/DwsP/urm6/8TDxP/Ix8j/0dDQ/6moqv+ura7/pKOl/6imp/+mpKb/mZiZ/5eWl/+bmZv/n52g/6Sjpf+gnqD/q6qs/66tr/+6uLr/p6Wn/62rrf+npqj/pqSm/5WTlv+fnaD/n52h/5GRk/+amZz/oJ+i/5WUlv+NjI3/kpGS/4qJi/+OjZD/hIOF/42Mjv+Jh4r/k5GV/4mIiv+BgIP/gH+C/4OChP+GhYj/iIaI/358fv+DgoT/eHZ3/3Z1d/92dHf/dHJ0/19dXv92dHb/cW9y/05LTf9mZGb/amhp/z89P/80MjP/SUZJ/zk3O/8lIyb/5eXl/768vv/c3N3/rayu/7q5vP+ysbP/29rb/7m3uf+3trj/qKep/6emqP+qqKr/oaCi/6qoqf+vra//sbCx/7Gwsf+vrrD/vLu8/8/O0P/t7e7/8fDx//Dw8P/w8PD/7+/v/+Pi4//b2tv/ysjJ/9XU1P/m5ub/zMvN/8LBw/+3t7n/srGz/7Oytf+qqar/rq2u/6Oho/9ycHL/rKuu/2ZkZv9cWlr/gH+C/zIxNP/q6ur///////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/Z2dn/QkFD/xsaHv9XVlj/pqWm/83Mzf/e3d3/4uHi/+Pj4//k4+T/5OTk/+Tj4//j4uP/5OPk/+Xk5P/l5OX/5uXl/+Xl5f/l5eb/5OTl/+Xk5f/n5uf/5eXl/+Xk5f/k5OT/5eTl/+Tk5f/l5eb/5eXl/+Xl5f/k5OT/5eTl/+Tj5P/k4+T/5OTl/+Tk5P/j4+T/5OPk/+Xk5P/k5OX/5OPk/+Tj5P/l5eX/5eTk/+Xk5P/k4+T/5eTl/+Xk5P/k4+P/5eTk/+Xk5f/l5eX/5eTk/+Xk5P/l5OT/5eTl/+Tk5P/m5eX/5uXl/+Xk5f/k4+T/5OTk/+Xk5f/k4+P/5eTk/+Tj5P/l5OT/4+Lj/+Tj5P/k4+P/4+Li/+Tj4//k4+T/5OTk/+Tj5P/k4+T/5OPj/+Tk5f/k5OT/5OPj/+Xk5f/l5OT/5eTk/+Xk5P/l5OX/5uXk/+bl5f/k4+P/4+Pj/+Tj4//k4+T/5uXl/+Tk5f/k5OT/5eXl/+Xk5P/k5OT/5OPk/+Tj4//j4uL/4+Li/+Tj4//j4uP/4+Li/+Tj4//k4+T/5OPj/+Xj5P/k4+T/5OPk/+Pi4//j4+T/5OPk/+Xk5P/k4+T/5OTk/+Tk5P/k5OT/5OPk/+Pi4v/k4+P/5OPk/+Tj5P/k4+P/4+Lj/+Xk5P/l5OT/5eTk/+Tk5P/k4+T/5OPj/+Pj4//i4eL/4eDh/+Lh4v/i4eL/4uHi/+Lh4v/i4eL/4uHi/+Pi4v/j4uL/4uHh/+Df4P/d3Nz/393d/93c3P/d3Nz/393e/97c3f/V1NX/ysnK/6qpq/+xsLP/gH+C/yQjJv/k5OT/t7W2/+/u7//k4+T/4+Pk/+fm5v/n5ub/5+fn/+jn5//o5+j/6enp/+vr6//r6ur/7e3t/+3s7f/u7u7/7Ozs/+zs7f/u7e7/7Ovt/+3t7v/w8PH/6+vs/+7u7//r6+z/5+bm/+no6f/s6+v/5eTk/93c3f/h4OH/19bX/6impv+cmpv/iIeI/4SDhP94dXb/amdn/0VDRP9ycHD/RUJE/z89Pv+Ih4n/NzU4/+3t7v/////////////////////////////////////////////////////////////////////////////////////////////////////////////////6+vr/rq6u/1tZXP80MzX/IiAj/yAeIf8dGx7/HBod/xwZHP8dHB7/GRga/xsZHf8bGBv/HRsd/x0bHv8cGx3/IB8h/yQjJf8jIiX/HBod/xoZHf8XFRf/HBod/x4cH/8gHiD/HRsd/x4cH/8hHyL/Hhwe/x0bHv8dGx7/Hx0f/x8dH/8eHB7/IB0f/x4cHf8gHh//JCIk/yIgIf8gHyD/IR4g/yEfIf8iHyL/FxUY/xkXGv8hICL/IiAj/yIgIv8hICH/IiAi/yEgIv8kIyX/IiEj/yEgIv8jISP/JSMl/yUjJf8jISP/JSMk/yMhI/8kIiT/IyEj/yIgIv8jISP/IyEj/yMiJP8jIST/IR8i/yEeIv8kIyX/JSMm/yUjJv8jISP/JSMl/yMhI/8kIiT/JyUo/yMiJP8jISX/JCIm/yQhJP8mJSf/IyEi/yYkJv8oJij/JSMl/yEgIv8iICL/IiEi/yEfIf8iISL/IiAj/yIgI/8hHyH/IiEk/yMhI/8gHyH/IB8h/x8dH/8gHiD/IB4g/yEfIv8fHh//IB4g/x8eIP8hHyD/IiAi/x8dIP8fHiH/Hh0f/x8eIP8fHR//IB4g/yAeIP8dGx7/IB4h/yAfIf8gHyH/IB4h/yAfIf8hICL/IB4h/yIfIv8hHyH/IR8h/yAeH/8gHR7/Gxka/xsZG/8eHB//IR8i/yIgI/8fHSD/IB4g/yEgIv8gHiD/Hx0e/x4cHv8fHR//Hx0f/x0bHf8fHR//Hh0f/xwaHP8dGhz/HBob/x0bHf8dGx3/HRsd/x0bHf8bGRr/Hx0f/xkXGf8XFhn/HBsd/+Pj4//DwsT/5eXl/7Kxsv+2tbb/tLOz/7WztP+0s7P/trW1/7m4uf+7ubv/vby8/7W1tv/Ix8j/xcTG/8nIy//Ew8X/x8bH/9DP0f/Jx8r/1NPU/+no6v/T0tT/2NfY/9va2//U09T/29rb/+np6f/g3+D/2NfY/+Pi4//Y19j/09HT/8LBwv+wsLH/p6an/5+en/+XlZX/ZGFi/5GOjv9VU1P/S0hK/4aEhf80MzX/7e3t/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////f39//Dv7//Z2Nn/0dHR/83MzP/Kysr/ysrK/8rJyv/Kycn/ysnK/8nIyP/IyMj/x8bH/8fGx//Jycn/ysrK/8zMzP+cm5z/cnF1/3x7fP/Hx8f/ycjJ/8nJyf/JyMn/yMfI/8rJyv/JyMj/yMjI/8nIyf/Ly8v/zc3N/83Nzf/Ozs7/zs3N/8zMzP/NzM3/zc3N/87Nzv/Pzs7/zs3O/8nJyf9zcnP/dHN1/8/Pz//R0dH/0dHR/9LR0f/R0dH/0dDR/9HR0f/Pzs//zs7O/9DPz//R0dH/0dDQ/8/Pz//Pz8//z8/P/87Ozv/Pzs7/z87P/8/Oz//Q0ND/0dHR/9LS0v/Pz8//z87P/9HR0f/R0dH/0dHR/9HR0f/R0NH/0M/Q/9HR0f/S0dL/0dHR/9LR0v/S0dL/0dHR/9HQ0P/Q0ND/0tHS/9PT0//S0tL/0dHR/9LR0f/R0dH/0dHR/9HQ0f/Qz8//zs3N/9DQ0P/Q0ND/zc3N/83MzP/My8v/zMzM/8rKyv/Lysv/y8rL/8zLy//MzMz/zc3N/8zMzP/Kysr/y8rL/8rKyv/Ly8v/zMvL/8vKy//My8v/zMvL/8rKyv/Ly8v/zMzM/83Nzf/Ozs7/zc3N/8/Oz//Pzs//zs7O/8/Ozv/Ozs7/zMzM/8vKyv96eXr/dHJ0/769vv/Q0ND/0M/Q/8/Oz//Ozc7/zs3O/87Ozv/NzM3/y8rL/8zMzP/Kysr/yMfH/8jIyP/JyMn/yMfH/8fGxv/IyMj/ycjI/8jIyP/Ix8j/yMfH/8jIyP/Jycn/ycjI/6uqq/8oJij/4+Lj/6alpv/s6+r/09LS/7y7u//GxMT/vLu7/9rZ2f/a2dr/wL/A/9nY2P/BwMH/3Nvc/7u6vP/Hxcb/uLe5/7Kwsv+wr7D/srKz/6moqv+lpKX/rayv/7Gvsv/FxMb/zMvL/9TT1P/GxMX/5OPk/9nZ2f/Lysv/397g/83Mzf/BwMH/trW3/62rrP+qqKn/o6Gi/6Khov9wb2//pKOk/2dlZ/9YVlj/f36A/zUzNv/t7e3//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8PDw/+amJr/mJeZ////////////////////////////////////////////////////////////////////////////////////////////////////////////+vr6/5GPkf+Mioz//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5aVlv+Vk5X/5+fn////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////2tra/ysqK//i4uL/r62u//Dw8P/u7u7/7+7u/+7t7f/w7+//8PDw//Lx8f/x8fH/8vLy//Dw8f/w8PH/7+7u/+fm5//Sz9H/zs3P/8rJyv/Pzs//z87Q/8fGyP/Ozc7/0tHS/+Lh4//r6ur/7Orr/+jn6P/q6en/4eDg/8vKy//Ozc7/qaip/6akpf+npaf/o6Gi/52bnf+WlJb/kY+R/2tpav+WlZb/YmFk/0VDRf+JiIv/NTQ3/+7u7v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////xMPD/5iXmv+RkJH////////////////////////////////////////////////////////////////////////////////////////////////////////////5+fn/jYuM/5KRk///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////l5aX/5COkP/n5+f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////n5uf/LSss/8fGxv+9vL7/4+Pk/8vKy//e3t7/u7q7/9rZ2v/Kycv/4ODg/7Cvsf/c29z/trW4/5ybnf+Xlpj/nJuc/5ybnf+bmpz/mZeY/5+en/+hn6D/oJ6g/5qZm/+dnJ7/mZia/5WUlv+ZmJn/n56g/6akpv+lo6X/sK6v/6yqqv+rqan/qqip/5yZmv+Vk5P/h4WH/4OChP98enz/X1xe/3Nxcv9kYmT/aGZp/2JgZP9EQkX/9/f3///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////IyMj/nZye/5SUlf////////////////////////////////////////////////////////////////////////////////////////////////////////////r6+v+Lioz/jY2P//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+SkZH/jo2N/+fn5/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f9+fX7/MC4w/4OChP+XlZf/lJOU/5KRkv+Xlpf/lpWW/5WUlf+Uk5T/lJOU/5SSk/+Rj5D/kY+Q/46Mj/+KiYv/hIOE/4eGh/+HhYf/iYiJ/4qIiv+Fg4X/g4KE/4F/gf+GhIX/hYOE/4aEhv+HhYf/jIqM/4mHif+Lioz/jIqM/42Ljf+Mio3/iIeK/4OChP+DgoT/gH+B/3p5e/92dXf/d3Z5/3NydP9YV1n/IB4i/6Kiov/+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8rJyv+amJr/kZCR////////////////////////////////////////////////////////////////////////////////////////////////////////////+Pj4/4+Oj/+MjI7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5ybm/+PjY//5eXl//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////j4+P+npqf/b21u/2FfYP9hYGL/WVlb/xYVF/85ODv/SkhL/zs6PP8yMDL/JiQn/xUTFv9LSkv/VFJU/1NSU/9TUVP/UlBS/1NSVP9WVFb/VFJU/1NSU/9XVlf/VFJU/1NSVP9VU1X/UlBS/1FPUf9RUFH/UE9Q/1NRUv8/PT7/HBsc/zw7Pv8zMTT/MjAy/yopK/8kIyX/Ghkc/1dWWP9VVFb/WFdY/2ZlZv+3trf//Pz8////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////ycjJ/6OipP+Uk5X////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/j42P/5GQkv//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////l5aX/5qZm//n5+f//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+//7+/v/8/Pz/JiUn/46Njv+sqqv/h4aH/3p3ef9eXF//FBIU/9ra2v/8/Pz//Pz8//z8/P/8/Pz//Pz8//z8/P/8/Pz//Pz8//z8/P/8/Pz//Pz8//z8/P/8/Pz//Pz8//z8/P/8/Pz//Pz8/6qpqf8zMTP/s7O1/3Nxc/+DgYP/W1lc/1BOUP8mJSf//Pz8//39/f/9/f3//v7+///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////FxMX/pKKj/5WUlv////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P+Uk5X/kJCS//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+VlJX/m5mb/+np6f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////r6+v8jIiX/lZSW/7Oxs/+JiIn/f31//1hWWP8VExX/3dzd////////////////////////////////////////////////////////////////////////////////////////////rKur/zUzNf+2tbj/b21u/4KAgP9WU1X/UE5Q/yUkJ//+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8HAwf+dm53/nZye////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/5CPkP+OjpD//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5iXmP+Rj5L/6Ojp////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/r6/yQiJv+dm53/tbS2/46NkP99e33/YmFk/xUUF//e3t7///////////////////////////////////////////////////////////////////////////////////////////+sq6z/NjU3/8fHyv9ycHH/hoWF/1RSU/9SUVT/JiUm//39/f//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////p6an/5uZmv+wr7D////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Pz/kZCS/5STlf//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////nZyd/5mYmv/p6en////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6+vr/IiAj/6Gfov+/vcD/kI+R/3Nxc/9cW17/FBIV/9/f3////////////////////////////////////////////////////////////////////////////////////////////6+ur/82NTn/v77B/399f/+Mioz/VlRW/1VTVf8pJyn//f39//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+SkJH/g4KD/9fX1/////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+TkpP/mZmb///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/wsLC/5KRkv+Ihof/ra2t//Hx8f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+ZmJj/l5aY/+bm5v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+v8lIyX/pKOl/769v/+TkZP/e3l6/2VkZv8WFRb/4ODg////////////////////////////////////////////////////////////////////////////////////////////r66w/zc2Ov+2tbj/hYOE/4+Njf9QTU//XVxd/ycmKP/9/f3/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8PDw/4yLjf9hYGT/+vr6////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/4+OkP+amZv/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////4+Li/3Jwcv+RkJD/lJOV/4+OkP+Pjo//a2lr/7W1tv/9/f3//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5uam/+cm5z/5+fn////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/r6/yYkJv+joqT/uLe4/5GQkf91c3T/ZmRn/xYVF//f39////////////////////////////////////////////////////////////////////////////////////////////+ura7/NTQ3/7KxtP+EgoP/j42N/1VTVP9fXV7/JSQm//39/f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v+zsrP/pqSm/46Oj//////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/j46P/5uanP///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9vb2/92dHb/iYiJ/6Ghof/k5OT/7Ozs/7W1tv+DgoP/gYCB/6qpqv/+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////lpSW/5aUlv/n5uf////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6+vr/JCIk/6OipP+ysbL/kZCR/398fv9jYmT/FhQW/+Dg4P///////////////////////////////////////////////////////////////////////////////////////////6qpqv84Njr/uLi6/4eGiP+OjIz/VlNU/1tZWf8pJyn//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6unp/5CPkP94d3n/4+Pj//////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P+Pjo//oaCj///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5+fn/iYiI/3l4e//Ozc7//////////////////////+zs7P+JiIn/goGC/9LR0v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+TkpP/lZOV/+fn5/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+v8kIiX/o6Kk/7W0tv+ZmJn/enh6/11bXv8YFhj/4uHh////////////////////////////////////////////////////////////////////////////////////////////r66v/zY1OP+rqq3/g4GC/46Njf9aV1j/WVdY/yooK//9/f3///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P+Uk5X/mJaY/5+en//+/v7//////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz8/42Mjf+hoKH//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9HR0f+Ihon/mZia/////////////////////////////////9PT0v+dnJ3/f35//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5aVlv+SkJH/6enp////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/yUkJv+lpKb/sLCx/5STlP9ycHL/Wllc/xkXGf/i4uL///////////////////////////////////////////////////////////////////////////////////////////+ura7/NjQ4/7SytP+NjIz/jImK/1FPT/9VU1T/LSst///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/mJeX/6inqf9/foD/9fX1///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/jo2O/6Cfof//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////pKOk/4KAg//X1tf//////////////////////////////////v7+/4SDhP98e3z/+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////kpGS/5ORk//r6uv////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////6+vr/JCIk/6inqf+4t7n/k5GT/3Vzdv9ZWFv/FxUY/+Li4v///////////////////////////////////////////////////////////////////////////////////////////6yrrP86ODz/oZ+h/4WDhf+CgIH/SkhK/2BeYP8rKSv//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9PT0/6alpf+mpKX/fHp7/+rp6v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P+TkpP/o6Kk//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+ZmJn/cG5v/9/f3///////////////////////////////////////gYCC/3p4ef/39/f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+VlJX/lpWW/+vr6/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/8kIiX/paSl/7WztP+Yl5b/d3R1/1lXWf8TERP/3Nzc////////////////////////////////////////////////////////////////////////////////////////////qqmq/zo5PP+rqaz/i4mL/5aVlv9WVFf/X11e/ysqK//+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/9jX1/+5uLj/rKut/42Mjf/s7Oz//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz8/5CPkP+dnJ3//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5qZmv+AfoH/u7q7//////////////////////////////////X19f+GhIb/aWhq//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5OSk/+enZ7/6urr/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz8/yknKv+pp6n/srGy/5qZmf96d3n/VVRW/xkXGf/Ix8j///////////////////////////////////////////////////////////////////////////////////////////+hoKH/Pz1A/46NkP9/foD/lJKU/1ZUVf9dW1z/OTc5//////////////////////////////////////////////////////////////////////////////////////+/vr//o6Kk/62srv+qqar/rKqr/6moqf+op6j/rays/7GwsP+zsrP/srGx/7CvsP+2trb/u7u8/7y7vP+0tLX/ubi5/7q6u/+3trf/urm6/8zMzf/b29v/zs3N/8rJyf/Kycn/wL6//4SChP+vrq//+Pj4///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/j46Q/6Kgov//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////zs7O/359f/9tbG7//Pz8////////////////////////////tLOz/6alqP9zcnP/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////lJSV/5yam//g4OD////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/ODc4/6alpv+urK3/srGx/3d1d/9PTU//Kikr/5STlP///////////////////////////////////////////////////////////////////////////////////////v7+/3t7fP9QT1P/kpGV/3NxdP+DgoT/TUpM/1JQUf9FREX//////////////////////////////////////////////////////////////////////////////////////7y6u/+vr7D/r66w/6+vsf+vrrD/rayt/7CvsP+xsLH/sK+x/7e2uP+ysLP/s7O0/7i4uf+3trj/t7a5/7Cwsv+ysrT/srG0/7Gxs/+2trj/v77A/7m4uv+qqav/h4WI/3h3ef+enZ7/8PDw//7+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P+Pjo7/oJ+g///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/goGD/56dn/+Qj5H/+vr6/////////////v7+/8vKy/+VlJX/YmFj/93d3f////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+enZ7/o6Gj/9DQ0P////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9VVFX/iIeJ/6CfoP/Mysn/bmxu/1dVVv9DQUP/TUtN//7+/v/////////////////////////////////////////////////////////////////////////////////5+Pn/PDs+/2JhZv+mpaj/dXR2/4B/gf9iYGD/Pz0//2hnaP//////////////////////////////////////////////////////////////////////////////////////wsLC/7y7vP++vr7/vr29/8DAwP+7urv/uLi4/7u7u/+5ubn/wL/A/7u6u/+5uLn/vr2+/7++v//BwcL/wMDA/76+vv+8vLz/u7q7/7q6uv++vb7/wsLC/9bV1v/w8PD//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/5KRkv+enZ7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P/eXh6/6CfoP+TkpP/t7e3/729vf+npqf/lpWX/3p5fP+zsrP//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7Gxsf+enJ7/vLy9/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////4yLjP9WVVf/rKus/9bV1f97eXv/b21w/2BdX/8ZFxr/yMfI/////////////////////////////////////////////////////////////////////////////////8DAwP8gHyP/aGZr/56doP+op6n/amhs/2NhY/8qKSz/lpWW///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/j46P/6Wkpf/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P/kI+Q/3l4ev+DgoT/iIeI/4aEhv90c3X/vb2+//39/f//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////29vb/4eFh/+bmpz//f39////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////zMzM/yooKv/Gxcb/sK+x/7a1t/97en3/VFFU/zIwM/9NTE7/8/Pz///////////////////////////////////////////////////////////////////////x8fH/Q0FD/0ZESf97en7/kI+T/5WUl/9lY2b/cnBy/xkYG//X19f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+TkpP/pqWm///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v3/5+fn/87Nzf9YVlf/1dTU//T08//+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f/fHt9/5ybnf/o6Oj////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P/PTw+/5WUlf+SkZP/5eTm/4KBg/9bWlz/Y2Fk/xkXGf+Afn//+vr6////////////////////////////////////////////////////////////+fn5/3t5ev8gHiL/YV9j/6moq/+gn6L/kI6S/1ZVWP9eXWH/Q0JE//n5+f//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+vr6/5KRkv+sq63//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/2lnZ//+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v+enZ7/qKeo/62trv////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v+Xlpf/PDo8/9DQ0P+sq6z/zs3N/4uJiv85Njb/XFpb/xsaHP+Ih4j/+Pj4//////////////////////////////////////////////////X19f94d3j/Ghga/2hnaf+CgYT/nJue/5CPkf9vbXD/g4KF/yUjJ/+fnp///v7+///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/jYyN/66trv/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/f3/X11f//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+Tk5P96eXr/kpCR/+Hh4f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+vr6/83Njj/mZia/6yrq//S0dH/oJ6e/4yKi/84Njb/VFNW/xwaHv9SUFL/x8bH//T09P/+/v7//////////////////v7+//Py8/+8u7v/SEZH/yAeIf9dW17/c3F0/6Ggo/+vrrH/n56f/2NiZf9oZ2n/Ojk7/+rq6v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+QjpD/qaip//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f9iYWL//v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/6CfoP+mpab/lpWW/+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+//X19f/29vb//v7+/////////////////6+vsP8lIyb/wsHC/5eWlv/j4eL/lJOU/5eVmP9RUFH/WVha/zg2Of8bGh3/SEdI/318ff+enZ7/r66u/6Oio/96eXr/QkFC/xoYG/84Nzv/UE9T/4OChP+Zl5n/srG0/7e2uP91dHb/nJud/yEgI/+rqqv//v7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz7/5STlP+ko6X//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz8/2dlZ//+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/3h3eP+5uLn/o6Ok//Ly8v///////////////////////////////////////////////////////////////////////////////////////////////////////////97e3v+Pjo//jYyO/4qJi/+KiYz/xMTF////////////+/v7/21sbf8+PT//zs3O/5+dnf/X1tf/oJ+h/5aVlv95eHr/RUNG/09OT/9JR0r/ODY5/yYkJv8kIST/Lywu/0lHS/9LSk7/SklN/2loa/+Qj5P/o6Kl/62ssv/W1df/eHd5/62trv8sKy7/Z2Zo//n5+f/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/j46P/5+en//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/Xl1f//7+/v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Pz/2hnaP+0s7X/p6an/+rq6//////////////////////////////////////////////////////////////////////////////////////////////////Y2Nj/hoWH/4eGiP95d3n/fXt+/4mIjP+RkJL/qqqr////////////9/f3/01MTf9MS03/y8rK/5SSkv/m5eX/wcDC/4uJiv+HhYj/h4WH/15cX/86ODz/MS4y/z48P/89Oz7/UE9T/3l4e/+Fg4X/oJ+h/6inqv+trLD/2djb/4GAg/+/v8D/Ojk7/zw7Pf/t7e3///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+Qj5D/oqGi//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////z8/P9mZGb//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9PPz/3d2d/+Uk5X/s7Kz/9TT0//09PT//v7+////////////////////////////////////////////////////////////////////////////9PT0/4SDhP+CgYP/vb29//7+/v/+/v7/2NjY/3d2eP+JiIn/4+Pj////////////6+rq/0xLTP9LSkz/x8XF/4yKiv+1tLX/4N/g/87Nzv+enZ3/joyN/5OSk/+Zl5r/mJeY/5STlf+RkJL/kZCR/6alqP+zsrT/zMvN/6qpq/+amZz/ube5/zs6PP9DQkX/5eXl////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/5CPkP+bmpv//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////Pz7/2dlZv/+/v7/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+Pj4/6SkpP9sa23/pqao/8jHyf+/vr//zc3N/87Ozv/X19f/2dnZ/93c3f/b29v/3Nzc/93d3f/f3t7/29ra/9ra2v/Y2Nj/2NjX/9fX1/+qqar/goGD/5ORk//9/f3/////////////////mJeY/6Sjpf+srKz/////////////////7e3t/29vb/8uLS7/lZSW/7y6u/+rqar/s7Gz/8jHyP/o5+j/6ejp/9jX2P/i4eH/5OPk/93c3v/Ew8X/vr2//6yrrv+npqj/vr6//4KChP8nJin/aWhp/+jo6P/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/kI+Q/52cnf/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////5+fn/ZGJi//7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+jo6P+gn6D/cW9y/39+gf+Uk5b/oaCi/6inqf+joaL/oqGj/5+eoP+ko6X/n56h/6Oipv+dnJ//k5OW/5WUmP+VlJf/kZCT/25tb/+Hhon/rayu//////////////////////+5uLn/np2f/5STlP//////////////////////+fn5/6+urv8zMjT/PjxA/5GQkv/CwcP/yMfJ/7Cvsf+enqD/rKut/6+trv+ko6T/rKut/7++wP/W1db/w8PE/4SEhv83NTr/NzU4/6qpqv/39/f///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/+Rj5D/oJ6f//7+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////r6+f9eXFz//v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/6+vr/6ejp/8fGx/+ysbL/rKut/6inqP+ko6T/pKOk/6ioqP+npqf/pqan/6Oio/+mpab/qKeo/6Wkpf+op6j/iomK/4KBhP+NjI3//v7+/////////////////4OCg/+pqKn/oqGi//////////////////////////////////Dw8P+amZr/OTg7/xoYHf9CQEP/cG9y/4+NkP+lo6b/raus/6Wjpf+KiYv/ZmRl/zc1OP8bGh3/QD9B/6Khov/z8/P//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v7/5OSlP+cm53//v7+////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+/v6/2dlZf/9/f3////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////w8PD/dnV4/5GPkv+wr6//7+/v//Dw8P+4t7f/kI+R/2tpa//j4+P////////////////////////////////////////////7+/v/ysrK/5GRkf9nZmj/S0pM/zo4Ov80MjT/NjU3/0pISv9lZGX/lJOT/9HR0f/8/Pz////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8/Pz/lpWX/6Ggof/+/v7////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/cG5u//7+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/BwcH/dXR2/56doP+bm5z/np2e/5qYmv9pZ2r/rKys///////////////////////////////////////////////////////////////////////+/v7//Pz8//r6+v/8+/v//v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v+xsbP/q6qr//7+/v////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////39/f+Eg4P//v7+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+/v/S0dL/gYCD/2lobP9lZGf/cnBy/8vKyv/+/v7///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////7+//Hx8v/l5eX//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v7+/9jX1//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9/f3/9/f3//b29v/8/Pz/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
"""

def build_app_icon() -> QIcon:
    try:
        data = base64.b64decode(_ICON_B64.strip())
        pm = QPixmap()
        pm.loadFromData(data)
        return QIcon(pm)
    except Exception:
        return QIcon()  # fallback

def export_ico(path: str = "aunssh.ico"):
    """Write the embedded icon as .ico next to the program (for PyInstaller etc.)"""
    try:
        data = base64.b64decode(_ICON_B64.strip())
        with open(path, "wb") as f:
            f.write(data)
    except Exception:
        pass

# ==============================================================================
# Syntax Highlighter
# ==============================================================================
_PY_KW = "False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split()
_JS_KW = "var let const function return if else for while do switch case break continue new delete typeof void null undefined true false this class extends import export default async await yield try catch finally throw".split()
_SH_KW = "if then else elif fi for in do done while case esac function return export source local readonly declare".split()
_C_KW = "auto break case char const continue default do double else enum extern float for goto if int long register return short signed sizeof static struct switch typedef union unsigned void volatile while include define".split()


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
        kw_color, str_color, cmt_color, num_color = "#79c0ff", "#a5d6ff", "#6e7681", "#ff9f0a"
        kwmap = {
            "python": (_PY_KW, r"#[^\n]*"),
            "javascript": (_JS_KW, r"//[^\n]*"),
            "shell": (_SH_KW, r"#[^\n]*"),
            "c": (_C_KW, r"//[^\n]*"),
        }
        if self.lang not in kwmap:
            return
        kws, cmt = kwmap[self.lang]
        for k in kws:
            self.rules.append((QRegularExpression(r"\b" + k + r"\b"), self._fmt(kw_color, True)))
        self.rules += [
            (QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self._fmt(str_color)),
            (QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self._fmt(str_color)),
            (QRegularExpression(cmt), self._fmt(cmt_color)),
            (QRegularExpression(r"\b\d+(\.\d+)?\b"), self._fmt(num_color)),
        ]

    def highlightBlock(self, text):
        if len(text) > 4000:
            return
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ==============================================================================
# File icon cache
# ==============================================================================
_ICON_CACHE: Dict[str, QIcon] = {}


def get_file_icon(name: str) -> QIcon:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in _ICON_CACHE:
        return _ICON_CACHE[ext]
    colors = {
        "py": "#3776ab", "js": "#f7df1e", "ts": "#3178c6", "json": "#cbcb41",
        "html": "#e34c26", "css": "#563d7c", "md": "#519aba", "sh": "#4eaa25",
        "yaml": "#cb171e", "yml": "#cb171e", "sql": "#e38c00", "go": "#00add8",
        "rs": "#dea584", "php": "#777bb4", "rb": "#cc342d", "conf": "#6c8ebf",
        "c": "#555555", "cpp": "#f34b7d", "h": "#a074c4", "txt": "#8a8a99",
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
            assert self.ssh is not None
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            kwargs = dict(hostname=self.host, port=self.port, username=self.user,
                          timeout=10, banner_timeout=10, auth_timeout=15)
            if self.key_path:
                self.ssh.connect(key_filename=self.key_path, **kwargs)
            else:
                self.ssh.connect(password=self.password, look_for_keys=False,
                                 allow_agent=False, **kwargs)
            tr = self.ssh.get_transport()
            if tr:
                tr.set_keepalive(30)  # keep connection responsive (PuTTY-style)
            self._sftp = self.ssh.open_sftp()
            return ""
        except paramiko.AuthenticationException:
            return "Authentication failed - wrong username or password/key"
        except socket.timeout:
            return "Connection timed out"
        except Exception as e:
            return str(e)

    def get_sftp(self) -> paramiko.SFTPClient:
        if not self._sftp or self._sftp.sock is None:
            self._sftp = self.ssh.open_sftp()
        return self._sftp

    def open_shell(self, cols=120, rows=32):
        tr = self.ssh.get_transport()
        chan = tr.open_session()
        chan.get_pty(term="xterm-256color", width=cols, height=rows)
        chan.invoke_shell()
        return chan

    def is_alive(self) -> bool:
        try:
            tr = self.ssh.get_transport()
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
                items.append((a.filename, is_dir, a.st_size or 0))
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
                f.prefetch()
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
# Terminal: reader thread + ANSI-aware widget
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
        while self._run:
            try:
                r, _, _ = select.select([ch], [], [], 0.1)
                if ch in r:
                    if ch.recv_ready():
                        chunk = ch.recv(16384)
                        if not chunk:
                            break
                        self.data.emit(self._decoder.decode(chunk))
                    elif ch.exit_status_ready():
                        break
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


# nicer ANSI 16-color theme (GitHub-dark inspired)
_ANSI_FG = {
    30: "#484f58", 31: "#ff7b72", 32: "#3fb950", 33: "#d29922",
    34: "#58a6ff", 35: "#bc8cff", 36: "#39c5cf", 37: "#b1bac4",
    90: "#6e7681", 91: "#ffa198", 92: "#56d364", 93: "#e3b341",
    94: "#79c0ff", 95: "#d2a8ff", 96: "#56d4dd", 97: "#f0f6fc",
}
_ANSI_BG = {k + 10: v for k, v in _ANSI_FG.items()}
DEFAULT_FG = "#e6edf3"
DEFAULT_BG = "#0d1117"

_SPECIAL_KEYS = {}


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
    """A pragmatic ANSI-aware terminal. Handles colours, line editing, erase,
    cursor moves and clear-screen -- enough for shells, package managers, git,
    tmux line apps. Not a full VT100 grid, but fast and responsive."""

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

    # ---- lifecycle ----
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
            self.reader.wait(800)
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

    # ---- sizing ----
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

    # ---- input ----
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

        # VSCode-style copy / paste
        if ctrl and shift and key == Qt.Key.Key_C:
            self.copy()
            return
        if ctrl and shift and key == Qt.Key.Key_V:
            self._paste()
            return
        if ctrl and key == Qt.Key.Key_Insert:
            self.copy()
            return
        if shift and key == Qt.Key.Key_Insert:
            self._paste()
            return

        if key in _SPECIAL_KEYS:
            self._send(_SPECIAL_KEYS[key])
            return

        if ctrl and not shift and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self._send(bytes([key - Qt.Key.Key_A + 1]))  # Ctrl+C..Ctrl+Z
            return
        if ctrl and key == Qt.Key.Key_Space:
            self._send(b"\x00")
            return
        if ctrl and key == Qt.Key.Key_BracketLeft:
            self._send(b"\x1b")
            return
        if ctrl and key == Qt.Key.Key_Backslash:
            self._send(b"\x1c")
            return

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
        a_copy = m.addAction("Copy\tCtrl+Shift+C")
        a_paste = m.addAction("Paste\tCtrl+Shift+V")
        m.addSeparator()
        a_clear = m.addAction("Clear")
        a_sel = m.addAction("Select All")
        a_copy.triggered.connect(self.copy)
        a_paste.triggered.connect(self._paste)
        a_clear.triggered.connect(self.clear)
        a_sel.triggered.connect(self.selectAll)
        m.exec(self.viewport().mapToGlobal(pos).toPoint())

    # ---- output / ANSI processing ----
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
                    self._pending = s[i:]
                    break
                nxt = s[i + 1]
                if nxt == "[":
                    m = self._csi_re.match(s, i)
                    if not m:
                        self._pending = s[i:]
                        break
                    self._flush(cur, out); out = ""
                    self._handle_csi(cur, m.group(0))
                    i = m.end()
                    continue
                elif nxt == "]":
                    m = self._osc_re.match(s, i)
                    if not m:
                        self._pending = s[i:]
                        break
                    i = m.end()
                    continue
                elif nxt in "()":
                    if i + 2 >= n:
                        self._pending = s[i:]
                        break
                    i += 3
                    continue
                elif nxt == "M":
                    i += 2
                    continue
                else:
                    i += 2
                    continue
            elif c == "\r":
                self._flush(cur, out); out = ""
                cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                i += 1
            elif c == "\n":
                self._flush(cur, out); out = ""
                cur.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cur.insertText("\n")
                i += 1
            elif c == "\b":
                self._flush(cur, out); out = ""
                if not cur.atBlockStart():
                    cur.movePosition(QTextCursor.MoveOperation.Left)
                i += 1
            elif c in ("\x07", "\x00"):
                i += 1
            else:
                out += c
                i += 1
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
            return  # private mode toggles -> ignore
        params = [int(p) if p else 0 for p in body.split(";")] if body else []

        if final == "m":
            self._apply_sgr(params or [0])
        elif final == "K":  # erase line
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
        elif final == "J":  # erase display
            mode = params[0] if params else 0
            if mode in (2, 3):
                self.clear()
                cur.movePosition(QTextCursor.MoveOperation.End)
            else:
                cur.movePosition(QTextCursor.MoveOperation.End,
                                 QTextCursor.MoveMode.KeepAnchor)
                cur.removeSelectedText()
        elif final == "C":  # cursor forward
            for _ in range(max(1, params[0] if params else 1)):
                if cur.atBlockEnd():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Right)
        elif final == "D":  # cursor back
            for _ in range(max(1, params[0] if params else 1)):
                if cur.atBlockStart():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Left)
        elif final in ("G", "`"):  # column absolute
            col = (params[0] if params else 1) - 1
            cur.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            for _ in range(col):
                if cur.atBlockEnd():
                    break
                cur.movePosition(QTextCursor.MoveOperation.Right)
        # A/B/H and others: best-effort ignore (no full grid)

    def _apply_sgr(self, params: List[int]):
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self._fmt = QTextCharFormat()
                self._fmt.setForeground(QColor(DEFAULT_FG))
            elif p == 1:
                self._fmt.setFontWeight(700)
            elif p == 22:
                self._fmt.setFontWeight(400)
            elif p in (3,):
                self._fmt.setFontItalic(True)
            elif p in (4,):
                self._fmt.setFontUnderline(True)
            elif p in (23,):
                self._fmt.setFontItalic(False)
            elif p in (24,):
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
                    r, g, b = _xterm256(params[i + 2])
                    i += 2
                elif i + 1 < len(params) and params[i + 1] == 2 and i + 4 < len(params):
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]
                    i += 4
                else:
                    i += 1
                    continue
                col = QColor(r, g, b)
                if is_fg:
                    self._fmt.setForeground(col)
                else:
                    self._fmt.setBackground(col)
            i += 1


# ==============================================================================
# Find / Replace bar (editor)
# ==============================================================================
class FindBar(QWidget):
    def __init__(self, editor: QPlainTextEdit, parent=None):
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

        prev_b = QToolButton(); prev_b.setText("▲"); prev_b.setToolTip("Previous (Shift+Enter)")
        prev_b.clicked.connect(self.find_prev)
        next_b = QToolButton(); next_b.setText("▼"); next_b.setToolTip("Next (Enter)")
        next_b.clicked.connect(self.find_next)
        self.toggle_rep = QToolButton(); self.toggle_rep.setText("⇄"); self.toggle_rep.setCheckable(True)
        self.toggle_rep.setToolTip("Toggle replace")
        self.toggle_rep.toggled.connect(self._toggle_replace)
        close_b = QToolButton(); close_b.setText("✕"); close_b.setToolTip("Close (Esc)")
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
        self.editor.setExtraSelections([])
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
            while True:
                cur = doc.find(text, cur, self._flags())
                if cur.isNull():
                    break
                count += 1
                sel = QPlainTextEdit.ExtraSelection()
                sel.cursor = cur
                sel.format = fmt
                selections.append(sel)
        self.editor.setExtraSelections(selections)
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
        if cur.hasSelection() and (
            cur.selectedText() == self.find_in.text() or
            (not self.case_cb.isChecked() and cur.selectedText().lower() == self.find_in.text().lower())
        ):
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
        self.setFixedSize(440, 470)
        self.session: Optional[SSHSession] = None
        self.config = load_config()
        self.use_key = False
        self._loading = False

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

        # saved profiles
        prof_row = QHBoxLayout()
        prof_row.addWidget(QLabel("Saved:"))
        self.profile_cb = QComboBox()
        self.profile_cb.addItem("— New connection —", None)
        for p in self.config.get("profiles", []):
            self.profile_cb.addItem(p.get("name") or p.get("host", ""), p)
        self.profile_cb.currentIndexChanged.connect(self._load_profile)
        prof_row.addWidget(self.profile_cb, 1)
        self.del_btn = QToolButton(); self.del_btn.setText("🗑")
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
        self.show_btn = QToolButton(); self.show_btn.setText("👁"); self.show_btn.setCheckable(True)
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

        warn = QLabel("Saved credentials are stored locally (base64, not encrypted).")
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

        # auto-load last used profile
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
        self._loading = True
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
        self._loading = False

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
        except ValueError:
            port = 22

        password = key_path = ""
        if self.use_key:
            key_path = self.auth_in.text().strip()
        else:
            password = self.auth_in.text()

        # persist profile
        name = f"{user}@{host}"
        profile = {
            "name": name, "host": host, "port": port, "user": user,
            "auth": "key" if self.use_key else "password",
            "remember": self.remember_cb.isChecked(),
            "key_path": key_path if self.remember_cb.isChecked() else "",
            "password": _b64e(password) if (self.remember_cb.isChecked() and not self.use_key) else "",
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
        self.modified = False
        self._workers: List[QThread] = []
        self.current_file = None
        self._highlighter = None
        self._loading_file = False
        self.terminal: Optional[SSHTerminal] = None
        self.news_manager = None

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
            home = session.get_sftp().normalize(".")
        except Exception:
            home = "/"
        self._list_dir(home)

    # ---------- UI build ----------
    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(4)
        root.setContentsMargins(6, 6, 6, 6)

        # path bar
        path_bar = QHBoxLayout()
        path_bar.setSpacing(4)
        self.home_btn = QPushButton("⌂ Home"); self.home_btn.setFixedWidth(90)
        self.home_btn.clicked.connect(self._go_home)
        path_bar.addWidget(self.home_btn)
        self.up_btn = QPushButton("↑ Up"); self.up_btn.setFixedWidth(70)
        self.up_btn.clicked.connect(self._go_up)
        path_bar.addWidget(self.up_btn)
        self.refresh_btn = QPushButton("⟳"); self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.setToolTip("Refresh (F5)")
        self.refresh_btn.clicked.connect(lambda: self._list_dir(self.current_path))
        path_bar.addWidget(self.refresh_btn)
        self.path_in = QLineEdit(); self.path_in.setFont(QFont(MONO, 10))
        self.path_in.returnPressed.connect(self._go_path)
        path_bar.addWidget(self.path_in, 1)
        go_btn = QPushButton("Go"); go_btn.setFixedWidth(60)
        go_btn.clicked.connect(self._go_path)
        path_bar.addWidget(go_btn)
        root.addLayout(path_bar)

        # news banner placeholder (row index 1)
        root.addWidget(QWidget())  # spacer replaced by news container

        # main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # left: file list
        self.file_list = QListWidget()
        self.file_list.setFont(QFont(MONO, 10))
        self.file_list.setIconSize(QSize(16, 16))
        self.file_list.itemDoubleClicked.connect(self._on_item_double_click)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._context_menu)
        splitter.addWidget(self.file_list)

        # right: vertical splitter (editor on top, bottom panel below)
        right_split = QSplitter(Qt.Orientation.Vertical)

        # editor area
        editor_area = QWidget()
        ea = QVBoxLayout(editor_area)
        ea.setContentsMargins(0, 0, 0, 0); ea.setSpacing(2)
        self.file_info_lbl = QLabel("No file selected")
        self.file_info_lbl.setStyleSheet("font-size:10px; padding:2px 6px;")
        ea.addWidget(self.file_info_lbl)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont(MONO, 11))
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.document().modificationChanged.connect(self._on_modification_changed)

        self.find_bar = FindBar(self.editor)
        ea.addWidget(self.find_bar)
        ea.addWidget(self.editor, 1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        self.save_btn = QPushButton("💾 Save  Ctrl+S"); self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_file)
        btn_row.addWidget(self.save_btn)
        self.find_btn = QPushButton("🔍 Find  Ctrl+F"); self.find_btn.setEnabled(False)
        self.find_btn.clicked.connect(lambda: self.find_bar.show_bar())
        btn_row.addWidget(self.find_btn)
        self.close_btn = QPushButton("✕ Close"); self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self._close_file)
        btn_row.addWidget(self.close_btn)
        btn_row.addStretch()
        ea.addLayout(btn_row)
        right_split.addWidget(editor_area)

        # bottom panel: tabs (Terminal / Logs)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setTabPosition(QTabWidget.TabPosition.North)

        term_wrap = QWidget()
        tw = QVBoxLayout(term_wrap)
        tw.setContentsMargins(0, 0, 0, 0); tw.setSpacing(2)
        term_toolbar = QHBoxLayout(); term_toolbar.setSpacing(4)
        self.term_restart_btn = QPushButton("⟳ Restart shell")
        self.term_restart_btn.clicked.connect(self._restart_terminal)
        self.term_clear_btn = QPushButton("Clear")
        self.term_clear_btn.clicked.connect(self._clear_terminal)
        term_toolbar.addWidget(self.term_restart_btn)
        term_toolbar.addWidget(self.term_clear_btn)
        term_toolbar.addStretch()
        hint = QLabel("Ctrl+Shift+C copy · Ctrl+Shift+V paste · Ctrl+C interrupt")
        hint.setStyleSheet("color:#6e7681; font-size:10px;")
        term_toolbar.addWidget(hint)
        tw.addLayout(term_toolbar)
        self.terminal = SSHTerminal(self.session, log_fn=self.log)
        tw.addWidget(self.terminal, 1)
        self.bottom_tabs.addTab(term_wrap, "Terminal")

        # logs tab
        logs_wrap = QWidget()
        lw = QVBoxLayout(logs_wrap)
        lw.setContentsMargins(0, 0, 0, 0); lw.setSpacing(2)
        log_toolbar = QHBoxLayout(); log_toolbar.setSpacing(4)
        self.log_copy_btn = QPushButton("📋 Copy logs")
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

        # status bar with connection indicator + reconnect
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.conn_dot = QLabel("●")
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

        # shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self, self._save_file)
        QShortcut(QKeySequence("Ctrl+F"), self, self._show_find)
        QShortcut(QKeySequence("Ctrl+H"), self, self._show_replace)
        QShortcut(QKeySequence("F5"), self, lambda: self._list_dir(self.current_path))
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_file)
        QShortcut(QKeySequence("Ctrl+`"), self, self._focus_terminal)
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
        alive = self.session.is_alive()
        if alive:
            self.conn_dot.setStyleSheet("color:#3fb950; font-size:14px;")
            self.conn_text.setText(f"Connected · {self.session.user}@{self.session.host}")
            self.reconnect_btn.setEnabled(True)
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
        self.worker = ConnectWorker(old.host, old.port, old.user, old.password, old.key_path)
        self.worker.success.connect(self._on_reconnected)
        self.worker.failed.connect(self._on_reconnect_failed)
        self.worker.start()

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

    # ---------- find ----------
    def _show_find(self):
        if self.current_file:
            self.find_bar.show_bar(replace=False)

    def _show_replace(self):
        if self.current_file:
            self.find_bar.show_bar(replace=True)

    # ---------- news ----------
    def _setup_news_banner(self):
        news_container = QWidget()
        nl = QHBoxLayout(news_container)
        nl.setContentsMargins(0, 0, 0, 0); nl.setSpacing(4)
        self.news_label = QLabel()
        self.news_label.setStyleSheet(
            "QLabel{background:#1f2a3e;color:#79c0ff;padding:4px 8px;"
            "font-size:11px;border-radius:4px;}")
        self.news_label.setWordWrap(True)
        self.news_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.news_label.setOpenExternalLinks(True)
        self.news_close = QPushButton("✕"); self.news_close.setFixedSize(20, 20)
        self.news_close.clicked.connect(lambda: self.news_container.hide())
        nl.addWidget(self.news_label, 1); nl.addWidget(self.news_close)
        # replace the spacer at index 1
        lay = self.centralWidget().layout()
        old = lay.itemAt(1).widget()
        if old:
            old.setParent(None)
        lay.insertWidget(1, news_container)
        self.news_container = news_container
        self.news_container.hide()
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
                    disp = (f'📢 <a href="{link}" style="color:#79c0ff;'
                            f'text-decoration:none;">{text}</a>') if link else f"📢 {text}"
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
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)

    def _go_home(self):
        try:
            home = self.session.get_sftp().normalize(".")
        except Exception:
            home = "/"
        self._list_dir(home)

    def _go_up(self):
        self._list_dir(os.path.dirname(self.current_path.rstrip("/")) or "/")

    def _go_path(self):
        path = self.path_in.text().strip()
        if not path:
            return
        if not path.startswith("/"):
            path = self.current_path.rstrip("/") + "/" + path
        path = os.path.normpath(path).replace("\\", "/")
        if not self.session.is_alive():
            QMessageBox.critical(self, "Error", "Connection lost"); return
        try:
            self.session.get_sftp().stat(path)
            self._list_dir(path)
        except FileNotFoundError:
            QMessageBox.warning(self, "Not Found", path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _list_dir(self, path: str):
        if not self.session.is_alive():
            self.show_msg("Connection lost - please reconnect"); return
        self.current_path = path
        self.path_in.setText(path)
        self.show_msg(f"Loading {path}...")
        self.file_list.clear()
        w = DirWorker(self.session, path)
        w.done.connect(self._populate_list)
        w.failed.connect(lambda e: (self.show_msg(f"Error: {e}"), self.log("ERROR", e)))
        self._track_worker(w)
        w.start()

    def _populate_list(self, path: str, items: list):
        self.current_path = path
        self.path_in.setText(path)
        self.show_msg(f"{path}  ({len(items)} items)")
        self.file_list.clear()
        for name, is_dir, size in items:
            it = QListWidgetItem(f"{name}{'/' if is_dir else ''}")
            it.setIcon(get_folder_icon() if is_dir else get_file_icon(name))
            it.setData(Qt.ItemDataRole.UserRole, {
                "name": name, "is_dir": is_dir,
                "path": path.rstrip("/") + "/" + name, "size": size})
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
            QMessageBox.critical(self, "Error", "Connection lost"); return
        if self.modified:
            if QMessageBox.question(
                self, "Unsaved changes",
                "Current file has unsaved changes. Open anyway?",
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
        self.file_info_lbl.setText(f"Editing: {path}")
        self.editor.setReadOnly(False)
        self.editor.setPlainText(content)
        self.editor.document().setModified(False)
        self._loading_file = False
        self.save_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        self.find_btn.setEnabled(True)
        self.show_msg(f"Opened: {path}")
        self.log("INFO", f"Opened {path}")

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = ("python" if ext in ("py", "pyw") else
                "javascript" if ext in ("js", "ts", "jsx", "tsx") else
                "shell" if ext in ("sh", "bash") else
                "c" if ext in ("c", "h", "cpp", "hpp", "cc") else
                "plain")
        if self._highlighter:
            self._highlighter.setDocument(None)
        self._highlighter = SimpleHighlighter(self.editor.document(), lang)

    def _on_file_error(self, path: str, error: str):
        QMessageBox.warning(self, "Error", f"Cannot open {path}\n\n{error}")
        self.show_msg("Open failed")
        self.log("ERROR", f"Open {path}: {error}")

    def _on_modification_changed(self, modified: bool):
        if self._loading_file:
            return
        self.modified = modified
        if self.current_file:
            self.file_info_lbl.setText(f"{'* ' if modified else ''}Editing: {self.current_file}")

    def _save_file(self):
        if not self.current_file or not self.modified:
            return
        content = self.editor.toPlainText()
        self.show_msg(f"Saving {self.current_file}...")
        w = SaveFileWorker(self.session, self.current_file, content)
        w.done.connect(self._on_saved)
        w.failed.connect(lambda e: (QMessageBox.critical(self, "Save Failed", str(e)),
                                    self.log("ERROR", f"Save failed: {e}")))
        self._track_worker(w)
        w.start()

    def _on_saved(self, path: str):
        self.editor.document().setModified(False)
        fn = os.path.basename(path)
        self.show_msg(f"✓ Saved: {fn}")
        self.log("INFO", f"Saved {path}")
        QTimer.singleShot(3000, lambda: self.show_msg(f"Ready - {self.current_path}"))

    def _close_file(self):
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
        if self._highlighter:
            self._highlighter.setDocument(None)
            self._highlighter = None

    # ---------- context menu / fs ops ----------
    def _context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        menu = QMenu(self)
        menu.addAction("📄 New File", self._new_file)
        menu.addAction("📁 New Folder", self._new_folder)
        menu.addAction("⟳ Refresh", lambda: self._list_dir(self.current_path))
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                menu.addSeparator()
                menu.addAction("✏ Rename...", lambda: self._rename(data["path"]))
                menu.addAction("🗑 Delete", lambda: self._delete(data["path"], data["is_dir"]))
        menu.exec(self.file_list.viewport().mapToGlobal(pos).toPoint())

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if not ok or not name.strip():
            return
        path = self.current_path.rstrip("/") + "/" + name.strip()
        try:
            with self.session.get_sftp().open(path, "w") as f:
                f.write(b"")
            self._list_dir(self.current_path)
            self.log("INFO", f"Created file {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        try:
            self.session.get_sftp().mkdir(self.current_path.rstrip("/") + "/" + name.strip())
            self._list_dir(self.current_path)
            self.log("INFO", f"Created folder {name.strip()}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _rename(self, old_path: str):
        name, ok = QInputDialog.getText(self, "Rename", "New name:",
                                        text=os.path.basename(old_path))
        if not ok or not name.strip():
            return
        new_path = os.path.dirname(old_path.rstrip("/")) + "/" + name.strip()
        try:
            self.session.get_sftp().rename(old_path, new_path)
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
            self.log("INFO", f"Deleted {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------- close ----------
    def closeEvent(self, event):
        if self.modified:
            if QMessageBox.question(
                self, "Exit", "There are unsaved changes. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                event.ignore(); return
        if self.terminal:
            self.terminal.stop()
        self.session.close()
        event.accept()


# ==============================================================================
# Theme
# ==============================================================================
DARK_THEME = """
    QMainWindow, QWidget {
        background:#0d1117; color:#e6edf3;
        font-family:'Segoe UI','Ubuntu',sans-serif; font-size:12px;
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
"""


def main():
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland*=false"
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(build_app_icon())

    # write an .ico next to the program for packaging (best-effort, ignored if fails)
    try:
        export_ico(str(Path(__file__).with_name("aunssh.ico")))
    except Exception:
        pass

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    win = MainWindow(login.session)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()