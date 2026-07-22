import asyncio

import httpx
from last_translation_benchmark.geocoding import geocode_location


def test_geocode_location_formats_first_candidate():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=[
                {
                    "lat": "49.5042650",
                    "lon": "5.9493863",
                    "display_name": "Maison du Savoir, Esch-sur-Alzette",
                }
            ],
        )
    )

    async def geocode():
        async with httpx.AsyncClient(transport=transport) as client:
            return await geocode_location("University of Luxembourg", client)

    assert asyncio.run(geocode()) == {
        "lat": 49.504265,
        "lng": 5.9493863,
        "address": "Maison du Savoir, Esch-sur-Alzette",
    }
