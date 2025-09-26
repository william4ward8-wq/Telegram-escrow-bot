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
        
        # Auto-set webhook URL for Railway
        railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("WEBHOOK_BASE_URL")
        if railway_url:
            # Ensure railway_url doesn't have protocol prefix
            if railway_url.startswith("https://"):
                webhook_url = f"{railway_url}/webhook"
            else:
                webhook_url = f"https://{railway_url}/webhook"
            
            logger.info(f"🔗 Setting webhook URL automatically: {webhook_url}")
            
            # Set webhook using proper event loop integration
            try:
                import asyncio
                telegram_app = getattr(app, 'telegram_application', None)
                event_loop = getattr(app, 'event_loop', None)
                
                if telegram_app and event_loop:
                    # Get secret token if configured
                    secret_token = os.environ.get("TELEGRAM_SECRET_TOKEN")
                    
                    # Create async function to set webhook with proper configuration
                    async def set_webhook_async():
                        if secret_token:
                            result = await telegram_app.bot.set_webhook(
                                url=webhook_url,
                                secret_token=secret_token,
                                drop_pending_updates=True
                            )
                        else:
                            result = await telegram_app.bot.set_webhook(
                                url=webhook_url,
                                drop_pending_updates=True
                            )
                        return result
                    
                    # Run webhook setup using the application's event loop
                    future = asyncio.run_coroutine_threadsafe(set_webhook_async(), event_loop)
                    webhook_result = future.result(timeout=15)
                    
                    if webhook_result:
                        logger.info("✅ Webhook URL set successfully!")
                        
                        # Verify webhook configuration
                        async def verify_webhook():
                            info = await telegram_app.bot.get_webhook_info()
                            return info
                        
                        verify_future = asyncio.run_coroutine_threadsafe(verify_webhook(), event_loop)
                        webhook_info = verify_future.result(timeout=10)
                        
                        logger.info(f"✅ Webhook verified - URL: {webhook_info.url}")
                        if webhook_info.last_error_message:
                            logger.warning(f"⚠️ Last webhook error: {webhook_info.last_error_message}")
                        if webhook_info.pending_update_count > 0:
                            logger.info(f"📊 Pending updates: {webhook_info.pending_update_count}")
                    else:
                        logger.error("❌ Webhook setup returned False - setup failed")
                        
                else:
                    logger.warning("⚠️ Could not get telegram application or event loop")
                    
            except Exception as webhook_error:
                logger.error(f"❌ Failed to set webhook: {webhook_error}")
                logger.error("Bot will start but may need manual webhook setup")
                logger.error("Check Railway logs for webhook configuration issues")
        else:
            logger.warning("⚠️ RAILWAY_PUBLIC_DOMAIN/WEBHOOK_BASE_URL not found")
            logger.warning("Manual webhook setup may be required")
        
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