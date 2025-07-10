from http.server import BaseHTTPRequestHandler
import json
import asyncio
import asyncpg
import logging
from urllib.parse import quote
import os
import urllib.request
import urllib.parse

# Konfigurasi dari Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN", "8186303125:AAEU3cKzbllqtiot55iRbDf0Q5yK44EelGA")
BOT_USERNAME = "@StoreDB_airdropbot"

# Konfigurasi Database
DB_CONFIG = {
    "user": os.getenv("DB_USER", "neondb_owner"),
    "password": os.getenv("DB_PASSWORD", "npg_ntWwHqA9dKI2"),
    "database": os.getenv("DB_NAME", "neondb"),
    "host": os.getenv("DB_HOST", "ep-lucky-shape-a14jznh2-pooler.ap-southeast-1.aws.neon.tech"),
    "port": os.getenv("DB_PORT", "5432"),
    "ssl": "require"
}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_db_connection():
    """Membuat koneksi database"""
    try:
        conn = await asyncpg.connect(
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            ssl=DB_CONFIG['ssl']
        )
        return conn
    except Exception as e:
        logger.error(f"Gagal membuat koneksi database: {e}")
        raise

async def save_message_to_db(message_text: str, source_link=None, is_forwarded=False):
    """Menyimpan pesan ke database"""
    try:
        conn = await create_db_connection()
        await conn.execute(
            """INSERT INTO messages 
            (message, source_link, is_forwarded) 
            VALUES ($1, $2, $3)""",
            message_text,
            source_link,
            is_forwarded
        )
        await conn.close()
        logger.info(f"Pesan disimpan: {message_text[:100]}...")
        return True
    except Exception as e:
        logger.error(f"Gagal menyimpan pesan ke database: {e}")
        return False

def generate_group_link(chat_id, message_id=None):
    """Generate link grup/channel Telegram"""
    base_url = "https://t.me/c/"
    chat_id_str = str(chat_id).replace('-100', '')
    if message_id:
        return f"{base_url}{chat_id_str}/{message_id}"
    return f"{base_url}{chat_id_str}"

async def send_telegram_message(chat_id, text):
    """Mengirim pesan ke Telegram menggunakan urllib"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    
    try:
        # Convert data to JSON string
        json_data = json.dumps(data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Send request
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
            
    except Exception as e:
        logger.error(f"Gagal mengirim pesan: {e}")
        return None

async def handle_telegram_update(update_data):
    """Menangani update dari Telegram"""
    try:
        # Parse update data
        if "message" not in update_data:
            return {"status": "ok", "message": "No message in update"}
        
        message = update_data["message"]
        chat_id = message["chat"]["id"]
        chat_type = message["chat"]["type"]
        
        # Ambil teks pesan
        message_text = message.get("text") or message.get("caption")
        
        if not message_text:
            if chat_type == "private":
                await send_telegram_message(chat_id, "Maaf, saya hanya menyimpan teks. Gambar tidak disimpan.")
            return {"status": "ok", "message": "No text in message"}
        
        # Cek jika pesan diforward
        source_link = None
        is_forwarded = False
        
        if "forward_origin" in message:
            forward_origin = message["forward_origin"]
            if forward_origin.get("type") == "channel":
                try:
                    origin_chat_id = forward_origin["chat"]["id"]
                    message_id = forward_origin["message_id"]
                    source_link = generate_group_link(origin_chat_id, message_id)
                    is_forwarded = True
                except Exception as e:
                    logger.error(f"Gagal generate link channel: {e}")
        
        logger.info(f'User ({chat_id}) in {chat_type}: "{message_text[:100]}..." | Forwarded: {is_forwarded}')
        
        # Handle berdasarkan chat type
        if chat_type == "private":
            # Simpan ke database
            success = await save_message_to_db(message_text, source_link, is_forwarded)
            
            if success:
                reply_text = "Pesan teks Anda telah disimpan ke database!"
                if is_forwarded and source_link:
                    reply_text += f"\n\nLink sumber: {source_link}"
                await send_telegram_message(chat_id, reply_text)
            else:
                await send_telegram_message(chat_id, "Maaf, terjadi kesalahan saat menyimpan pesan.")
        else:
            await send_telegram_message(chat_id, "Silakan kirim pesan secara private ke bot ini.")
        
        return {"status": "ok", "message": "Message processed successfully"}
        
    except Exception as e:
        logger.error(f"Error handling update: {e}")
        return {"status": "error", "message": str(e)}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request untuk health check"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "ok",
            "message": "Telegram Bot Webhook is running!",
            "bot": BOT_USERNAME
        }
        
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle POST request dari Telegram webhook"""
        try:
            # Baca data dari request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse JSON
            update_data = json.loads(post_data.decode('utf-8'))
            
            # Process update menggunakan asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(handle_telegram_update(update_data))
            loop.close()
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logger.error(f"Error in POST handler: {e}")
            
            # Send error response
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                "status": "error",
                "message": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())

# Export handler untuk Vercel
def lambda_handler(event, context):
    """Handler untuk serverless deployment"""
    return handler(event, context)
