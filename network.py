# network.py
import websocket
import threading
import json
from collections import deque

class Network:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.thread = None
        self.is_connected = False
        self.received_messages = deque()

    def connect(self, room_code):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        
        # Guardamos el código de la sala para el mensaje de 'join'
        self.room_code = room_code

    def on_open(self, ws):
        print("Conexión establecida.")
        self.is_connected = True
        # Unirse a la sala
        join_message = {"type": "join", "room": self.room_code}
        self.send(join_message)

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.received_messages.append(data)
        except json.JSONDecodeError:
            print(f"Error decodificando mensaje: {message}")

    def on_error(self, ws, error):
        print(f"Error de conexión: {error}")
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        print("Conexión cerrada.")
        self.is_connected = False

    def send(self, data):
        if self.is_connected and self.ws:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                print(f"Error al enviar datos: {e}")
    
    def get_message(self):
        if self.received_messages:
            return self.received_messages.popleft()
        return None

    def disconnect(self):
        if self.ws:
            self.ws.close()