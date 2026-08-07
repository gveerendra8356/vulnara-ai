import asyncio
import websockets

async def test():
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5MWNlZjlhOS0yMTBjLTQ1ZDItOTAyMi1hNmE4ZTJmYzk3NDEiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3ODYxNDU1Nzh9.Kv9tHLoCwnFvNTiwd4RiWLXJ6t3gWum8c4al7MoTTdY'
    uri = f'ws://127.0.0.1:8000/ws/scans/982ba4bb-02c1-4939-b7c8-d337bea224af?token={token}'
    try:
        async with websockets.connect(uri) as ws:
            print('Connected!')
            await ws.send('{"event":"ping"}')
            res = await ws.recv()
            print('Received:', res)
    except Exception as e:
        print('Error:', type(e), e)

asyncio.run(test())
