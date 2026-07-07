"""Eng yaqin propan (LPG) / metan (CNG) zapravkasini OpenStreetMap
Overpass API orqali topuvchi yordamchi funksiyalar."""

import asyncio
import logging
import math

import httpx

logger = logging.getLogger(__name__)

# Bir nechta Overpass ko'zgusi (mirror) - biri 406/429 bersa, keyingisini
# sinab ko'ramiz. Bu bepul serverlarning tez-tez rad etishiga qarshi chora.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Overpass server User-Agent bo'lmagan so'rovlarni ko'pincha rad etadi.
HEADERS = {
    "User-Agent": "ZapravkaGO-TelegramBot/1.0 (contact: example@example.com)",
}

# Qidiruv radiuslari (metrda) - avval yaqinroq radiusda qidiradi,
# topilmasa kattalashtirib boradi.
SEARCH_RADII = [3000, 7000, 15000, 30000, 60000]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofani km da hisoblaydi."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def build_overpass_query(lat: float, lon: float, radius: int) -> str:
    """fuel:lpg=yes yoki fuel:cng=yes tegiga ega amenity=fuel
    nuqtalarini qidiruvchi Overpass QL so'rovi."""
    return f"""
    [out:json][timeout:25];
    (
      node["amenity"="fuel"]["fuel:lpg"="yes"](around:{radius},{lat},{lon});
      node["amenity"="fuel"]["fuel:cng"="yes"](around:{radius},{lat},{lon});
      way["amenity"="fuel"]["fuel:lpg"="yes"](around:{radius},{lat},{lon});
      way["amenity"="fuel"]["fuel:cng"="yes"](around:{radius},{lat},{lon});
    );
    out center tags;
    """


async def find_nearest_station(lat: float, lon: float):
    """Eng yaqin LPG/CNG zapravkasini topadi.

    Topilsa dict qaytaradi: name, lat, lon, distance_km, fuel_type.
    Topilmasa None qaytaradi.
    """
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        for radius in SEARCH_RADII:
            query = build_overpass_query(lat, lon, radius)
            data = None

            for url in OVERPASS_URLS:
                try:
                    resp = await client.post(url, data={"data": query})
                    resp.raise_for_status()
                    data = resp.json()
                    break  # shu ko'zgu ishladi, boshqasiga o'tmaymiz
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Overpass (%s) xatolik: %s", url, exc)
                    await asyncio.sleep(0.5)
                    continue

            if data is None:
                logger.error("Barcha Overpass ko'zgular ishlamadi (radius=%s)", radius)
                await asyncio.sleep(1)
                continue

            elements = data.get("elements", [])
            if not elements:
                continue

            candidates = []
            for el in elements:
                if el["type"] == "node":
                    elat, elon = el["lat"], el["lon"]
                else:  # way -> "center" qaytadi
                    center = el.get("center")
                    if not center:
                        continue
                    elat, elon = center["lat"], center["lon"]

                tags = el.get("tags", {})
                name = tags.get("name", "Nomi ko'rsatilmagan zapravka")

                fuel_types = []
                if tags.get("fuel:lpg") == "yes":
                    fuel_types.append("Propan (LPG)")
                if tags.get("fuel:cng") == "yes":
                    fuel_types.append("Metan (CNG)")

                dist = haversine_km(lat, lon, elat, elon)
                candidates.append(
                    {
                        "name": name,
                        "lat": elat,
                        "lon": elon,
                        "distance_km": dist,
                        "fuel_type": " / ".join(fuel_types) or "LPG/CNG",
                    }
                )

            if candidates:
                candidates.sort(key=lambda c: c["distance_km"])
                return candidates[0]

    return None