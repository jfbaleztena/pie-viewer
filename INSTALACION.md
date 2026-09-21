# Instalación y Configuración - Sistema de Visualización de Pies

## Estado: ✅ LISTO PARA INSTALAR

El proyecto completo está en: `C:\Users\juanf\OneDrive\Escritorio\FM Ortopedia\pie-viewer`

## Pasos de Instalación

### 1. Abrir Terminal/PowerShell

```
Windows: Win + R → cmd o PowerShell
```

### 2. Navegar al Directorio

```bash
cd "C:\Users\juanf\OneDrive\Escritorio\FM Ortopedia\pie-viewer"
```

### 3. Crear Entorno Virtual

```bash
python -m venv venv
```

### 4. Activar Entorno Virtual

```bash
# Windows:
.\venv\Scripts\activate

# Deberías ver: (venv) en tu terminal
```

### 5. Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Esto instalará:**
- PyQt6 6.7.1 (UI framework)
- VTK 9.3.0 (3D rendering)
- NumPy 1.24.3 (Matemática)
- SciPy 1.11.3 (Geometría)
- pytest 7.4.3 (Testing)

### 6. Ejecutar la Aplicación

```bash
python -m src.main
```

## Primeros Pasos en la App

1. **Cargar un STL:**
   - Menú: Archivo → Abrir STL
   - O: Ctrl+O
   - Selecciona un archivo .stl

2. **Ver diferentes perspectivas:**
   - Usa los 7 botones del panel derecho
   - O el menú Ver

3. **Interactuar:**
   - Click derecho + drag: Rotar
   - Rueda mouse: Zoom
   - Click central + drag: Desplazar

## Verificar que Todo Funciona

```bash
# Tests unitarios (MeshLoader)
python -m pytest tests/test_mesh_loader.py -v

# Tests de integración
python -m pytest tests/test_integration.py -v

# Todos los tests
python -m pytest tests/ -v
```

Resultado esperado: **24/24 tests passing ✅**

## Estructura del Proyecto

```
pie-viewer/
├── src/
│   ├── core/
│   │   └── mesh_loader.py      # Carga STL (ASCII + Binary)
│   ├── ui/
│   │   ├── main_window.py      # Ventana principal
│   │   └── widgets/
│   │       └── view_3d.py      # Canvas VTK
│   ├── models/
│   │   └── foot_model.py       # Estructura de datos
│   ├── utils/
│   │   ├── constants.py        # Configuración
│   │   └── logger.py           # Logging
│   └── main.py                 # Punto de entrada
├── tests/
│   ├── test_mesh_loader.py     # 13 tests unitarios
│   └── test_integration.py     # 11 tests integración
├── requirements.txt            # Dependencias
├── README.md                   # Descripción general
├── QUICK_START.md             # Inicio rápido
└── RUN_APPLICATION.md         # Guía de uso
```

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'PyQt6'"
```bash
pip install PyQt6==6.7.1
```

### Error: "ModuleNotFoundError: No module named 'vtkmodules'"
```bash
pip install VTK==9.3.0
```

### Error: "Ventana no aparece"
1. Verifica que el venv esté activado: `(venv)` debe verse en la terminal
2. Verifica que instalaste todo: `pip list | findstr PyQt6`
3. Ejecuta de nuevo: `python -m src.main`

### Error: "No module named 'src'"
- Asegúrate de estar en el directorio `pie-viewer`
- Verifica: `ls src/` (debe mostrar core, ui, models, utils, main.py)

## Próximos Pasos (Sprint 2)

Una vez verificado que todo funciona:

1. **Plano de Apoyo Personalizado:**
   - Permitir al usuario seleccionar 3 puntos en la malla
   - Definir automáticamente el plano de apoyo

2. **Mapa de Colores:**
   - Colorear la malla según distancia al plano
   - Mostrar mapa de presión relativa

3. **Mediciones:**
   - Distancia entre puntos
   - Ángulos
   - Área de superficie

4. **Anotaciones:**
   - Marcar puntos importantes
   - Notas asociadas

## Soporte

Revisar documentación incluida:
- `README.md` - Descripción general
- `QUICK_START.md` - Inicio rápido (5 minutos)
- `RUN_APPLICATION.md` - Guía detallada de uso
- `ARQUITECTURA.md` - Diseño técnico (en proyecto)

¡La aplicación está lista para usar! 🚀
