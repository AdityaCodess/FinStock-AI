# finstock-ai/backend/app/api/websockets.py
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services import prediction # We'll use our dummy prediction function

# Create a new router just for WebSockets
router = APIRouter(
    prefix="/ws",  # All routes in this file will start with /ws
    tags=["WebSockets"] # Group this in the docs
)

# This class will manage all active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_json(self, message: dict, websocket: WebSocket):
        """Sends a JSON message to a single websocket."""
        await websocket.send_text(json.dumps(message))

# Create a single instance of the manager to use in our endpoint
manager = ConnectionManager()


@router.websocket("/intraday")
async def websocket_intraday_feed(websocket: WebSocket):
    """
    WebSocket endpoint for the real-time intraday feed.
    """
    await manager.connect(websocket)
    
    # We need to know which stock to "track"
    # In a real app, the client would send this as the first message
    # For now, let's just default to a dummy symbol.
    symbol = "DUMMY.NS" 

    try:
        # Keep the connection alive, sending dummy data every 5 seconds
        while True:
            await asyncio.sleep(5) # Wait for 5 seconds
            
            # Get a new dummy prediction
            pred_data = prediction.get_intraday_prediction(symbol)
            
            # Format it as a WebSocket message
            message = {
                "type": "intraday_update",
                "data": pred_data
            }
            
            # Send the new prediction to the client
            await manager.send_json(message, websocket)
            
    except WebSocketDisconnect:
        print(f"Client disconnected from WebSocket.")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"An error occurred in the WebSocket: {e}")
        manager.disconnect(websocket)