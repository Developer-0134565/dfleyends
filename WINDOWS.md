# DF-Chronicles en Windows

Guía de instalación, arranque, empaquetado y solución de problemas.

---

## 1. Requisitos

| Elemento | Versión | Nota |
|---|---|---|
| Windows | 10 u 11 | Probado en Windows 11 |
| Python | **3.11 o superior** | Probado en 3.14.7 |

**Nada más.** Sin `pip install`, sin `requirements.txt`, sin `node_modules`.
Todo usa la biblioteca estándar.

```powershell
python --version
```

Si Windows no reconoce `python`, pruebe `py --version`. Si tampoco funciona,
instale Python desde <https://www.python.org/downloads/> y marque
**«Add Python to PATH»** durante la instalación.

---

## 2. Dónde deben estar los datos

```
<una carpeta llamada como quieras>\
└── DF-Chronicles\
    ├── run.py
    ├── dfchron\
    └── 00_SOURCE\
        ├── original_data\
        │   ├── legends.xml          49.223.702 B
        │   └── legends_plus.xml     17.664.819 B
        └── processed\
            ├── from_legends_xml\
            ├── from_legends_plus\
            ├── merged\              <- el índice que usa la aplicación
            └── validation\
```

**El proyecto puede moverse a cualquier carpeta.** No hay rutas absolutas en el
código: se resuelven desde la ubicación de los propios ficheros.

Si algún día pierde la pista del proyecto, puede forzarlo:

```powershell
$env:DFCHRON_ROOT = "D:\otro sitio\DF-Chronicles"
python run.py
```

Comprobación sin arrancar el servidor:

```powershell
python run.py --comprobar
```

Debe imprimir los conteos reales:

```
  Figuras      : 11,144
  Entidades    : 1,067
  Sitios       : 734
  Eventos      : 57,215
  Artefactos   : 427
  Relaciones   : 13,192
  Anios        : 1-100
```

---

## 3. Arranque

```powershell
cd DF-Chronicles
python run.py
```

Se abre <http://127.0.0.1:877/> automáticamente.

```powershell
python run.py 9000              # otro puerto
python run.py --sin-navegador   # no abrir el navegador
python run.py --comprobar       # comprobar y salir
```

Para no cerrar la ventana, cree `iniciar.bat` en la raíz del proyecto:

```bat
@echo off
cd /d "%~dp0"
python run.py --sin-navegador
pause
```

---

## 4. Ubicación de los datos

| Qué | Dónde |
|---|---|
| XML originales | `00_SOURCE/original_data/` — **solo lectura** |
| Índice que usa la app | `00_SOURCE/processed/merged/` — **solo lectura** |
| Fixtures de validación | `00_SOURCE/processed/validation/` — **solo lectura** |
| Exportaciones | `00_SOURCE/exports/` — **único sitio donde la app escribe** |

La aplicación **nunca** escribe fuera de `exports/`. Está comprobado por
pruebas: el hash del dataset se compara antes y después de servir peticiones.

---

## 5. Comprobaciones

```powershell
python 00_SOURCE\tools\probar_integracion.py   # 20
python 00_SOURCE\tools\probar_nucleo.py        # 48
python 00_SOURCE\tools\probar_adversarial.py   # 39
python dfchron\pruebas\probar_api.py           # 54
python 00_SOURCE\tools\test_determinismo.py    # 29 consultas x 4 procesos
python 00_SOURCE\tools\verificar_reproducibilidad.py
```

Todas devuelven código de salida `0` si pasan.

En PowerShell, para ver la salida completa sin que intercepte el `stderr`:

```powershell
cmd /c "python 00_SOURCE\tools\probar_nucleo.py 2>&1"
```

---

## 6. Rendimiento

| Medida | Valor |
|---|---|
| Carga del índice | **2,1 – 2,6 s** (~500 MiB de RAM) |
| Búsqueda | 2,5 ms |
| Ficha de figura | 2,3 ms |
| Ficha de sitio | 52 ms |
| Eventos filtrados por año | 17 ms |

El arranque domina el coste. Para ver la memoria:

