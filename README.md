# Sistema de Visualización de Pies 3D

Aplicación desktop para visualizar y analizar modelos 3D de pies obtenidos mediante el escáner Creality CR-Scan Ferret Pro.

## Características Sprint 1

- ✅ Importar archivos STL (ASCII y Binary)
- ✅ Visualizar modelo 3D con VTK
- ✅ 7 vistas estándar predefinidas (Dorsal, Plantar, Medial, Lateral, Anterior, Posterior, Isométrica)
- ✅ Interacción: rotación (click derecho + drag), zoom (rueda), pan (click central)
- ✅ Información de malla en tiempo real
- ✅ Validación robusta de geometría
- ✅ Manejo de errores completo

## Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
.\venv\Scripts\activate

# Activar entorno (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
# Ejecutar aplicación
python -m src.main

# O directamente
python src/main.py
```

## Pruebas

```bash
# Tests unitarios
python -m pytest tests/test_mesh_loader.py -v

# Tests de integración
python -m pytest tests/test_integration.py -v

# Todos los tests
python -m pytest tests/ -v
```

## Documentación

- `RUN_APPLICATION.md` - Guía de uso detallada
- `ARQUITECTURA.md` - Diseño técnico
- `ROADMAP.md` - Plan de desarrollo

## Próximas Fases

- Sprint 2: Plano de apoyo + Color mapping
- Sprint 3: Mediciones y anotaciones
- Sprint 4: Comparación bilateral y reportes

