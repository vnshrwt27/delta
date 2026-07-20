from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.database import SessionLocal
from app.core.ot import Op, apply, transform_list
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.document import Document
from app.models.operation import Operation

ws_router = APIRouter()


@ws_router.websocket("/ws/documents/{doc_id}")
async def document_ws(websocket: WebSocket, doc_id: int, token: str = Query(...)):
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            await websocket.close(code=4004)
            return
        doc_version = doc.version
        doc_content = doc.content
    finally:
        db.close()

    await manager.join(doc_id, websocket)
    await websocket.send_json({
        "type": "snapshot",
        "content": doc_content,
        "version": doc_version,
    })

    try:
        while True:
            data = await websocket.receive_json()

            match data.get("type"):
                case "ping":
                    await websocket.send_json({"type": "pong"})

                case "cursor":
                    await manager.broadcast(doc_id, {
                        "type": "cursor",
                        "user_id": user_id,
                        "pos": data.get("pos"),
                        "selection": data.get("selection"),
                    }, exclude=websocket)

                case "op":
                    db = SessionLocal()
                    try:
                        client_version = data["client_version"]
                        op_data = data["op"]

                        op = Op(
                            type=op_data["type"],
                            pos=op_data["pos"],
                            text=op_data.get("text", ""),
                            length=op_data.get("length", 0),
                            user_id=str(user_id),
                        )

                        prior_ops = db.query(Operation).filter(
                            Operation.document_id == doc_id,
                            Operation.version > client_version,
                        ).order_by(Operation.version).all()

                        prior = [
                            Op(p.op_type, p.pos, p.text, p.length)
                            for p in prior_ops
                        ]
                        op = transform_list(op, prior)

                        doc = db.get(Document, doc_id)
                        if not doc:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Document not found",
                            })
                            continue

                        doc.content = apply(doc.content, op)
                        doc.version += 1
                        new_version = doc.version

                        db_op = Operation(
                            document_id=doc_id,
                            user_id=user_id,
                            op_type=op.type,
                            pos=op.pos,
                            text=op.text,
                            length=op.length,
                            version=new_version,
                        )
                        db.add(db_op)
                        db.commit()

                        await websocket.send_json({
                            "type": "op_ack",
                            "version": new_version,
                        })

                        await manager.broadcast(doc_id, {
                            "type": "op_broadcast",
                            "user_id": user_id,
                            "op": {
                                "type": op.type,
                                "pos": op.pos,
                                "text": op.text,
                                "length": op.length,
                            },
                        }, exclude=websocket)

                    except Exception as e:
                        db.rollback()
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })
                    finally:
                        db.close()

    except WebSocketDisconnect:
        await manager.leave(doc_id, websocket)
    except Exception:
        await manager.leave(doc_id, websocket)
