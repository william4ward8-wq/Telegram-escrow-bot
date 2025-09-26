#!/usr/bin/env python3
"""
Simplified Railway deployment script - fixes import issues
This creates a minimal, working deployment for Railway
"""
import os
import sys
import logging

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run the bot with proper error handling and simplified imports"""
    try:
        logger.info("🚀 Starting SecureDealz Bot on Railway...")
        
        # Check required environment variables
        required_vars = ["BOT_TOKEN", "DATABASE_URL"]
        missing_vars = []
        
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            logger.error("Please add these variables in Railway dashboard -> Variables tab")
            sys.exit(1)
        
        logger.info("✅ All required environment variables found")
        
        # Import modules after environment check
        logger.info("📦 Importing application modules...")
        
        try:
            from main import app
            logger.info("✅ Main Flask app imported")
        except Exception as e:
            logger.error(f"❌ Failed to import main app: {e}")
            raise
        
        try:
            from bot import initialize_bot_webhook
            logger.info("✅ Bot module imported")
        except Exception as e:
            logger.error(f"❌ Failed to import bot module: {e}")
            raise
        
        # Initialize bot for webhook mode
        logger.info("🔧 Initializing bot for webhook mode...")
        if not initialize_bot_webhook(app):
            logger.error("❌ Failed to initialize bot webhook")
            sys.exit(1)
        
        logger.info("✅ Bot webhook initialized successfully")
        
        # Get port from Railway environment
        port = int(os.environ.get("PORT", 5000))
        host = "0.0.0.0"
        
        logger.info(f"🌐 Starting Flask server on {host}:{port}")
        logger.info("📡 Railway deployment mode - webhook ready")
        
        # Start the Flask app
        app.run(
            host=host, 
            port=port, 
            debug=False, 
            use_reloader=False,
            threaded=True
        )
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all required files are uploaded to GitHub:")
        logger.error("- main.py")
        logger.error("- bot.py") 
        logger.error("- models.py")
        logger.error("- requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()