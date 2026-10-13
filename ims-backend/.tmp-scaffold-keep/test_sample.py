# generator: b0a-1
# def_hash: f3ac0d3b7e0a
# generated_at: 2026-10-13T15:11:01
from fastapi.testclient import TestClient
from routes import build
def test_codes():
    client = TestClient(build())
    codes = [client.get(p).json()['code'] for p in ['/ok','/bad','/deny','/missing','/used']]
    assert codes == [0, 1001, 1008, 1504, 1502]
