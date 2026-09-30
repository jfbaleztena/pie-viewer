# Cómo Ejecutar la Aplicación

## Primero: Configurar Entorno

```bash
cd pie-viewer
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

## Ejecutar la Aplicación

```bash
# Opción 1 (RECOMENDADO)
python -m src.main

# Opción 2
python src/main.py
```

## Usar la Aplicación

### Cargar STL
- Menú: Archivo → Abrir STL
- Atajo: Ctrl+O

### Cambiar Vistas
- Panel derecho: 7 botones grandes
- Menú: Ver → [Nombre de vista]
- Barra de herramientas: Iconos de vista

### Interactuar con la Malla
- **Rotación**: Click derecho + arrastrar
- **Zoom**: Rueda del mouse
- **Pan**: Click central + arrastrar

## Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt6'"
```bash
pip install PyQt6==6.7.1
```

### "ModuleNotFoundError: No module named 'vtkmodules'"
```bash
pip install VTK==9.3.0
```

### Ventana no aparece
1. ¿Activaste el venv?
2. ¿Instalaste dependencias?
3. ¿Ejecutas con `python -m src.main`?

## Tests

```bash
python -m pytest tests/test_mesh_loader.py -v
python -m pytest tests/test_integration.py -v
```

Resultado esperado: 24/24 tests passing

