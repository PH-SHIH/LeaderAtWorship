import pytest


@pytest.mark.asyncio
async def test_create_song(client):
    resp = await client.post("/api/v1/songs", json={"title": "奇異恩典", "artist": "John Newton"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "奇異恩典"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_list_songs(client):
    await client.post("/api/v1/songs", json={"title": "奇異恩典"})
    await client.post("/api/v1/songs", json={"title": "祢真偉大"})
    resp = await client.get("/api/v1/songs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
