from json import JSONDecodeError, loads
from aiohttp import WSMessage, WSMsgType, web
from aiohttp_apispec import docs, request_schema, setup_aiohttp_apispec
from marshmallow import ValidationError

from message import send_message_to_all, send_message
from schema import MessageSchema

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@docs(
   tags=["telegram"],
   summary="Send message API",
   description="This end-point sends message to telegram bot user/users",
)
@request_schema(MessageSchema())
@routes.post("/")
async def index_get(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except JSONDecodeError:
        return web.json_response({"result": "Request data is invalid"})

    try:
        schema = MessageSchema()
        data = schema.load(payload)
    except ValidationError as e:
        return web.json_response({"result": "Validation Error", "error": e.messages})

    if data.get("chat_id"):
        await send_message(data.get("chat_id"), data.get("message"))
    else:
        await send_message_to_all(data.get("message"))
    return web.json_response({"result": "OK"})

@docs(
   tags=["websocket"],
   summary="Websocket endpoint",
   description="Connect to websocket",
)
@request_schema(MessageSchema())
@routes.get("/ws")
async def websockets(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:  # type: WSMessage
        if msg.type == WSMsgType.TEXT:
            if msg.data == "/close":
                await ws.close()
            else:
                data = loads(msg.data)
                if data.get("chat.id"):
                    await send_message(data.get("chat.id"), data.get("message"))
                else:
                    await send_message_to_all(data.get("message"))
                await ws.send_str(msg.data)
        elif msg.type == WSMsgType.ERROR:
            logger.error(f"WS connection closed with exception {request.app.ws.exception()}")
    return ws



if __name__ == "__main__":
    app = web.Application()
    setup_aiohttp_apispec(
        app=app, title="telegram_bot Bot documentation", version="v1.0",
        url="/api/docs/swagger.json", swagger_path="/api/docs",
    )
    app.add_routes(routes)
    web.run_app(app, port=5000)