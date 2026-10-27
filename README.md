# Bip
   <p align="center">
     <img src="bip.png" width="220" alt="Bip">
   </p>
Bip es una mascota virtual flotante para Windows, desarrollada con Python y PyQt6. Tiene expresiones animadas, sonidos, comportamientos interactivos y funciones opcionales relacionadas con la música.

## Funciones

- Expresiones animadas y sonidos.
- Interacción con el cursor: mimos, clics, arrastre y piruetas.
- Reacciones según algunas aplicaciones y el contexto de uso.
- Reproductor en pantalla con información y controles multimedia compatibles.
- Movimiento autónomo, juegos sencillos y opciones para esconderse.
- Funciones opcionales como Pomodoro, recordatorios y datos del clima.

![Bip](BIP.gif)

## Requisitos

- Windows 10 u 11.
- Python 3.10 o posterior: https://www.python.org/downloads/

## Instalación y ejecución

1. Descargá el repositorio desde GitHub o clonalo:

   ```bash
   git clone https://github.com/Marcoshav/BIP.git
   cd BIP
   ```

2. Ejecutá `ejecutar.bat`. El archivo instala las dependencias declaradas e inicia Bip.

También podés instalar las dependencias y ejecutarlo manualmente:

```bash
python -m pip install -r requirements.txt
python bip.py
```

Las funciones multimedia opcionales usan los paquetes de `requirements-medios.txt`. Si su instalación falla, algunas funciones de música pueden no estar disponibles.

## Crear un ejecutable

Ejecutá `crear_exe.bat` en Windows. El proceso intenta generar `Bip.exe`. El ejecutable no se incluye en el repositorio; publicalo como archivo adjunto de una versión (GitHub Release) si querés distribuirlo.

## Uso básico

| Acción | Resultado |
|---|---|
| Pasar el cursor o hacer clic | Interacción y mimos |
| Doble clic | Pirueta |
| Arrastrar | Cambiar su posición |
| Clic derecho | Abrir el menú de opciones |

## Privacidad

Bip puede consultar el título de la ventana activa y la actividad general del equipo para adaptar sus comportamientos. Algunas funciones se conectan a internet para obtener información meteorológica, ubicación aproximada por IP o buscar música, según las funciones que uses.

Los datos locales se guardan en `%USERPROFILE%\\.bip`. Revisá el código fuente antes de usar el programa si necesitás verificar en detalle su comportamiento de privacidad.

## Estructura del proyecto

- `bip.py`: inicio de la aplicación.
- `bip_ui.py`: interfaz, dibujo y movimiento.
- `bip_cerebro.py`, `bip_pensar.py`: estado y decisiones.
- `bip_conductas.py`, `bip_juegos.py`: comportamientos y juegos.
- `bip_cara.py`, `bip_props.py`, `bip_fx.py`: expresiones, objetos y efectos.
- `bip_sonido.py`: generación de sonidos.
- `bip_apps.py`, `bip_sistema.py`: detección de aplicaciones y funciones de Windows.
- `bip_medios.py`, `bip_tarjeta.py`, `bip_musica.py`: música y reproductor.

## ¿Te gustaría colaborar con el proyecto?

- **cafecito.app:** https://cafecito.app/marcoshav.
- **ETH o BSC (ERC20 o BEP20):** 0xcc24fa1fca0f0961b09ca20443f4d4459b36e91e.
- **SOL (Solana):** 8gX9APP1HVWMMub6hAutSiKezgfJt7TENRLJ9jPtc6hC.
- **TRX (TRC20):** TUqi8Y6ytaX3c91afsucCYH6LkqGDPo8xa.


## Licencia

Copyright (C) 2026 Marcos Herrero (Marcoshav)

Bip es software libre: podés redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública General GNU (GPL) publicada por la Free Software Foundation, versión 3 de la Licencia. Consultá el archivo [`LICENSE`](LICENSE).

Esto significa, en resumen:

- Podés usar, estudiar, modificar y compartir Bip.
- Si distribuís una versión modificada (o un programa que la incluya), tenés que publicarla bajo la misma licencia GPLv3, entregar su código fuente y **conservar el aviso de copyright y la autoría original**.
- No se puede cerrar el código ni distribuirlo como producto propietario.

**Dependencias:** las bibliotecas de terceros mantienen sus propias licencias. En particular, PyQt6 se distribuye bajo GPLv3 o una licencia comercial, según los términos de Riverbank Computing, y es compatible con la GPLv3 de este proyecto: https://www.riverbankcomputing.com/software/pyqt/