```powershell
Get-Process python | Select-Object Id, WS

---

## 7. Empaquetado en un `.exe`

**Estado actual: no implementado, y no recomendado todavía.**

No hay `.exe` porque la arquitectura no lo necesita: el proyecto ya es
portable (sin dependencias) y `python run.py` funciona en cualquier equipo
con Python. Un `.exe` añadiría un paso de compilación, un antivirus que lo
marca y unos 40 MiB, a cambio de nada.

Si en el futuro se quiere, la vía natural es
[PyInstaller](https://pyinstaller.org/), y el punto de entrada sería
`run.py`. El resto de la arquitectura lo permite sin cambios: `rutas.py`
resuelve las rutas desde `__file__`.

Requisitos para que funcione empaquetado:

* Los JSONL de `processed/merged/` deben **acompañar** al `.exe` (no se
  pueden empaquetar dentro: el diseño exige poder reconstruirlos y verificar
  sus hashes en disco).
* `dfchron/web/` también debe acompañar al ejecutable.

Comando previsto:

```powershell
pyinstaller --onedir --name DF-Chronicles `
            --add-data "00_SOURCE\processed;00_SOURCE\processed" `
            --add-data "dfchron\web;dfchron\web" `
            run.py
```

> Usar `--onedir`, **nunca** `--onefile`: los JSONL deben seguir siendo
> ficheros reales en disco para que las salvaguardas de reproducibilidad y
> los hashes conserven su sentido.

---

## 8. Solución de problemas

### «No se encuentra el módulo nucleo»

Se ha ejecutado una herramienta desde una carpeta que no es la del proyecto.
Solución: ejecutar desde la raíz con `python run.py`, o usar rutas completas:

```powershell
python "C:\ruta\DF-Chronicles\00_SOURCE\tools\probar_nucleo.py"
```

### «El puerto 877 está ocupado»

```powershell
python run.py 9000
```

Para ver quién lo ocupa:

```powershell
Get-NetTCPConnection -LocalPort 877 -ErrorAction SilentlyContinue
```

### «No existe el dataset normalizado»

Falta `00_SOURCE/processed/merged/`. Reconstruir desde los XML:

```powershell
python 00_SOURCE\tools\integrar_legends.py
```

Debe terminar con `9/9 secciones byte-identicas` frente al manifiesto.

### La página se queda en «Cargando el archivo historico…»

El índice tarda ~2,5 s. Si es más, mira la consola donde se lanzó
`python run.py`: los errores se registran ahí. La API responde
`500 ERROR_INTERNO` **sin filtrar el traceback al navegador**, por seguridad.

### La página se ve sin estilos

No es un fallo. Comprueba que <http://127.0.0.1:877/static/estilo.css>
devuelve el CSS; si da `404`, falta `dfchron/web/estilo.css`.

### La exportación no escribe el fichero

Por diseño. «Exportar JSON» y «Exportar Markdown» **no escriben nada**: abren
el contenido en el navegador. Para escribir en disco hay que usar «Guardar en
disco», que solo escribe en `00_SOURCE/exports/`. Un nombre con `/` o `..` se
rechaza a propósito.

### El Firewall de Windows pregunta

Solo si se cambia `--host 0.0.0.0`. Con el valor por defecto (`127.0.0.1`) no
hay tráfico de red y no debería preguntar. Si lo hizo y aceptaste, la regla
afecta solo a este programa.

### Acentos raros en la consola

Windows usa a veces CP437 o CP850. El proyecto fuerza UTF-8 en los JSONL. Si
la consola muestra caracteres incorrectos:

```powershell
chcp 65001
```

La UI del navegador se ve bien en cualquier caso: el servidor envía
`Content-Type: text/html; charset=utf-8`.

---

## 9. Compartir o mover el proyecto

1. Copiar **toda** la carpeta `DF-Chronicles/`.
2. Los XML de `original_data/` son la parte pesada (67 MB). Para solo
   consultar, basta con copiar también `00_SOURCE/processed/merged/`.
3. Ejecutar `python run.py --comprobar` en la nueva ubicación.

`rutas.py` sigue el proyecto automáticamente. Si aun así hace falta:

```powershell
$env:DFCHRON_ROOT = "D:\nueva\ubicacion\DF-Chronicles"
python run.py
```

```
