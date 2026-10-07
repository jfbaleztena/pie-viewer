# Resumen de la interfaz — material para la guía de usuario

Los textos entre comillas están copiados tal cual de la aplicación (se
extrajeron de la ventana real y del código). Todo lo que figura como
"verificado con eventos simulados" o "no verificado" está aclarado donde
corresponde: conviene confirmarlo con el mouse y una malla real antes de
publicarlo en la guía.

## 1. Datos generales

| Dato | Valor |
|---|---|
| Título de la ventana | `Sistema de Visualización de Pies - MVP` |
| Versión que muestra la ventana | `Versión 0.1.0 MVP` (Ayuda > Acerca de) |
| Texto completo de "Acerca de" | `Sistema de Visualización de Pies` / `Versión 0.1.0 MVP` / `Para análisis y medición de modelos 3D de pies` / `en ortopedia.` |
| Tamaño inicial de la ventana | 1600 × 1000 píxeles |
| Unidad de las mediciones | milímetros (`mm`) |
| Cómo se abre | `.\venv\Scripts\python.exe -m src.main` desde la carpeta `pie-viewer` |

La ventana tiene cuatro zonas: **barra de menú** (arriba), **barra de
herramientas** (debajo), **vista 3D** (centro, ocupa casi todo) y **panel
derecho** (vistas, tabla de mediciones y puntos de referencia). Abajo hay una
**barra de estado** con el último mensaje de la aplicación; al abrir dice
`Listo`.

## 2. Formatos de archivo

| Para qué | Formato | Notas |
|---|---|---|
| Abrir un modelo | `.stl` (binario o ASCII) y `.obj` | El diálogo ofrece los filtros `Mallas 3D (*.stl *.obj)`, `STL Files (*.stl)`, `OBJ Files (*.obj)` y `Todos los archivos (*)`. |
| Textura (opcional) | `.obj` + `.mtl` + imagen `.png` o `.jpg`/`.jpeg` | La imagen se referencia desde el `.mtl` (`map_Kd`) y deben estar en la misma carpeta que el `.obj`. Solo los OBJ pueden traer textura; los STL no. |
| Tamaño máximo | 2.000.000 triángulos | El rechazo (`Demasiados triángulos…`) solo se aplica a STL binarios. Con más de 500.000 triángulos, en cualquier formato, se avisa que puede ir lento. |
| Escala esperada | milímetros | Un pie de 10 a 40 cm de largo se interpreta como milímetros sin aviso (ver sección 8). |
| Guardar proyecto | `.json` (`Proyecto pie-viewer (*.json)`) | Guarda la ruta a la malla, el plano, las mediciones y los puntos de referencia. No guarda la malla en sí. |
| Exportar mediciones | `.csv` | Columnas: `Archivo` y `Fecha` en el encabezado; luego `Medicion`, `Tipo`, `Valor`, `Unidad`. |
| Exportar informe | `.pdf` | Título "Informe de medicion - Sistema de Visualizacion de Pies", nombre del archivo, fecha, una captura de la vista 3D actual y la tabla de mediciones. |
| Autoguardado | `<nombre de la malla>.pieviewer.json` | Se crea solo, junto al archivo de la malla (ej. `pie.obj` → `pie.obj.pieviewer.json`). Ver sección 6.8. |

## 3. Menús

### Archivo
| Opción | Atajo | Qué hace | Estado inicial |
|---|---|---|---|
| `Abrir malla (STL/OBJ)` | `Ctrl+O` | Abre el diálogo "Abrir archivo de malla 3D" y carga el modelo. | Habilitado |
| `Abrir proyecto...` | — | Abre un `.json` guardado: recarga la malla que indica y restaura plano, mediciones y puntos. | Habilitado |
| `Guardar proyecto...` | — | Guarda el estado actual en un `.json` a elección. | Deshabilitado hasta cargar una malla |
| `Exportar mediciones (CSV)...` | — | Guarda la tabla de mediciones en un `.csv`. | Deshabilitado hasta cargar una malla |
| `Exportar informe (PDF)...` | — | Genera un PDF con captura de la vista y mediciones. | Deshabilitado hasta cargar una malla |
| `Salir` | `Ctrl+Q` | Cierra la aplicación. | Habilitado |

