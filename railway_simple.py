#!/usr/bin/env python3
"""
Simple, reliable Railway deployment script
This ensures the Flask app starts properly on Railway
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the bot with minimal complexity for Railway"""
    try:
        logger.info("🚀 Starting SecureDealz Bot on Railway (Simple Mode)...")
        
        # Verify environment variables
        bot_token = os.environ.get("BOT_TOKEN")
        database_url = os.environ.get("DATABASE_URL")
        
        if not bot_token:
            logger.error("❌ BOT_TOKEN environment variable missing")
            sys.exit(1)
            
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable missing")
            sys.exit(1)
            
        logger.info("✅ Environment variables validated")
        
        # Import Flask app
        logger.info("📦 Importing Flask application...")
        from main import app
        logger.info("✅ Flask app imported successfully")
        
        # Import and initialize bot
        logger.info("🤖 Initializing Telegram bot...")
        from bot import initialize_bot_webhook
        
        if not initialize_bot_webhook(app):
            logger.error("❌ Failed to initialize bot webhook")
            sys.exit(1)
            
        logger.info("✅ Bot webhook initialized successfully")
        
        # Get Railway port
        port = int(os.environ.get("PORT", 5000))
        host = "0.0.0.0"
        
        logger.info(f"🌐 Starting Flask server on {host}:{port}")
        logger.info("🎯 Railway deployment ready!")
        
        # Start Flask app with error handling
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all files are uploaded to GitHub and Railway can access them")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()