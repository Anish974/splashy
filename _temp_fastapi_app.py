from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()
app.mount('/files', StaticFiles(directory='public'), name='files')

@app.get('/')
async def root():
    return {'status': 'ok', 'message': 'Static file server running'}

@app.get('/health')
async def health():
    files = os.listdir('public')
    return {'status': 'healthy', 'files': files}