### Ver
| Opción | Qué hace |
|---|---|
| `Dorsal (Arriba)` | Vista desde arriba, con los dedos hacia arriba y el talón hacia abajo. |
| `Isométrica` | Vista en perspectiva diagonal. |

### Ayuda
| Opción | Qué hace |
|---|---|
| `Acerca de` | Muestra nombre y versión (ver sección 1). |

## 4. Barra de herramientas

De izquierda a derecha, con los separadores tal como aparecen. Los botones con
"(interruptor)" quedan marcados mientras están activos; al volver a tocarlos se
apagan.

| Grupo | Botón | Qué hace | Se habilita cuando |
|---|---|---|---|
| Vistas | `Dorsal` | Igual que Ver > Dorsal (Arriba). | Siempre |
| | `Isométrica` | Igual que Ver > Isométrica. | Siempre |
| | `Ejes` (interruptor) | Muestra u oculta los ejes de coordenadas. | Siempre |
| Plano | `Definir plano de apoyo` (interruptor) | Inicia la selección de 3 puntos de la base del pie. | Hay una malla cargada |
| | `Mostrar plano` (interruptor) | Muestra u oculta el plano sin borrarlo. | Ya hay un plano definido |
| Mediciones | `Medir altura del arco` (interruptor) | 1 click: altura de ese punto sobre el plano. | Ya hay un plano definido |
| | `Medir distancia en el plano` (interruptor) | 2 clicks: distancia entre los puntos proyectados en el plano. | Ya hay un plano definido |
| Puntos | `Marcar metatarsianos` (interruptor) | 2 clicks: cabeza del 1er y del 5to metatarsiano. | Hay una malla cargada |
| | `Marcar talón distal` (interruptor) | 1 click: punto más posterior del talón. | Hay una malla cargada |
| Colores | `Mapa de calor` (interruptor) | Colorea toda la malla según su altura sobre el plano (azul = cerca del plano, rojo = lo más alto). | Ya hay un plano definido |
| | `Mostrar textura` (interruptor) | Muestra la foto del pie sobre la malla. | La malla trae textura (solo algunos OBJ) |

Los botones deshabilitados se ven en gris claro. Solo uno de los modos de
selección (plano, altura, distancia, metatarsianos, talón) puede estar activo a
la vez: al activar uno, se desactiva el anterior. `Mapa de calor` y `Mostrar
textura` tampoco pueden estar activos juntos.

## 5. Panel derecho

De arriba hacia abajo:

1. Título `Vistas Estándar:` con dos botones: `Dorsal (Arriba)` e `Isométrica`
   (hacen lo mismo que los del menú Ver).
2. Texto `Mediciones (doble click para renombrar, click derecho para
   eliminar):` y debajo la **tabla de mediciones**, con columnas `Medición` y
   `Valor` (ej. `127.25 mm`).
   * Doble click en el nombre: renombrar. Si se deja vacío, se conserva el nombre anterior. La columna `Valor` no se edita.
   * Click derecho sobre una fila: menú con `Eliminar medición`.
   * Seleccionar una fila y presionar `Supr`: elimina esa medición.
3. `Puntos de referencia:` con tres líneas, cada una `marcado` o `sin marcar`:
   * `Cabeza 1er metatarsiano`
   * `Cabeza 5to metatarsiano`
   * `Punto distal del talón`

Además, **sobre la vista 3D**, abajo a la izquierda, aparece en blanco el
listado de todas las mediciones (`Nombre: valor mm`, una por línea).

Nombres que asigna la aplicación: `Altura arco 1`, `Altura arco 2`…,
`Distancia plano 1`…, y las tres distancias automáticas entre puntos de
referencia (sección 6.7): `Metatarsiano 1 - 5`, `Talón - Metatarsiano 1`,
`Talón - Metatarsiano 5`.

## 6. Controles y flujos de trabajo

### 6.0 Mouse y teclado

**Mouse sobre la vista 3D** (verificado con eventos simulados; conviene
confirmarlo a mano):

