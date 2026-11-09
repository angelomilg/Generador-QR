"""Avisos opcionales por Telegram (si no se configuran, solo se escriben en el registro)."""

import json
import logging
import urllib.request

log = logging.getLogger("bot")


def avisar(cfg, texto):
    log.info("AVISO: %s", texto)
    token, chat = cfg.get("telegram_token"), cfg.get("telegram_chat_id")
    if not token or not chat:
        return
    try:
        datos = json.dumps({"chat_id": chat, "text": f"[Trading bot] {texto}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=datos,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:  # un fallo de Telegram nunca debe parar el bot
        log.warning("No se pudo enviar el aviso por Telegram: %s", e)
