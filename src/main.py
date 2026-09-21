"""
Aplicación Principal - Sistema de Visualización de Pies
Punto de entrada de la aplicación
"""
import sys
from pathlib import Path

# Agregar src al path para poder importar módulos locales
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger


def main():
    """Función principal de la aplicación"""
    # Configurar logging
    logger = setup_logger(__name__)
    logger.info("Iniciando Sistema de Visualización de Pies...")

    # Crear aplicación Qt
    app = QApplication(sys.argv)
    app.setApplicationName("Visualizador de Pies")
    app.setApplicationVersion("0.1.0")

    # Crear ventana principal
    window = MainWindow()
    window.show()

    logger.info("Aplicación iniciada correctamente")

    # Ejecutar loop de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