| Acción | Efecto |
|---|---|
| Arrastrar con el botón izquierdo | Girar el modelo |
| Rueda hacia adelante / hacia atrás | Acercar / alejar (zoom) |
| Arrastrar con el botón derecho | Zoom (hacia abajo aleja; hacia arriba acerca) |
| Arrastrar con el botón central | Desplazar (mover el modelo sin girarlo) |
| `Shift` + arrastrar con el izquierdo | Desplazar (equivale al botón central) |
| `Ctrl` + arrastrar con el izquierdo | Girar la imagen sobre sí misma (como girar una rueda) |

Cuando hay un modo de selección activo, un **click izquierdo sin mover el
mouse** marca un punto; si se arrastra más de unos pocos píxeles se interpreta
como giro de cámara y no marca nada. Mientras se mueve el mouse aparece una
esfera blanca semitransparente que muestra dónde caería el punto.

**Teclado**

| Tecla | Efecto |
|---|---|
| `Ctrl+O` | Abrir malla |
| `Ctrl+Q` | Salir |
| `Escape` | Cancela el modo de selección activo |
| `Ctrl+Z` | Deshace el último punto de una selección a medias (plano, distancia, metatarsianos); si no hay ninguna en curso, elimina la última medición |
| `Supr` | Con la tabla seleccionada, elimina la medición elegida |

### 6.1 Cargar un archivo
1. `Archivo > Abrir malla (STL/OBJ)` (o `Ctrl+O`) y elegir el archivo.
2. La barra de estado pasa por `Cargando: …`, `Parseando: …`, `Renderizando: …` y
   termina en `✓ nombre.stl - 28014 vértices, 54671 triángulos`.
3. El modelo aparece en vista dorsal. Si esa malla ya tenía mediciones
   guardadas, se restauran solas (ver 6.8).
4. Si la malla tiene algo fuera de lo normal, aparece el aviso `Revisar antes
   de medir` (ver sección 8).

### 6.2 Vistas
Solo hay dos: `Dorsal (Arriba)` e `Isométrica`. La cámara se reencuadra sola
para que el modelo entre completo. Qué cara del pie se ve en la dorsal depende
de cómo vino orientado el escaneo; en los escaneos de ejemplo probados se ve la
planta.

### 6.3 Plano de apoyo
Es la referencia de las alturas, las distancias en el plano y el mapa de calor.
1. Tocar `Definir plano de apoyo`. La barra de estado dice `Plano de apoyo: click
   en 3 puntos de la base del pie (0/3)`.
2. Hacer click en 3 puntos bien separados de la base del pie. Cada click suma un
   marcador celeste y actualiza el contador (`1/3`, `2/3`).
3. Al tercero, se dibuja un rectángulo azul semitransparente del tamaño de la
   huella del pie y la barra dice `Plano de apoyo definido. Ahora podés medir
   altura del arco o distancias.` Se habilitan `Mostrar plano`, `Medir altura
   del arco`, `Medir distancia en el plano` y `Mapa de calor`.

**Importante para la guía:** volver a tocar `Definir plano de apoyo` y
redefinir el plano **borra todas las mediciones** hechas hasta ese momento (se
calculan respecto al plano), y apaga el mapa de calor. Si cancelás a mitad con
`Escape`, la barra dice `Selección de plano de apoyo cancelada`.

### 6.4 Medir altura del arco
1. `Medir altura del arco`. La barra dice `Altura del arco: click en el punto
   más alto del arco plantar`.
2. Un click en ese punto. Se agrega una fila `Altura arco N` con la distancia
   perpendicular al plano, un marcador naranja y una línea hasta el plano.
3. El modo se apaga solo; para otra medición hay que volver a tocar el botón.

### 6.5 Medir distancia en el plano
1. `Medir distancia en el plano`. Según `Mostrar plano`:
   * **Plano visible:** `Distancia en el plano: click en 2 puntos sobre el plano (0/2)`. Los puntos se ubican **sobre el plano**, aunque el pie no lo toque.
   * **Plano oculto:** `Distancia en el plano: click en 2 puntos de la superficie de apoyo (0/2)`. Los puntos se marcan sobre la malla y se miden sus proyecciones.
