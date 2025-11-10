# DDLCPet :)
> [!WARNING]
> El proyecto sigue en desarrollo, no se ha probado en otro dispositivo aparte del mio, estoy trabajando en eso para hacer el codigo mas portable y agregarle un menu CLI para tener mas de una doki al mismo tiempo  
Mascota de escritorio escrita en Python + PyQt6 que flota sobre Hyprland/Wayland/X11 como una ventana transparente y siempre permanece sobre el resto de aplicaciones. El objetivo es tener un personaje animado, configurable y fácil de extender que pueda acompañarte mientras trabajas.

## Estado actual

-   Ventana sin bordes, translúcida y siempre al frente; funciona en Hyprland/Wayland forzando `QT_QPA_PLATFORM=xcb`.
-   Se posiciona centrada al pie de la pantalla y “camina” justo pegada al borde gracias a una física simple de gravedad + rebotes.
-   Movimiento sub‑pixel con timers precisos (~60 FPS), mini saltos aleatorios, bobbing sinusoidal y giros controlados por cooldown para evitar glitches.
-   Reacciona al cursor: si pasas el mouse por encima hace un brinco corto alejándose como en el proyecto de GameMaker.
-   Arrastre estilo golf: puedes tomarla, moverla y soltarla para lanzarla; la velocidad resultante depende del gesto que hagas.
-   Sistema de animaciones configurable: idle y walk comparten sprite (tal como pediste) y hay un estado `jump` que se activa automáticamente cuando despega.
-   Las animaciones se espejan dinámicamente según la dirección del movimiento, evitando duplicar assets.

## Requisitos

-   Python ≥ 3.11
-   PyQt6 ≥ 6.10
-   Pillow ≥ 10.0

Instalación rápida:

```bash
pip install -r requirements.txt
```

## Estructura del proyecto

```
.
├── assets/             # Imágenes actuales (idle.png, walk.png, etc.)
├── config.toml         # Config global (ventana, movimiento, sprites)
├── deskpet/
│   ├── __init__.py
│   ├── config.py       # Dataclasses + loader TOML
│   ├── core.py         # Lógica/UI principal del pet
│   ├── sprites.py      # Carga y slicing de sprites animados
│   └── utils.py        # Reservado para helpers futuros
└── main.py             # Punto de entrada (setea QApplication y crea la mascota)
```

## Ejecutar

```bash
python main.py
```

En Hyprland/Wayland es necesario forzar el backend X11:

```bash
QT_QPA_PLATFORM=xcb python main.py
```

`main.py` ya establece esta variable vía `os.environ`, así que basta con ejecutar el script como siempre mientras tengas `xcb` disponible.

## Configuración (`config.toml`)

Todo lo importante se ajusta sin tocar código. Los bloques principales:

-   `[window]`: tamaño del widget y offset inferior (actualmente pegado al borde).
-   `[movement]`: velocidad base, tasa de actualización, rango de empujes horizontales aleatorios, probabilidad/cooldown de giros y parámetros del bobbing sinusoidal.
-   `[physics]`: gravedad, intensidad de los brincos, cooldown del hover, amortiguación de arrastre, rebotes y factor de lanzamiento para el modo golf.
-   `[sprites]`: carpeta base y definición por estado. Cada `sprites.states.<nombre>` acepta:
    -   `file`: sprite sheet o imagen base.
    -   `frames`: cantidad de frames en la hoja.
    -   `fps`: velocidad de esa animación.
    -   `layout`: `horizontal` o `vertical` (también se puede especificar `frame_size` manualmente).

Esto permite añadir nuevos estados (p. ej. `sleep`, `jump`, `menu`) simplemente declarando sprites adicionales y luego referenciándolos desde `core.py`.

## Comportamiento

-   El pet vive en un pequeño motor de física 2D (gravedad + rebotes). `idle` y `walk` usan la misma sprite, mientras que `jump` se dispara al despegar.
-   Hace saltos aleatorios cada cierto intervalo y también reacciona al puntero para escapar con brincos más altos.
-   El movimiento horizontal nace de pequeños empujes pseudoaleatorios y de la inercia obtenida al lanzarlo.
-   En cada frame se decide si debe espejar la animación según el signo de la velocidad X.
-   El arrastre pausa la física; al soltar calcula la velocidad final y la aplica como si fuera un lanzamiento de golf.

## Próximos pasos / ideas

-   Añadir sprites con múltiples frames reales para aprovechar el sistema de animación (actualmente los PNGs son de un solo frame).
-   Más estados (sleep, jump, dance), sonidos y un menú contextual.
-   Colisiones con otros elementos de la UI (por ejemplo, “subirse” a ventanas específicas).
-   Posibilidad de cargar múltiples mascotas con configuraciones distintas.
-   Hot-reload del `config.toml` para ajustar parámetros en vivo.
