# V10 NEXUS Swarm — Entry Point
import os
from app import create_app, socketio
from utils.crypto_utils import init_crypto_manager

master_key = os.environ.get("MASTER_KEY")
if master_key:
    init_crypto_manager(master_key)

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
