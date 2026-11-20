from __future__ import annotations

from datetime import timedelta

DOMAIN = "ninjas_todo"
PLATFORMS = ["button", "sensor"]
TODO_ENTITY = "todo.shopping_list"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
LOCATION_REFRESH_INTERVAL = timedelta(hours=24)
NOTIFICATION_COOLDOWN = timedelta(minutes=30)
DEFAULT_DETECTION_RADIUS_METERS = 120

BRAND_ALIASES: dict[str, tuple[str, ...]] = {
    "continente": ("continente", "modelo", "bom dia"),
    "pingo_doce": ("pingo doce",),
    "auchan": ("auchan", "jumbo"),
    "lidl": ("lidl",),
    "makro": ("makro",),
    "intermarche": ("intermarche", "intermarché", "intermarché"),
    "aldi": ("aldi",),
    "mercadona": ("mercadona",),
    "elcorteingles": ("el corte ingles", "elcorteingles"),
}

BRAND_LABELS = {
    "continente": "Continente (Continente, Modelo, Bom Dia)",
    "pingo_doce": "Pingo Doce",
    "auchan": "Auchan",
    "lidl": "Lidl",
    "makro": "Makro",
    "intermarche": "Intermarche",
    "aldi": "Aldi",
    "mercadona": "Mercadona",
    "elcorteingles": "El Corte Inglés",
}
