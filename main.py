"""
Main Flask application for Telegram Escrow Bot
"""
import os
import asyncio
import logging
import threading
from flask import Flask, request, jsonify
from models import db, User
# Removed nowpayments integration - using manual processing

# Create the Flask app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "escrow-bot-secret-key-2025"

# Force PostgreSQL for production reliability - no SQLite fallback
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL environment variable is required for production!")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
print(f"✅ Using database: {DATABASE_URL[:20]}...")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 1800,  # Recycle connections every 30 minutes
    "pool_pre_ping": True,  # Test connections before use
    "pool_size": 10,
    "max_overflow": 20,
}

# Initialize the database
db.init_app(app)

# Create all tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return {
        "message": "Telegram Escrow Bot API is running",
        "status": "active",
        "version": "1.0.0"
    }


@app.route('/health')
def health():
    return {"status": "healthy"}


@app.route('/manual-deposits', methods=['GET'])
def manual_deposits():
    """Endpoint for manual deposit status (for admin reference)"""
    return {
        "message": "Manual deposit processing active",
        "instructions": "All deposits require admin approval through Telegram bot",
        "status": "manual_processing"
    }


@app.route('/webhook', methods=['POST'])
def webhook():
    """Secured Telegram webhook endpoint for receiving updates"""
    try:
        # Security: Use secret token if configured (optional for easier setup)
        telegram_secret_token = os.environ.get("TELEGRAM_SECRET_TOKEN")
        if telegram_secret_token:
        
            provided_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if not provided_token or provided_token != telegram_secret_token:
                logging.warning(f"Webhook access denied - invalid secret token from {request.remote_addr}")
                return {'error': 'Unauthorized'}, 403
        
        # Check bot readiness
        telegram_app = getattr(app, 'telegram_application', None)
        event_loop = getattr(app, 'event_loop', None)
        if not telegram_app or not event_loop:
            logging.error("Webhook called but bot not initialized - dropping update")
            return {'error': 'Bot not ready'}, 503
        
        if request.content_type == 'application/json':
            json_data = request.get_json()
            # Process the webhook update asynchronously
            try:
                from telegram import Update
                update = Update.de_json(json_data, telegram_app.bot)
            except ImportError:
                # Fallback - process as raw JSON in deployment
                import json
                logging.info(f"Processing webhook with raw JSON: {json_data}")
                # Create a simple update object
                class SimpleUpdate:
                    def __init__(self, data):
                        self.update_id = data.get('update_id', 0)
                        self.message = data.get('message')
                        self.callback_query = data.get('callback_query')
                update = SimpleUpdate(json_data)
            asyncio.run_coroutine_threadsafe(
                telegram_app.process_update(update),
                event_loop
            )
            return {'status': 'ok'}, 200
        else:
            return {'error': 'Content-Type must be application/json'}, 400
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {'error': 'Internal server error'}, 500


@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Secured admin endpoint to set webhook"""
    try:
        # Security: Require admin authentication
        admin_secret = os.environ.get("ADMIN_SECRET")
        if not admin_secret:
            return {'error': 'Admin operations disabled - no ADMIN_SECRET configured'}, 501
        
        provided_secret = None
        if request.is_json and request.json:
            provided_secret = request.json.get('admin_secret')
        
        if not provided_secret or provided_secret != admin_secret:
            logging.warning(f"Unauthorized webhook admin access attempt from {request.remote_addr}")
            return {'error': 'Unauthorized'}, 403
        
        # Check bot readiness
        telegram_app = getattr(app, 'telegram_application', None)
        event_loop = getattr(app, 'event_loop', None)
        if not telegram_app or not event_loop:
            return {'error': 'Bot not initialized'}, 503
        
        webhook_url = None
        if request.is_json and request.json:
            webhook_url = request.json.get('webhook_url')
        if webhook_url:
            # Set webhook with secret token if available
            telegram_secret_token = os.environ.get("TELEGRAM_SECRET_TOKEN")
            
            # Set webhook and await completion for proper error handling
            if telegram_secret_token:
                future = asyncio.run_coroutine_threadsafe(
                    telegram_app.bot.set_webhook(
                        url=webhook_url,
                        secret_token=telegram_secret_token
                    ),
                    event_loop
                )
            else:
                future = asyncio.run_coroutine_threadsafe(
                    telegram_app.bot.set_webhook(url=webhook_url),
                    event_loop
                )
            try:
                future.result(timeout=30)  # Wait for completion
                logging.info(f"Webhook successfully set to: {webhook_url}")
                return {'status': 'webhook_set', 'url': webhook_url}, 200
            except Exception as webhook_error:
                logging.error(f"Failed to set webhook: {webhook_error}")
                return {'error': f'Webhook setup failed: {str(webhook_error)}'}, 500
        else:
            return {'error': 'webhook_url required'}, 400
    except Exception as e:
        logging.error(f"Set webhook error: {e}")
        return {'error': str(e)}, 500


@app.route('/ready')
def ready():
    """Readiness probe - returns healthy only when bot is fully initialized"""
    telegram_app = getattr(app, 'telegram_application', None)
    event_loop = getattr(app, 'event_loop', None)
    
    if telegram_app and event_loop:
        is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
        return {
            "status": "ready", 
            "mode": "webhook",
            "environment": "production" if is_production else "development",
            "bot_username": telegram_app.bot.username if hasattr(telegram_app.bot, 'username') else None
        }, 200
    else:
        return {"status": "not_ready", "error": "Bot not initialized"}, 503


@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information (admin only)"""
    try:
        # Security: Require admin authentication
        admin_secret = os.environ.get("ADMIN_SECRET")
        if not admin_secret:
            return {'error': 'Admin operations disabled'}, 501
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'error': 'Unauthorized - Bearer token required'}, 403
        
        provided_secret = auth_header[7:]  # Remove 'Bearer ' prefix
        if provided_secret != admin_secret:
            logging.warning(f"Unauthorized webhook info access attempt from {request.remote_addr}")
            return {'error': 'Unauthorized'}, 403
        
        telegram_app = getattr(app, 'telegram_application', None)
        event_loop = getattr(app, 'event_loop', None)
        
        if not telegram_app or not event_loop:
            return {'error': 'Bot not initialized'}, 503
        
        # Get webhook info asynchronously
        async def get_webhook_info_async():
            webhook_info = await telegram_app.bot.get_webhook_info()
            return {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": webhook_info.last_error_date.isoformat() if webhook_info.last_error_date else None,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates
            }
        
        future = asyncio.run_coroutine_threadsafe(
            get_webhook_info_async(), event_loop
        )
        result = future.result(timeout=30)
        return {"status": "success", "webhook_info": result}, 200
    except Exception as e:
        logging.error(f"Get webhook info error: {e}")
        return {'error': str(e)}, 500


if __name__ == '__main__':
    # Initialize bot for webhook mode
    try:
        import asyncio
        import threading
        import logging
        import os
        from bot import initialize_bot_webhook
        
        # Initialize bot for webhook mode
        print("🔧 Initializing Telegram bot for webhook mode...")
        if not initialize_bot_webhook(app):
            print("❌ Failed to initialize bot")
            exit(1)
        
        # Start Flask app with webhook mode integrated
        # Use dynamic PORT for production deployments
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start Flask app with bot: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)