2. Dos clicks. Se agrega `Distancia plano N` y se dibujan dos marcadores
   violetas unidos por una línea verde, siempre por encima de la malla.
3. **Ajustar:** con el plano visible y sin ningún modo activo, se puede
   arrastrar cada marcador violeta (el cursor cambia a una cruz de flechas al
   pasar encima). El valor, la tabla y el texto de la vista se actualizan al
   mover, y se guarda al soltar. (Verificado con eventos simulados.)

### 6.6 Mapa de calor
1. Con el plano definido, tocar `Mapa de calor`. La barra dice `Mapa de calor
   activado (máximo: 78.4 mm respecto al plano)` (el número cambia según el
   modelo).
2. Colorea toda la superficie: azul cerca del plano, verde en el medio, rojo en
   los puntos más altos. La escala va de 0 hasta el punto más alto de la malla
   completa.
3. Volver a tocarlo lo apaga (`Mapa de calor desactivado`). Redefinir el plano
   también lo apaga.

### 6.7 Marcar puntos de referencia
Sirven para guardar la ubicación de las cabezas de los metatarsianos y el
talón. No necesitan plano de apoyo.
* `Marcar metatarsianos`: `Metatarsianos: click en la cabeza del 1er
  metatarsiano (1/2)` → click → `Metatarsianos: click en la cabeza del 5to
  metatarsiano (2/2)` → click. Recién al segundo click se confirman los dos
  (amarillo = 1er, verde = 5to). Fin: `Cabezas del 1er y 5to metatarsiano
  marcadas`.
* `Marcar talón distal`: `Talón: click en el punto más distal (posterior) del
  talón` → un click (marcador rojo). Fin: `Punto distal del talón marcado`.
* Volver a marcar un punto **reemplaza** el anterior. Cancelar con `Escape`
  (`Marcado de metatarsianos cancelado` / `Marcado del talón cancelado`)
  conserva los puntos que ya estaban marcados. No hay forma de borrar un punto
  suelto, solo reemplazarlo.
* **Distancias automáticas:** cuando los tres puntos están marcados, se agregan
  solas a la tabla `Metatarsiano 1 - 5`, `Talón - Metatarsiano 1` y `Talón -
  Metatarsiano 5` (distancia recta 3D entre cada par, línea azul). La barra
  agrega `Distancias entre los 3 puntos agregadas a las mediciones.` Si se
  vuelve a marcar algún punto, se recalculan sin duplicarse y conservan el
  nombre aunque se hayan renombrado. Si se elimina una, reaparece la próxima
  vez que se marque cualquier punto.

### 6.8 Guardado automático y proyectos
* **Automático:** cada cambio (plano, medición nueva, borrada, renombrada o
  ajustada, puntos marcados) se guarda solo en `<malla>.pieviewer.json`, junto
  al archivo de la malla. Al volver a abrir esa malla se restauran y la barra
  dice `Se restauraron N mediciones y K puntos de referencia guardados de
  nombre.obj`. Si la malla cambió desde entonces (distinta cantidad de
  vértices) se pregunta antes de restaurar (ver sección 8).
* **Manual:** `Guardar proyecto...` / `Abrir proyecto...` guardan y abren un
  `.json` en la ubicación que se elija (por ejemplo para pasarlo a otra
  carpeta). Barra: `Proyecto guardado: nombre.json`, `Proyecto cargado:
  nombre.json (N mediciones)`.
* **Exportar:** `Exportar mediciones (CSV)...` (`Mediciones exportadas:
  nombre.csv`) y `Exportar informe (PDF)...` (`Informe exportado:
  nombre.pdf`). El PDF incluye lo que se ve en la vista 3D en ese momento.
* Al cerrar la ventana, solo se pregunta `Hay mediciones sin guardar. ¿Querés
  guardarlas antes de salir?` (Guardar / Descartar / Cancelar) si falló el
  autoguardado.

### 6.9 Deshacer
`Ctrl+Z` actúa sobre lo último que se estaba haciendo: si hay un plano,
distancia o metatarsianos a medio marcar, quita el último punto; si no,
elimina la última medición completa. No hay "rehacer".

