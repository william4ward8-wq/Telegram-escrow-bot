#!/usr/bin/env python3
"""
Simple bot runner that works around package issues
"""
import os
import sys

# Set environment for production
os.environ['PYTHONPATH'] = '/workspace'

def main():
    """Run the bot with proper error handling"""
    try:
        print("🚀 Starting Telegram Escrow Bot...")
        print("✅ Using database:", os.environ.get("DATABASE_URL", "Not configured")[:20] + "...")
        
        # Import the main module and bot initialization
        import main
        from bot import initialize_bot_webhook
        
        # Initialize bot for webhook mode
        print("🔧 Initializing Telegram bot for webhook mode...")
        if not initialize_bot_webhook(main.app):
            print("❌ Failed to initialize bot")
            exit(1)
        
        # Use dynamic PORT for production deployments
        port = int(os.environ.get("PORT", 5000))
        
        print(f"🌐 Starting server on port {port}")
        main.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()