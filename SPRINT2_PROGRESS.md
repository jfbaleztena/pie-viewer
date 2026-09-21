# Sprint 2 - Progreso

## Nota sobre el contexto de la tarea

La consigna original referenciaba `claude/ARQUITECTURA.md`, `claude/ROADMAP.md` y
`claude/SPRINT1_PROGRESS.md` como documentación de diseño ya existente. Esos
archivos **no existen** en el repo (`pie-viewer/`) — se buscaron en todo el
disco y no aparecieron (solo se encontró un `pie-viewer-sprint1.tar.gz` que
resultó ser un placeholder de 12 bytes, no un archivo comprimido real).

Por lo tanto este sprint se construyó leyendo directamente el código de
Sprint 1 (`mesh_loader.py`, `view_3d.py`, `main_window.py`, `foot_model.py`,
`tests/`) en lugar de la documentación de arquitectura. El repo tampoco tiene
Git inicializado (`.git` no existe), así que no se generaron commits.

## Resumen de lo implementado

1. **Soporte OBJ en `MeshLoader`** (además de STL, que ya existía).
2. **Picking de puntos en la vista 3D** con `vtkCellPicker`.
3. **Plano de apoyo**: click en 3 puntos de la base → se calcula el plano.
4. **Altura del arco**: click manual en el punto más alto del arco → distancia
   perpendicular al plano. Se pueden tomar **varias mediciones de altura**
   sin perder las anteriores (útil para medir en distintos puntos del arco).
5. **Distancia en el plano de apoyo**: click en 2 puntos → distancia entre
   sus proyecciones sobre el plano (ignora diferencias de altura entre
   ambos puntos). Pensado para medir extensiones de la superficie de apoyo
   (ancho, largo de la zona de contacto), no solo la altura del arco.
6. **Mediciones acumulables**: todas las mediciones (altura y distancia) se
   guardan en una lista (`MainWindow.measurements`, usando la clase
   `Measurement` ya definida en `foot_model.py` desde Sprint 1) y se listan
   juntas en el texto superpuesto del canvas, no se pisan entre sí.
7. **Visualización**: marcadores de los puntos clickeados (colores distintos
   por tipo de medición), líneas entre los puntos relevantes de cada
   medición (todas visibles a la vez, no solo la última), plano
   semi-transparente, texto superpuesto en el canvas con todas las
   mediciones y mensaje en la status bar.
8. Tres botones en la toolbar existente: **"Definir plano de apoyo"**,
   **"Medir altura del arco"** y **"Medir distancia en el plano"**
   (checkeables, mutuamente excluyentes, sin paneles nuevos).
9. **Tabla de mediciones** en el panel derecho (2 columnas: nombre y valor),
   con click derecho sobre una fila → "Eliminar medición". Borra la
   medición de la lista, de la tabla y sus marcadores/línea del canvas, sin
   afectar al resto.
10. **Plano de apoyo dimensionado a la huella real** de la malla (antes era
    un tamaño fijo aproximado, centrado en uno de los 3 puntos clickeados,
    que podía quedar chico o descentrado respecto al pie).
11. **Encuadre de cámara automático** al cargar una malla o cambiar de vista
    (antes usaba una distancia fija que podía dejar la malla recortada,
    obligando a hacer zoom out a mano).
