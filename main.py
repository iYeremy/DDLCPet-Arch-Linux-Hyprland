import os
import sys
from PyQt6.QtWidgets import QApplication
from deskpet.core import DeskPet

# Forzar backend X11 para Hyprland
os.environ["QT_QPA_PLATFORM"] = "xcb"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    screen = app.primaryScreen().geometry()

    pet = DeskPet(screen)
    pet.show()

    sys.exit(app.exec())
