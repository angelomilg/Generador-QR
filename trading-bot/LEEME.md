# Trading bot

Bot que opera Bitcoin contra euros (BTC/EUR) día y noche y **elige solo la estrategia** que mejor está funcionando.

- Arranca en **modo simulación**: usa precios reales pero dinero ficticio (100 €). No necesitas cuenta en ningún exchange.
- Cada semana prueba 5 estrategias con los últimos 6 meses de precios y se queda con la que mejor resultado da en datos que no ha visto. Si ninguna gana dinero, **se queda en euros**.
- Tiene límites que no se puede saltar: si pierde un 5 % en un día, para hasta el día siguiente; si pierde un 20 % del total, se detiene del todo.
- Muestra un **panel** en el navegador con el resultado, comparado con haber comprado y mantenido.

> ⚠️ Ningún bot garantiza ganancias. Este puede perder dinero. Déjalo en simulación varias semanas antes de pensar en usar dinero real, y nunca pongas más de lo que estés dispuesto a perder.

---

## Cómo ponerlo en marcha

### Windows
1. Descarga la carpeta del bot (botón verde **Code → Download ZIP** en GitHub) y descomprímela donde quieras.
2. Entra en la carpeta `trading-bot` y haz doble clic en **`INICIAR_WINDOWS.bat`**.
   - La primera vez instala lo necesario (un par de minutos). Si no tienes Python, intenta instalarlo solo: cuando termine, vuelve a hacer doble clic.
   - Si Windows muestra "Windows protegió su PC", pulsa **Más información → Ejecutar de todas formas**.
3. Se abrirá el panel en el navegador. **Deja la ventana negra abierta**: es el bot funcionando (puedes minimizarla).

Opcional: haz doble clic en **`ARRANQUE_AUTOMATICO_WINDOWS.bat`** para que el bot se abra solo cada vez que enciendas el ordenador. Vuelve a ejecutarlo para desactivarlo.

### Mac
1. Descarga y descomprime la carpeta.
2. Haz clic derecho en **`iniciar_mac.command` → Abrir** (la primera vez hay que hacerlo así por seguridad de macOS).
3. Deja la ventana del Terminal abierta.

## El día a día

- **No tienes que hacer nada.** Mientras la ventana esté abierta, el ordenador no se suspenderá (salvo que cierres la tapa del portátil).
- **El panel** está en `estado/panel.html`: ábrelo cuando quieras y se actualiza solo.
- **Para pararlo**, cierra la ventana. Al volver a abrirlo continúa donde lo dejó.
- Si se apaga el ordenador o se corta internet, no pasa nada: al volver sigue funcionando. Si el bot falla, se reinicia solo al minuto.
- **Para empezar de cero**, cierra el bot y borra la carpeta `estado`.

## Avisos en el móvil (opcional)

Para recibir un mensaje de Telegram cada vez que compra, vende o cambia de estrategia:
1. En Telegram, habla con **@BotFather**, escribe `/newbot` y sigue los pasos. Te dará un *token*.
2. Escribe cualquier cosa a tu nuevo bot de Telegram.
3. Abre en el navegador `https://api.telegram.org/botTU_TOKEN/getUpdates` (con tu token) y busca el número que aparece en `"chat":{"id":...`.
4. Pon el token y ese número en `config.json` (`telegram_token` y `telegram_chat_id`) y reinicia el bot.

## Pasar a dinero real (solo cuando la simulación lo justifique)

Mi recomendación: al menos **4–6 semanas en simulación** y que el panel muestre que el bot va mejor que "Comprar y mantener".

1. Crea una cuenta en [Binance](https://www.binance.com) y deposita **solo** el dinero que vas a usar: el bot usa **todos** los euros de la cuenta.
2. Crea una clave API (Perfil → Gestión de API) con **solo** el permiso de *trading spot*. **Nunca actives el permiso de retiradas.**
3. Copia `claves.ejemplo.json` como `claves.json` y pega tu clave y tu secreto.
4. En `config.json` cambia `"modo": "simulacion"` por `"modo": "real"`.
5. Borra la carpeta `estado` (para que el seguimiento empiece de cero) y arranca el bot.

`claves.json` es privado: no lo compartas ni lo subas a ningún sitio (ya está excluido de Git).

## Qué estrategias usa

| Estrategia | Idea |
|---|---|
| Comprar y mantener | Referencia: comprar y no hacer nada |
| Cruce de medias | Comprar cuando hay tendencia al alza |
| Ruptura de canal | Comprar cuando el precio supera su máximo reciente |
| Reversión RSI | Comprar tras caídas fuertes y vender en el rebote |
| Bandas de Bollinger | Comprar cuando el precio se aleja mucho por abajo de su media |

Cada una se prueba con varias configuraciones. En la evaluación semanal:
1. Se ajusta con los primeros 4 meses del histórico.
2. Se valida con los 2 últimos meses, que no ha visto.
3. Se elige la de mejor rentabilidad ajustada al riesgo (Sharpe).

Para no cambiar de estrategia por simple ruido, solo cambia si la nueva es claramente mejor. Todas las pruebas incluyen comisiones (0,1 %) y deslizamiento.

Para ver la evaluación sin operar: `.venv\Scripts\python -m bot --backtest` (Windows) o `.venv/bin/python -m bot --backtest` (Mac).

## Archivos

- `config.json`: ajustes (par, capital, límites, Telegram).
- `bot/`: el código.
- `estado/`: lo que genera el bot (panel, registro `bot.log` y estado guardado).
- `tests/`: pruebas automáticas (`python -m pytest`).