### 6.10 Textura
`Mostrar textura` (solo si el OBJ trae textura): muestra la foto del pie sobre
la malla (`Textura activada` / `Textura desactivada`). Sirve para ubicar
marcas hechas con tinta en la piel; los clicks siguen midiendo sobre la
geometría con la textura encendida.

## 7. Mensajes de la barra de estado

| Mensaje | Cuándo |
|---|---|
| `Listo` | Al abrir la aplicación |
| `Error: Archivo no encontrado` | El archivo elegido ya no existe |
| `Error: malla inválida` | El archivo está dañado o tiene geometría imposible |
| `Error: Fallo al cargar` | Cualquier otro fallo al abrir |
| `<nombre> eliminada (N mediciones restantes)` | Al borrar una medición |
| `Altura arco 1: 15.50 mm agregada (1 mediciones en total)` | Al medir (mismo formato para distancias) |
| `No se pudieron guardar las mediciones automáticamente` | Falló el autoguardado (ej. carpeta de solo lectura) |
| `No se pudieron leer las mediciones guardadas de esta malla` | El archivo de autoguardado está dañado |

## 8. Mensajes de error y avisos (ventanas emergentes)

| Título de la ventana | Texto | Cuándo aparece |
|---|---|---|
| `Error` | `Archivo no encontrado:` + detalle | Al abrir un archivo que ya no existe |
| `Error` | `Error parseando archivo:` + detalle | El `.stl`/`.obj` no se puede leer. Detalles posibles: `Formato inválido en línea N…`, `Coordenadas inválidas en línea N…`, `No se encontraron vértices en archivo ASCII`/`binario`/`OBJ`, `No se encontraron caras en archivo OBJ`, `Header truncado…`, `Número de triángulos truncado`, `Vértice inválido en línea N…`, `Cara inválida en línea N…`, `Demasiados triángulos: N (máximo: 2,000,000)`, `Índice fuera de rango en cara N…`, `No hay vértices`, `No hay caras` |
| `Error` | `Error inesperado:` + detalle | Cualquier otro fallo al abrir |
| `Revisar antes de medir` | `Se detectó lo siguiente en la malla cargada:` + lista + `Verificá que la escala sea la esperada antes de tomar mediciones.` | Malla con algo fuera de lo normal. Ítems posibles: `Escala: probablemente METROS…`, `Escala: probablemente DECÍMETROS`, `Escala: REVISAR (tamaño inusual)`, `Escala: desconocida (verificar manualmente)`, `Malla grande: N triángulos (>500k puede ser lento)`, `N triángulos degenerados (área ~0)`. No aparece si la escala es la normal (`MILÍMETROS (pie normal)`). |
| `Falta plano de apoyo` | `Primero definí el plano de apoyo (3 clicks en la base del pie).` | Tocar altura, distancia o mapa de calor sin plano (en la práctica los botones están deshabilitados hasta definirlo) |
| `Puntos inválidos` | `Los 3 puntos seleccionados son colineales o coincidentes: no definen un plano válido. Elegí 3 puntos bien separados en la base.` | Los 3 clicks del plano están alineados o juntos |
| `Sin textura` | `Esta malla no tiene textura cargada (el archivo no trae coordenadas UV, .mtl o imagen de textura válidos).` | Tocar `Mostrar textura` en una malla sin textura (el botón está deshabilitado en ese caso) |
| `La malla cambió` | `Hay mediciones guardadas para este archivo, pero se tomaron sobre una malla de N vértices y la actual tiene M (¿se volvió a escanear?)…` + `¿Restaurarlas de todos modos? Si no, se reemplazarán cuando guardes mediciones nuevas.` (Sí / No, por defecto No) | Se abre una malla con el mismo nombre pero distinta cantidad de vértices |
| `Sin mediciones` | `No hay mediciones para exportar.` | Exportar CSV sin mediciones |
| `Sin malla cargada` | `Cargá una malla antes de generar el informe.` / `Cargá una malla antes de guardar el proyecto.` | Exportar PDF o guardar proyecto sin malla |
| `Error` | `No se pudo exportar el CSV:` / `No se pudo exportar el informe:` / `No se pudo guardar el proyecto:` + detalle | Falla al escribir el archivo (disco lleno, sin permisos, archivo abierto en otro programa) |
| `Error` | `No se pudo leer el proyecto:` + detalle | El `.json` no es un proyecto válido |
| `Malla no encontrada` | `El proyecto hace referencia a:` + ruta + `Ese archivo ya no está en esa ubicación. Movelo de vuelta o volvé a generar el proyecto desde la malla actual.` | Al abrir un proyecto cuya malla se movió o borró |
| `Error` | `No se pudo cargar la malla del proyecto:` + detalle | La malla del proyecto no se puede abrir |
| `Mediciones sin guardar` | `Hay mediciones sin guardar. ¿Querés guardarlas antes de salir?` | Al cerrar, solo si falló el autoguardado |

