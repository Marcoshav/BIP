# -*- coding: utf-8 -*-
"""
Bip - mascota flotante de escritorio para Windows.
Sólo depende de PyQt6. Ejecutar:  pythonw bip.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QLockFile
from PyQt6.QtGui import QPainter, QPixmap, QIcon, QColor, QPen
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox

from bip_sistema import APP_DIR, SysInfo, install_excepthook, __version__
from bip_ui import PetUI
from bip_cerebro import PetBrain
from bip_pensar import PetThink
from bip_conductas import Conductas
from bip_juegos import Juegos
from bip_tarjeta import PetMedia
from bip_charla import PetCharla


class Pet(PetUI, PetBrain, PetThink, Conductas, Juegos, PetMedia, PetCharla):
    BEHAVIORS = {**Conductas.BEHAVIORS, **Juegos.BEHAVIORS}

    def __init__(self, offline=False):
        super().__init__()
        self.init_ui()
        self.init_brain(offline, os.path.abspath(__file__))
        self.init_think()
        self.init_charla()
        self.init_media(offline)
        self.sc_t = 1.0
        self.start_timers()
        QTimer.singleShot(900, self.greet)


def tray_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(89, 242, 255), 3))
    p.setBrush(QColor("#171a22"))
    p.drawRoundedRect(QRectF(5, 12, 54, 40), 14, 14)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(89, 242, 255))
    p.drawRoundedRect(QRectF(18, 24, 9, 14), 4, 4)
    p.drawRoundedRect(QRectF(37, 24, 9, 14), 4, 4)
    p.end()
    return QIcon(pm)


def main():
    install_excepthook()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Bip")
    SysInfo.dpr = app.primaryScreen().devicePixelRatio()
    os.makedirs(APP_DIR, exist_ok=True)
    lock = QLockFile(os.path.join(APP_DIR, "bip.lock"))
    lock.setStaleLockTime(5000)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Bip", "Bip ya está corriendo. Buscalo flotando en tu pantalla.")
        return 0
    pet = Pet()
    pet.show()
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(tray_icon(), app)
        tray.setToolTip("Bip v%s" % __version__)
        menu = QMenu()
        menu.addAction("Mostrar / ocultar", lambda: pet.setVisible(not pet.isVisible()))
        menu.addAction("Darle mimos", pet.menu_pet)
        menu.addSeparator()
        menu.addAction("Salir", pet.quit_app)
        tray.setContextMenu(menu)
        tray.show()
    app.aboutToQuit.connect(pet.save)
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
