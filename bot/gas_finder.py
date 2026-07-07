
import asyncio
import logging
import math

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

HEADERS = {
    "User-Agent": "ZapravkaGO-TelegramBot/1.0 (contact: example@example.com)",
}

SEARCH_RADII = [3000, 7000, 15000, 30000, 60000]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        for radius in SEARCH_RADII:
            query = build_overpass_query(lat, lon, radius)
            data = None

            for url in OVERPASS_URLS:
                try:
                    resp = await client.post(url, data={"data": query})
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception as exc:
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
                else:  
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