## 9. Registros (logs)

**La aplicación no guarda los logs en ningún archivo.** Escribe sus mensajes
(inicio, malla cargada, errores, etc.) únicamente en la consola desde la que se
la ejecuta (PowerShell); al cerrar esa ventana se pierden. El código de
registro admite escribir a un archivo, pero la aplicación no lo configura. Si
la guía necesita una ruta de logs, hay que agregar esa función primero.

## 10. Incompleto, limitado o que no funciona todavía

Para marcar aparte en la guía:

* **El mapa de calor no tiene leyenda.** No hay barra de colores ni
  referencias: el único valor visible es el máximo, en la barra de estado
  (`máximo: X mm respecto al plano`). Además la escala llega hasta el punto más
  alto de toda la malla, incluidos fragmentos sueltos del escaneo; en un modelo
  de ejemplo probado (`Pie_random.stl`) un fragmento fijó el máximo en 78 mm y
  el resto del pie salió casi todo azul.
* **Solo existen las vistas Dorsal e Isométrica.** Se quitaron las vistas
  anterior, posterior, plantar, medial y lateral. Si la guía las mencionaba,
  hay que actualizarla.
* **No hay archivo de logs** (sección 9).
* **Los puntos de referencia no se exportan** al CSV ni al PDF (sí van a los
  archivos `.json`). Las tres distancias automáticas sí aparecen en ambos.
* **El PDF es básico:** no incluye datos del paciente (nombre, ficha, etc.) porque
  la aplicación no los pide.
* **No hay "rehacer"** (solo `Ctrl+Z` para deshacer).
* **Solo los marcadores de las distancias en el plano se pueden arrastrar.**
  Los de altura del arco y los puntos de referencia hay que borrarlos o
  volver a marcarlos.
* **No se puede borrar un punto de referencia suelto**, solo reemplazarlo.
* **Mallas marcadas antes de existir las distancias automáticas:** si ya tenían
  los 3 puntos, las distancias no aparecen solas al abrir; hay que volver a
  marcar un punto.
* **Abrir un proyecto manualmente no compara la malla:** el aviso `La malla
  cambió` solo aparece con el autoguardado, no con `Abrir proyecto...`. Si el
  archivo de la malla se reescaneó con el mismo nombre, las mediciones se
  restauran sobre coordenadas que ya no corresponden, sin aviso.
* **El listado de mediciones sobre la vista 3D no tiene límite:** con muchas
  mediciones ocupa mucho espacio (la tabla del panel es la lista completa).
* **Textura:** solo imágenes `.png` y `.jpg`/`.jpeg`; otros formatos no están
  soportados (no verificado qué mensaje se vería en ese caso). El mapa de calor
  y la textura no se pueden ver a la vez.
* **Aspecto:** con el plano todavía sin definir, el botón `Mostrar plano` se ve
  resaltado aunque está deshabilitado (es solo estético).
* **Marca "MVP":** la ventana y "Acerca de" siguen diciendo `MVP`, versión
  0.1.0.
* **Verificación:** los controles del mouse, el arrastre de marcadores y los
  flujos de selección se probaron con eventos de mouse simulados sobre mallas de
  ejemplo, no con un uso prolongado a mano. Conviene que alguien los confirme
  antes de publicar la guía.