12. **Mapa de calor de altura** (toggle "Mapa de calor" en la toolbar):
    colorea toda la malla (no solo puntos puntuales) según su distancia al
    plano de apoyo — azul cerca del plano, rojo en los puntos más altos.
    Reactiva `VTK3DView.set_vertex_colors()`, que existía sin usar desde
    Sprint 1 (ver bug #9 sobre por qué no funcionaba tal cual estaba).
13. **Exportar mediciones a CSV** y **exportar informe a PDF** (menú
    Archivo): el PDF incluye una captura de la vista 3D actual (malla +
    plano + marcadores) más la tabla de mediciones.
14. **Guardar/abrir proyecto** (menú Archivo, `.json`): persiste la ruta a
    la malla original, los 3 puntos del plano y todas las mediciones. Al
    abrir, vuelve a cargar la malla con `MeshLoader` y reconstruye plano +
    marcadores + líneas de cada medición.
15. **Botón "Mostrar plano"**: oculta/muestra el plano de apoyo sin borrarlo
    (`actor.SetVisibility()`) — el plano y las mediciones que dependen de él
    siguen intactos, solo cambia si se dibuja o no.
16. **Color distinto para la cara posterior de la malla** (`SetBackfaceProperty`):
    ayuda a notar cuándo se está mirando la malla "del lado de adentro" en
    vez de confundir la parte superior con la inferior — útil en un escaneo
    de una sola cara como el de un pie apoyado sobre una placa de vidrio.
17. **Previsualización al pickear**: mientras un modo de selección está
    activo (plano/altura/distancia), una esfera semi-transparente sigue al
    cursor mostrando dónde caería el click antes de confirmarlo.
18. **Advertencias de escala/geometría visibles**: `MeshLoader` ya calculaba
    `validation_warnings` (escala inusual, malla muy grande, triángulos
    degenerados) desde Sprint 1, pero nunca se mostraban en ningún lado — se
    calculaban y se descartaban en silencio. Ahora se avisan con un diálogo
    al cargar, salvo en el caso normal ("MILÍMETROS, pie normal") para no
    interrumpir en el caso esperado.
19. **Deshacer (`Ctrl+Z`)**: durante la selección de 3 puntos del plano o 2
    de una distancia, deshace el último click. Si no hay una selección a
    medio hacer, deshace la última medición completa (reusa el borrado
    individual ya existente).
20. **Confirmación al cerrar con mediciones sin guardar**: ofrece
    Guardar/Descartar/Cancelar. Si el usuario cancela el diálogo de guardado
    (ej. cierra el file picker sin elegir archivo), la ventana no se cierra,
    para no perder mediciones por accidente.
21. **Nombres de medición editables**: doble click en la columna "Medición"
    de la tabla para renombrar (ej. "Altura arco 1" → "Talón"). La columna
    "Valor" sigue sin ser editable (es un dato calculado).
22. **Atajos de teclado**: `Escape` cancela el modo de picking activo, `Supr`
    borra la medición seleccionada en la tabla (además del click derecho ya
    existente).
23. **Toggle de ejes de coordenadas** (botón "Ejes"): reactiva `show_axes()`,
    otro método de Sprint 1 que existía sin conectar a ningún botón.

## Archivos nuevos

- [src/core/measurements.py](src/core/measurements.py) — `compute_support_plane()`,
  `compute_arch_height()`, `compute_plane_distance()`,
  `compute_plane_footprint()` (centro + dimensiones del rectángulo que cubre
  la huella de la malla sobre el plano), `compute_height_map()` (altura de
  cada vértice, vectorizado, para el mapa de calor) y `height_map_to_colors()`
  (gradiente azul→verde→rojo). Todo desacoplado de Qt/VTK (mismo criterio
  que `mesh_loader.py`) para poder testearlo sin entorno gráfico.
- [src/core/report_export.py](src/core/report_export.py) — `export_measurements_csv()`
  y `export_report_pdf()` (usa `reportlab`, nueva dependencia — agregada a
  `requirements.txt`). Reciben la lista de `Measurement` y, para el PDF, la
  ruta a un PNG ya capturado; no dependen de ningún objeto de UI.
- [src/core/project_io.py](src/core/project_io.py) — `save_project()` /
  `load_project()`: serializan a JSON la ruta a la malla original, los 3
  puntos del plano y las mediciones (no la malla en sí, se vuelve a leer con
  `MeshLoader` al abrir).
- [tests/test_measurements.py](tests/test_measurements.py) — 25 tests del
  cálculo geométrico (plano desde 3 puntos, normal unitaria, colinealidad,
  distancia punto-plano, proyección, distancia entre proyecciones, footprint
  del plano, mapa de alturas, colores del mapa de calor).
- [tests/test_report_export.py](tests/test_report_export.py) — 7 tests
  (CSV con/sin mediciones, PDF con/sin mediciones, PDF con captura faltante,
  PDF a varias páginas).
- [tests/test_project_io.py](tests/test_project_io.py) — 4 tests (round-trip
  con/sin plano, orden de mediciones preservado, archivo inválido).

## Archivos modificados

- [src/core/mesh_loader.py](src/core/mesh_loader.py) — nuevo método `_load_obj()`
  + `_parse_obj_face_index()`, dispatch por extensión (`.obj` vs `.stl`), nueva
  excepción `OBJParseError`.
- [src/ui/widgets/view_3d.py](src/ui/widgets/view_3d.py) — `vtkCellPicker`,
  `enable_picking()`, marcadores esféricos (`add_marker`), línea de medición
  genérica (`add_measurement_line()`), texto superpuesto
  (`show_measurement_text`). Seguimiento de actores separado en dos
  esquemas: `plane_marker_actors` (los 3 puntos que definen el plano, se
  limpian todos juntos) y `measurement_visuals: Dict[id, List[actor]]`
  (marcador(es)+línea de cada `Measurement`, indexados por su id, para poder
  borrar una medición puntual sin tocar el resto vía `remove_measurement()`).
  `draw_support_plane()` ahora recibe centro + ancho + alto (rectángulo, ya
  no un cuadrado de tamaño fijo). `_set_camera_view()` llama `ResetCamera()`
  *después* de fijar la dirección de cámara, no antes, para que la distancia
  se ajuste automáticamente al tamaño real del modelo. `set_vertex_colors()`
  reescrito con `numpy_support.numpy_to_vtk` (antes iteraba en Python punto
  por punto) y ahora valida que la cantidad de colores coincida con la
  cantidad de puntos de la malla; nuevo `clear_vertex_colors()` para el
  toggle del mapa de calor; `load_mesh()` desactiva el splitting de
  `vtkPolyDataNormals` (ver bug #9); nuevo `capture_screenshot()` para el
  informe PDF. `load_mesh()` ahora también fija un `vtkProperty` distinto
  para la cara posterior (`SetBackfaceProperty`). Nuevo
  `set_plane_visible()` (oculta/muestra sin borrar). Todos los actores
  decorativos (marcadores, líneas, plano) ahora tienen `PickableOff()` — ver
  nota sobre este fix más abajo. Nueva previsualización de picking
  (`show_pick_preview`/`hide_pick_preview`), manejada desde `eventFilter`
  escuchando también `MouseMove`/`Leave` (antes solo escuchaba
  press/release).
- [src/ui/main_window.py](src/ui/main_window.py) — estado de picking
  (`_pick_mode`, `_plane_points`, `_distance_points`, `support_plane`,
  `measurements: List[Measurement]`), cuatro `QAction` checkeables en la
  toolbar (plano/altura/distancia mutuamente excluyentes vía
  `_set_pick_mode_exclusive()`, más "Mapa de calor" que es independiente),
  manejo completo de los 3 flujos de picking, diálogo de apertura ahora
  acepta `.obj` además de `.stl`. Nueva `QTableWidget` de 2 columnas en el
  panel derecho con menú contextual de borrado
  (`_show_measurement_context_menu`, `_delete_measurement`). Nuevos items en
  el menú Archivo: exportar CSV/PDF, guardar/abrir proyecto. Colores de
  marcador/línea por tipo de medición extraídos a constantes de módulo
  (se reusan tanto al medir en vivo como al restaurar un proyecto cargado).
- [src/models/foot_model.py](src/models/foot_model.py) — `Measurement` ahora
  tiene un campo `id` autogenerado (contador global), necesario para poder
  asociar y borrar sus actores visuales de forma individual.
- [tests/test_mesh_loader.py](tests/test_mesh_loader.py) — clase
  `TestMeshLoaderOBJ` (8 tests: triángulo simple, vértices compartidos,
  normales/texturas ignoradas, formato `v//vn`, triangulación de quads,
  bounds, errores de formato).

## Bugs encontrados y corregidos en pruebas manuales

Los bugs #1 a #4, #8 y #9 son preexistentes de Sprint 1 (en código de
renderizado que no había sido probado visualmente). Los bugs #5, #6 y #7 son
de la propia implementación de este Sprint 2 (picking y texto de medición),
expuestos recién al probar contra la app real con mouse de verdad.

### 1. `InsertNextCell()` con overload inexistente

Al probar la app manualmente, **cargar cualquier malla (STL u OBJ) fallaba**
con `Error cargando malla: no overloads of InsertNextCell() take 4 arguments`.
No era un problema de este sprint: `_vertices_faces_to_polydata()` en
`view_3d.py` armaba cada triángulo con
`triangles.InsertNextCell(*[3, id0, id1, id2])` (4 argumentos posicionales),
un overload que no existe en la versión de VTK realmente instalada en el
venv (9.7.0 — el `requirements.txt` pide `VTK==9.2.0`, pero lo instalado es
más nuevo). Se reemplazó por el patrón portable entre versiones:

```python
triangles.InsertNextCell(3)
triangles.InsertCellPoint(int(face[0]))
triangles.InsertCellPoint(int(face[1]))
triangles.InsertCellPoint(int(face[2]))
```

Verificado cargando `Pie_random.stl` completo (54.671 triángulos) a través
del pipeline real (`MeshLoader` → `VTK3DView.load_mesh`) sin excepciones.
Si en algún momento se fija `VTK==9.2.0` real en el venv (como pide
`requirements.txt`), igual conviene dejar este patrón: es válido en ambas
versiones.

### 2. `numpy.ndarray` evaluado con `or`

Con el bug anterior resuelto, cargar cualquier archivo seguía fallando, ahora
con `Error inesperado: The truth value of an array with more than one
element is ambiguous. Use a.any() or a.all()`. Causa: los 7 métodos
`set_view_*()` de `VTK3DView` (dorsal, plantar, anterior, posterior, medial,
lateral, isométrica) usaban:

```python
center = self.current_model.center or np.array([0, 0, 0])
```

`self.current_model.center` es un `np.ndarray` de 3 elementos (nunca `None`
tras una carga exitosa — se calcula siempre en `MeshLoader.load()`), y NumPy
no permite evaluar la verdad de un array de más de un elemento con `or`.
`open_file()` en `main_window.py` llama a `canvas.set_view_dorsal()`
inmediatamente después de cargar la malla, así que el bug se disparaba en
cuanto se abría cualquier archivo. Se corrigió el chequeo en los 7 métodos a:

```python
center = self.current_model.center if self.current_model.center is not None else np.array([0, 0, 0])
```

Verificado ejecutando las 7 vistas contra una malla real cargada (OBJ y STL).

### 3. Canvas en negro: `Initialize()` llamado antes de que el widget tenga superficie nativa

Con los dos bugs anteriores resueltos, la malla cargaba (status bar y logs lo
confirmaban) pero el canvas 3D quedaba completamente negro — ni siquiera se
veía el color de fondo configurado (`SetBackground(0.3, 0.3, 0.35)`), señal
de que el render window nunca llegó a pintar nada.

Causa: `VTK3DView.__init__()` llamaba `self.interactor.Initialize()`
**antes** de agregar el widget al layout y antes de que la ventana principal
se mostrara (`window.show()` en `main.py` ocurre después de construir todo
`MainWindow`). `QVTKRenderWindowInteractor` toma el handle de ventana nativa
(`winId()`) en su propio `__init__`, pero para que el render OpenGL se
componga correctamente en pantalla, `Initialize()` necesita que el widget ya
esté realizado/visible — llamarlo antes dejaba el render window "pintando"
sobre una superficie que todavía no estaba lista, y no se recuperaba solo.

Se corrigió difiriendo la llamada a `showEvent()`:

```python
def showEvent(self, event):
    super().showEvent(event)
    if not self._interactor_initialized:
        self.interactor.Initialize()
        self._interactor_initialized = True
        self.render_window.Render()
```

Esto solo, sin embargo, **no resolvió el canvas en negro** (ver bug #4): era
una corrección real pero no la causa principal.

### 4. Causa raíz del canvas en negro: falta registrar el backend OpenGL de `vtkmodules`

Con los 3 bugs anteriores corregidos, la malla cargaba pero el canvas seguía
sin mostrar nada (negro / blanco según la zona). La causa real: **VTK
modular (`vtkmodules`) no registra ninguna implementación concreta de
render hasta que se importa explícitamente el paquete del backend**. El
archivo nunca importaba `vtkmodules.vtkRenderingOpenGL2`. Sin ese import,
`vtkRenderWindow()` se construye como una clase sin implementación real
detrás — no tira ningún error, simplemente no dibuja nada. Se comprobó
directamente:

```python
from vtkmodules.vtkRenderingCore import vtkRenderWindow
vtkRenderWindow().SupportsOpenGL()  # 0 (sin el import de vtkRenderingOpenGL2)

import vtkmodules.vtkRenderingOpenGL2
vtkRenderWindow().SupportsOpenGL()  # 1, clase real: vtkWin32OpenGLRenderWindow
```

Se agregaron al principio de `view_3d.py`, antes de crear cualquier
render window:

```python
import vtkmodules.vtkRenderingOpenGL2  # registra el backend OpenGL real
import vtkmodules.vtkRenderingFreeType  # necesario para que vtkTextActor dibuje texto
```

Verificado: `VTK3DView().render_window.SupportsOpenGL()` devuelve `1` y la
clase pasa a ser `vtkWin32OpenGLRenderWindow` (antes devolvía `0` con una
clase base sin implementación). Esta es la causa raíz real de que no se
viera nada — el bug #3 (orden de `Initialize()`) era una corrección legítima
pero no suficiente por sí sola.

### 5. Picking nunca disparaba: `LeftButtonReleaseEvent()` no invoca el observer en esta versión de VTK

Con el canvas ya renderizando, activar "Definir plano de apoyo" y clickear
sobre la malla no hacía nada: ni marcador, ni contador, ni error. Se
diagnosticó instrumentando los observers directamente: el observer de
`AddObserver("LeftButtonPressEvent", ...)` SÍ se disparaba, pero el de
`AddObserver("LeftButtonReleaseEvent", ...)` **nunca** se disparaba, aun
cuando `mouseReleaseEvent` de Qt sí se ejecutaba y llamaba correctamente al
método `_Iren.LeftButtonReleaseEvent()`. Comprobado que el problema es del
método dedicado en sí: `_Iren.InvokeEvent('LeftButtonReleaseEvent')` (forma
genérica) SÍ dispara el observer; `_Iren.LeftButtonReleaseEvent()` (método
específico) no, de forma reproducible, independientemente de la prioridad
del observer.

Se reemplazó el mecanismo de picking: en vez de observers de VTK sobre
`LeftButtonPressEvent`/`LeftButtonReleaseEvent`, ahora `VTK3DView` instala un
`eventFilter` de Qt sobre el widget `interactor`, escuchando
`QEvent.Type.MouseButtonPress`/`MouseButtonRelease` directamente — un
mecanismo de Qt puro que no depende de la dispatch (con esa falla) de VTK.
La distinción click-vs-arrastre se mantiene igual (tolerancia de 3px entre
press y release), y la conversión de coordenadas Qt (origen arriba-izquierda,
lógicas) a coordenadas de píxel de VTK (origen abajo-izquierda, de
dispositivo) se hace a mano usando `devicePixelRatioF()`.

### 6. Picking encontraba "nada" aunque el click cayera justo sobre la malla: clipping range desactualizado

Con el bug #5 corregido, el evento de click sí llegaba a `vtkCellPicker`,
pero el pick fallaba (`GetCellId() == -1`) **en cualquier punto de la malla**,
incluso apuntando exactamente al centro proyectado del modelo (verificado con
`renderer.WorldToDisplay()`). Se probó también con `vtkPropPicker` y
`vtkPicker`: ambos fallaban igual, descartando un problema específico de
`vtkCellPicker`.

Causa: `_set_camera_view()` (usado por los 7 métodos `set_view_*`) llama
`renderer.ResetCamera()` **antes** de reposicionar la cámara a la vista
pedida (dorsal/plantar/etc.), pero nunca vuelve a ajustar el
`ClippingRange` después de mover la cámara. El render se ve perfecto porque
VTK maneja el clipping de forma más laxa al dibujar, pero el picking usa
`camera.GetClippingRange()` como límites del segmento de rayo a intersectar
— y ese rango quedaba calculado para la posición de cámara *anterior* a
moverla. Se comprobó puntualmente: para la vista plantar, el rango quedaba en
`(491.9, 686.3)` mientras la distancia real cámara→malla era `(136, 216)` —
rangos que ni se tocan, por eso el rayo de picking nunca intersectaba nada.

Se agregó `self.renderer.ResetCameraClippingRange()` en `_set_camera_view()`,
justo después de fijar la nueva posición/foco/view-up de cámara y antes de
`Render()`. Verificado: el mismo pick que antes devolvía `cellId=-1` en todo
el viewport ahora acierta (`cellId=49386`) en el centro de la malla.

Verificado el flujo completo end-to-end (3 clicks reales simulados con
`QTest` sobre `MainWindow` real → plano calculado correctamente; 1 click →
altura calculada) sin intervención manual.

### 7. `AddActor2D` no existe en `vtkRenderer` (VTK 9.7+)

Con el plano y el picking ya funcionando, medir la altura del arco cerraba
la aplicación de golpe apenas aparecía la línea amarilla. El traceback real
del usuario lo mostró directo:

```
AttributeError: 'vtkmodules.vtkRenderingOpenGL2.vtkOpenGLRenderer' object
has no attribute 'AddActor2D'. Did you mean: 'AddActor'?
```

Una excepción sin manejar dentro de un slot de Qt (`_on_height_point_picked`
→ `show_measurement_text`) hace que PyQt6 aborte todo el proceso, de ahí el
cierre abrupto sin diálogo de error. Causa: en VTK 9.7, `AddActor2D` /
`RemoveActor2D` / `GetActors2D` de `vtkRenderer` están deprecados/eliminados
en favor del `AddActor()` / `RemoveActor()` genérico (que ya acepta
`vtkActor2D`, incluido `vtkTextActor`) — comprobado directamente:
`renderer.AddActor(vtkTextActor())` funciona, `AddActor2D` no existe como
atributo. Se corrigieron las dos llamadas en `show_measurement_text()` y
`clear_measurement_text()`.

Verificado el flujo completo end-to-end otra vez (3 clicks → plano, 1 click
→ altura) sin crashear, con el texto de medición mostrado correctamente.

### 8. Cámara demasiado cerca al cargar una malla o cambiar de vista

El usuario reportó que al cargar un STL la primera vista queda "muy cerca"
y hay que hacer zoom out a mano. Causa: `_set_camera_view()` (usado por
`load_mesh()` → `set_view_dorsal()` y por los 7 botones de vista) llamaba
`renderer.ResetCamera()` **antes** de fijar la posición/foco de cámara que
pedía cada vista — es decir, ajustaba el encuadre para la cámara *anterior*
y después la pisaba con una posición a distancia fija (ej. `center + [0, 0,
200]`), sin relación con el tamaño real del modelo cargado. Para un modelo
más grande que ese offset fijo, la cámara queda dentro o muy cerca de la
malla.

Se corrigió invirtiendo el orden: fijar primero la dirección deseada
(`SetPosition`/`SetFocalPoint`/`SetViewUp`) y llamar `ResetCamera()`
**después** — VTK ajusta entonces la distancia a lo largo de esa misma
dirección para que el bounding box completo entre en cuadro, en vez de usar
la distancia fija que pasa el caller. El valor de `position` que pasan los
7 métodos `set_view_*()` ahora solo importa para establecer la dirección de
la cámara, no la distancia final.

Verificado con `Pie_random.stl`: distancia final de cámara ≈ 577 unidades
para un modelo cuya dimensión máxima es ≈ 257 — relación de 2.25x, un
encuadre con margen cómodo en vez de recortado.

### 9. `vtkPolyDataNormals` duplica vértices en bordes filosos: rompe el mapa de calor antes de nacer

Al implementar el mapa de calor (colorear cada vértice de la malla según su
altura respecto al plano), el plan era usar `set_vertex_colors()` — un
método que ya existía desde Sprint 1 pero nunca se había usado ni probado.
Antes de conectarlo a la UI, se verificó si realmente funcionaba: se
comprobó que `poly_data.GetNumberOfPoints()` (28.017) no coincidía con
`model.num_vertices` (28.014). La diferencia: `load_mesh()` procesa la malla
con `vtkPolyDataNormals` para calcular normales, y por defecto ese filtro
**duplica vértices en bordes filosos** (`Splitting` viene en `On`) para
poder darles normales distintas a cada lado del borde. Eso rompe la
correspondencia 1:1 entre índice de vértice y color que necesita
`set_vertex_colors()` — con esa desalineación, cada vértice se habría
pintado con el color de un punto distinto (silenciosamente, sin ningún
error).

Se corrigió con `normals_filter.SplittingOff()`. Un pie escaneado no tiene
bordes realmente filosos (es una superficie orgánica suave), así que
desactivar el splitting no cambia el shading visible. Verificado: con el fix,
`poly_data.GetNumberOfPoints() == model.num_vertices` (28.014 en ambos).

De paso, se reescribió `set_vertex_colors()` para usar
`numpy_support.numpy_to_vtk()` en vez de un loop en Python insertando color
por color (más rápido con mallas de decenas de miles de vértices, y menos
código).

Ninguno de los nueve bugs estaba cubierto por tests automatizados (los
existentes de Sprint 1 solo testean `MeshLoader`/`FootModel`, no
`VTK3DView`), por eso pasaron desapercibidos hasta la prueba manual de la
app real con mouse de verdad.

## Decisiones de diseño tomadas (y por qué)

- **STL vs OBJ para probar la app**: se recibieron dos archivos de prueba,
  `pie__mio.obj` (12.657 vértices / 24.245 caras) y `Pie_random.stl`
  (54.671 triángulos, binario). Para una aplicación terapéutica priorizamos
  la malla con mayor resolución → se usó `Pie_random.stl` para validar el
  flujo de medición end-to-end. El soporte OBJ se agregó igual (pedido
  explícito del usuario) para que la app acepte lo que exporte el escáner en
  cualquiera de los dos formatos.
- **Parser OBJ sin deduplicación de vértices**: a diferencia de STL (que es
  "triangle soup" sin índices compartidos, de ahí la deduplicación por
  tolerancia en `_find_or_add_vertex`), OBJ ya referencia vértices por índice.
  Deduplicar ahí sería trabajo innecesario y podría introducir bugs de
  tolerancia que el formato no requiere.
- **Altura del arco: click manual (no automático)**: ya decidido en la
  consigna original. Confirma la decisión: más simple y confiable para un
  MVP que un algoritmo de detección automática de "zona del arco" (que
  requeriría heurísticas de orientación del pie no triviales de validar sin
  un dataset).
- **Selección de puntos: distinguir click de arrastre por desplazamiento en
  píxeles** (tolerancia de 3px entre `LeftButtonPressEvent` y
  `LeftButtonReleaseEvent`), en vez de interceptar/abortar el evento del
  `vtkInteractorStyleTrackballCamera`. Esto evita pelear con la propagación
  de eventos de VTK y permite seguir rotando la cámara con el mismo botón
  mientras un modo de picking está activo — solo un click "quieto" dispara
  la selección.
- **Tolerancia de colinealidad (`1e-6`) en `compute_support_plane`**: si el
  producto cruz de los dos vectores del plano tiene magnitud menor a esa
  tolerancia, se considera que los 3 puntos no definen un plano válido y se
  lanza `MeasurementError` (la UI lo muestra como warning y reinicia la
  selección de plano). Valor elegido para coordenadas en mm: suficientemente
  chico para no rechazar planos válidos por errores de picking, suficiente
  para atrapar puntos realmente colineales/coincidentes.
- **Un solo modo de picking activo a la vez**: activar "Medir altura" cancela
  "Definir plano" (y viceversa) para simplificar el estado — no hace falta un
  botón de reset separado, alcanza con el mismo botón (checkeable) para
  cancelar.
- **Medir altura exige un plano ya definido**: si el usuario aprieta "Medir
  altura del arco" sin haber definido el plano, se le avisa con un
  `QMessageBox` y no se activa el modo.
- **Cargar una malla nueva reinicia toda la medición** (plano, marcadores,
  línea, texto) — evita mostrar geometría de la malla anterior superpuesta a
  la nueva.
- **Mediciones acumulables en vez de reemplazadas** (pedido explícito del
  usuario: "quiero tomar más alturas de arco"): se reemplazó el `Measurement`
  ya definido en `foot_model.py` desde Sprint 1 (sin usar hasta ahora) en vez
  de inventar una estructura nueva. Cada altura o distancia medida se agrega
  a una lista (`MainWindow.measurements`) y se numeran por tipo ("Altura arco
  1", "Altura arco 2", "Distancia plano 1", ...) contando cuántas del mismo
  prefijo hay ya en la lista, sin necesitar contadores separados.
- **Redefinir el plano de apoyo borra todas las mediciones acumuladas**: tanto
  la altura como la distancia en el plano se calculan relativas al plano
  vigente: si el plano cambia, esos valores dejan de tener sentido. Se
  prefirió este comportamiento explícito (sin diálogo de confirmación) para
  no complicar el flujo del MVP; queda documentado acá como algo a tener en
  cuenta si en el futuro se quiere permitir redefinir el plano sin perder
  mediciones que no dependan de él.
- **Distancia "en el plano" proyecta ambos puntos antes de medir** (no es la
  distancia 3D directa entre los dos clicks): así, si el usuario clickea
  ligeramente arriba o abajo de la superficie exacta del plano (algo
  esperable, dado el ruido normal de picking sobre una malla con curvatura),
  esa diferencia de altura no contamina la medición de una extensión de la
  superficie de apoyo (ancho/largo). Test dedicado
  (`test_height_difference_is_ignored`) que confirma que dos puntos con
  igual X/Y pero distinta Z dan distancia ~0.
- **Línea de altura vs. línea de distancia dibujan puntos distintos**: la
  línea de altura conecta el punto crudo clickeado con su proyección (marca
  visualmente "cuánto se elevó respecto al plano"); la línea de distancia
  conecta las dos proyecciones entre sí (marca "cuánto mide a lo largo del
  plano"), no los dos puntos crudos — coherente con que el valor reportado
  es la distancia proyectada, no la 3D directa.
- **Colores distintos por tipo de medición** para poder diferenciarlas a
  simple vista en el canvas cuando hay varias acumuladas: plano = celeste,
  altura = naranja (marcador) / amarillo (línea), distancia = magenta
  (marcador) / verde (línea).
- **`Measurement.id` autogenerado (contador global) en vez de pasado a
  mano**: necesario para poder borrar una medición puntual (tabla → click
  derecho → "Eliminar") sin afectar las demás. Se generó con
  `itertools.count` en vez de UUID por simplicidad — no hace falta que sea
  único entre sesiones ni impredecible, solo distinto dentro de la sesión
  actual.
- **Los actores visuales del plano y los de una medición se rastrean por
  separado** (`plane_marker_actors` vs. `measurement_visuals: Dict[id,
  List[actor]]`): los 3 puntos del plano no son una "medición" borrable
  individualmente (no tiene sentido borrar solo uno sin redefinir el plano
  entero), así que quedan en su propio bucket que solo se limpia completo.
- **El rectángulo del plano se dimensiona proyectando todos los vértices de
  la malla sobre el plano** (`compute_plane_footprint`), no con un tamaño
  fijo aproximado. Esto también corrige que antes quedaba centrado en uno de
  los 3 puntos clickeados (un punto cualquiera del borde de la base, no el
  centro de la huella) — ahora se centra en el centroide real de la
  proyección.
- **`ResetCamera()` después de fijar la dirección de cámara, no antes**
  (bug #8): el valor que antes se usaba como "distancia" en cada
  `set_view_*()` ahora solo define la dirección; la distancia final la
  calcula VTK para que el modelo completo entre en cuadro, sea cual sea su
  tamaño real.
- **Gradiente del mapa de calor normalizado contra el máximo del propio
  array, no contra un valor absoluto fijo**: así el rango de color
  (azul→verde→rojo) siempre se aprovecha completo sea cual sea el tamaño
  real del pie, en vez de que todo salga "casi azul" en un pie con arco bajo
  o "casi rojo" en uno con arco muy pronunciado si se comparara contra una
  escala fija.
- **El mapa de calor se apaga (no solo se deshabilita) al redefinir el
  plano o cargar una malla nueva**: los colores están calculados contra el
  plano vigente en el momento; dejarlos pintados tras cambiar de plano
  mostraría datos que ya no corresponden, sin ningún indicio visual de que
  quedaron desactualizados.
- **El informe PDF no falla si falta la captura de pantalla**: `export_report_pdf()`
  atrapa cualquier error al leer la imagen y sigue generando el PDF sin ella
  (con la tabla de mediciones igual) en vez de abortar todo el export por un
  problema en un elemento secundario.
- **`project_io` guarda la ruta a la malla, no la malla en sí**: guardar los
  vértices/caras completos en el JSON del proyecto sería redundante (ya
  existen en el .stl/.obj original) y pesado. La contra: si el archivo
  original se mueve o se borra, el proyecto no se puede reabrir — se avisa
  con un mensaje claro en vez de fallar en silencio o con un traceback.
- **Los ids de las mediciones no se preservan al guardar/cargar un
  proyecto**: cada `Measurement` cargado recibe un id nuevo (autogenerado)
  en vez de restaurar el id original guardado. No hace falta que sea
  estable entre sesiones — solo sirve para asociar actores visuales dentro
  de la sesión actual, y al cargar un proyecto esos actores se recrean de
  cero de todos modos.
- **Todos los actores decorativos (marcadores, líneas de medición, plano de
  apoyo) son `PickableOff()`**: al implementar la previsualización de
  picking se notó que estos actores eran pickeables por defecto — un click
  cerca de un marcador ya puesto, o cerca del borde del plano (que
  sobresale un poco de la huella real por el margen de
  `compute_plane_footprint`), podía seleccionar el objeto decorativo en vez
  de la malla real debajo. No era un bug reportado, pero sí un riesgo real
  para cualquier medición tomada cerca de un punto o borde ya marcado.
  Verificado con un test que clickea a propósito sobre la posición exacta de
  un marcador existente y confirma que el pick sigue devolviendo un punto de
  la malla.
- **La esfera de previsualización se crea una sola vez (lazy) y se
  reposiciona en cada movimiento de mouse**, en vez de crear un actor VTK
  nuevo por evento — mover el `vtkSphereSource.SetCenter()` de un actor ya
  existente es mucho más barato que instanciar geometría nueva a la
  frecuencia de eventos de `MouseMove`.
### Intentado y revertido: talón automático + distancias a metatarsianos

Se probó (y se revirtió a pedido del usuario) una función para marcar el
punto de talón automáticamente como el extremo geométrico de la malla a lo
largo del eje principal de la huella (PCA sobre la proyección en el plano),
más un modo de click manual para medir la distancia desde ese talón hasta
las cabezas del 1er y 5to metatarsiano.

**Bug encontrado por el usuario**: el punto marcado como talón no caía sobre
el plano de apoyo ni sobre la malla visible — aparecía separado, flotando
fuera del contorno del pie. Causa probable (no confirmada, no se llegó a
depurar): la búsqueda del extremo se hacía sobre **todos** los vértices de
la malla sin restricción, y esta sesión ya encontró antes, en otro contexto
(exportando un `.asc` de nube de puntos), que un escaneo puede traer un
pequeño fragmento de vértices desconectado del cuerpo principal del pie
(~8% de los puntos en ese caso). Si el extremo a lo largo del eje principal
cae en ese fragmento suelto en vez de en el cuerpo del pie, el resultado es
exactamente lo que se vio: un punto "extremo" válido matemáticamente pero
inútil en la práctica.

Si se retoma esto en el futuro, el primer paso antes de repetir el mismo
enfoque sería filtrar la búsqueda al componente conectado más grande de la
malla (exactamente la misma técnica de `scipy.sparse.csgraph.connected_components`
ya usada para limpiar la nube de puntos cruda más temprano en este proyecto),
en vez de buscar el extremo sobre la malla completa sin filtrar.

## Tests

65/65 tests pasan (22 preexistentes de Sprint 1 en `test_integration.py` y
las clases no-OBJ de `test_mesh_loader.py` + 43 nuevos de este sprint: 25 en
`test_measurements.py` — plano, altura, distancia en el plano, footprint del
plano, mapa de alturas y su gradiente de color —, 8 en `TestMeshLoaderOBJ`,
7 en `test_report_export.py` y 4 en `test_project_io.py`).

```bash
cd pie-viewer
./venv/Scripts/python.exe -m pytest tests/ -v
```

También se validó manualmente contra `Pie_random.stl` real (28.014 vértices
tras deduplicación, 54.671 triángulos): carga, cálculo de plano y distancia
punto-plano dan valores geométricamente consistentes (~50 mm en el punto más
alto respecto a un plano de base de prueba).

Las últimas 6 funcionalidades (avisos de escala, deshacer, confirmación al
cerrar, nombres editables, atajos de teclado, toggle de ejes) son de UI pura
sin cálculo geométrico nuevo, así que se validaron con scripts `QTest`
end-to-end (incluyendo disparar los atajos de teclado reales — `Escape`,
`Ctrl+Z`, `Supr` — a través del sistema de eventos de Qt, no solo llamando
los métodos manejadores directamente) en vez de sumarles tests unitarios
permanentes, siguiendo el mismo criterio que el resto de la UI en este sprint.

## Pendiente / limitaciones conocidas

- No hay tests automatizados de la UI/VTK **en la suite del repo** (picking,
  toolbar, render) — igual que en Sprint 1, `pytest` solo cubre
  `MeshLoader`/`FootModel`/`measurements.py`. Durante el desarrollo sí se
  validó el flujo completo de UI con scripts `QTest` (clicks simulados sobre
  la ventana real: cargar malla, definir plano, tomar varias alturas y una
  distancia, redefinir plano), pero esos scripts fueron descartados al
  terminar — no quedaron como tests permanentes. Agregarlos de forma estable
  (sin depender de una malla externa al repo) queda pendiente.
- ~~Las mediciones viven solo en memoria, sin poder exportarlas~~ — resuelto:
  ahora se pueden exportar a CSV, a un informe PDF, o guardar/reabrir como
  proyecto completo (plano + mediciones + referencia a la malla).
- El informe PDF es deliberadamente simple (encabezado, una imagen, tabla) —
  no incluye datos del paciente (nombre, ficha, etc.) porque la app no los
  captura en ningún lado todavía. Si hace falta un reporte por paciente de
  verdad, el siguiente paso natural es agregar esos campos a la UI antes de
  generar el PDF, no inventarlos en el export.
- `project_io` no valida que la malla cargada al reabrir un proyecto sea
  *la misma* que se guardó (mismo número de vértices, mismo archivo) más
  allá de que la ruta exista — si el archivo en esa ruta cambió de contenido
  mientras tanto (se volvió a escanear encima), el plano y las mediciones se
  van a restaurar sobre coordenadas que ya no corresponden a esa malla, sin
  ningún aviso.
- El texto superpuesto en el canvas lista todas las mediciones acumuladas
  sin límite (aunque ahora sí se puede borrar una individual desde la tabla
  del panel derecho). Con muchas mediciones el texto puede ocupar bastante
  espacio en pantalla — si eso llega a ser un problema real, la solución
  natural es mostrar ahí solo la última medición y dejar la lista completa
  en la tabla.
- ~~No hay forma de deshacer un click individual~~ — resuelto con `Ctrl+Z`.
  Sigue sin haber "rehacer" (redo) — se consideró de menor prioridad ya que
  el caso de uso real es corregir un error, no rehacer algo deshecho a propósito.
- `_unsaved_changes` es un flag booleano simple (no un historial completo de
  cambios): guardar el proyecto lo limpia por completo, así que si volvés a
  medir algo y volvés a deshacerlo con `Ctrl+Z`, el flag puede quedar en
  `True` aunque el estado final sea idéntico al último guardado. Es un
  falso positivo inofensivo (como mucho te pregunta si guardar cuando en
  rigor no hacía falta), no un riesgo de perder datos.
- La normal del plano no tiene una orientación garantizada hacia "arriba"
  del pie (depende del orden en que el usuario clickeó los 3 puntos); no
  afecta el cálculo de altura porque se usa valor absoluto, pero si a futuro
  se necesita el signo (por ejemplo para colorear por encima/debajo del
  plano) habría que fijar una convención.
- Strings de UI hardcodeados en español, sin capa de i18n (igual que en
  Sprint 1).
