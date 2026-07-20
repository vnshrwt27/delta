from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def join(self, doc_id: int, ws: WebSocket):
        await ws.accept()
        self.rooms[doc_id].add(ws)

    async def leave(self, doc_id: int, ws: WebSocket):
        self.rooms[doc_id].discard(ws)
        if not self.rooms[doc_id]:
            del self.rooms[doc_id]

    async def broadcast(self, doc_id: int, message: dict, exclude: WebSocket | None = None):
        for ws in self.rooms.get(doc_id, set()):
            if ws != exclude:
                await ws.send_json(message)


manager = ConnectionManager()
