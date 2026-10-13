# generator: b0a-1
# def_hash: f3ac0d3b7e0a
# generated_at: 2026-10-13T15:03:55
from fastapi import FastAPI
def build():
    app = FastAPI()
    @app.get('/ok')
    def ok():
        return {'code': 0}
    @app.get('/bad')
    def bad():
        return {'code': 1001}
    @app.get('/deny')
    def deny():
        return {'code': 1008}
    @app.get('/missing')
    def missing():
        return {'code': 1504}
    @app.get('/used')
    def used():
        return {'code': 1502}
    return app
