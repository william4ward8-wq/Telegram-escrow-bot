"""
Simplified SecureDealzBot - Clean version for Railway deployment
"""
import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from models import db, User, Deal, Transaction, DealStatus

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

class SimpleBotHandler:
    def __init__(self, flask_app):
        self.flask_app = flask_app
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Create welcome message
            welcome_msg = """
🎯 **Welcome to SecureDealzBot** 

Your trusted escrow service for secure cryptocurrency transactions!

✅ **What we offer:**
• Safe escrow for USDT, BTC, LTC deals
• Professional dispute resolution
• Top-rated seller verification
• 24/7 automated service

💰 **Fee Structure:**
• $5 flat fee for deals under $100
• 5% fee for deals over $100

🔒 **100% Secure & Trusted**

Choose an option below to get started:
"""
            
            # Create main menu keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🔗 Create Deal", callback_data="create_deal"),
                    InlineKeyboardButton("💰 My Wallet", callback_data="wallet")
                ],
                [
                    InlineKeyboardButton("📋 Active Deals", callback_data="my_deals"),
                    InlineKeyboardButton("⭐ Top Sellers", callback_data="top_sellers")
                ],
                [
                    InlineKeyboardButton("📞 Support", callback_data="help"),
                    InlineKeyboardButton("📚 User Guide", callback_data="guide")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Create user in database if needed
            if self.flask_app:
                with self.flask_app.app_context():
                    existing_user = User.query.filter_by(telegram_id=str(user.id)).first()
                    if not existing_user:
                        new_user = User(
                            telegram_id=str(user.id),
                            username=user.username or '',
                            first_name=user.first_name or '',
                            last_name=user.last_name or '',
                            is_admin=False
                        )
                        db.session.add(new_user)
                        db.session.commit()
                        logger.info(f"Created new user: {user.first_name}")
                        
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Welcome to SecureDealzBot! ⚡"
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            chat_id = query.message.chat_id
            
            if callback_data == "create_deal":
                msg = "🔗 **Create New Deal**\n\nComing soon! This feature is being finalized."
            elif callback_data == "wallet":
                msg = "💰 **My Wallet**\n\nWallet features coming soon!"
            elif callback_data == "my_deals":
                msg = "📋 **Active Deals**\n\nNo active deals found."
            elif callback_data == "top_sellers":
                msg = "⭐ **Top Sellers**\n\nTop sellers list coming soon!"
            elif callback_data == "help":
                msg = "📞 **Support**\n\nFor support, please contact our team."
            elif callback_data == "guide":
                msg = "📚 **User Guide**\n\nDetailed guide coming soon!"
            else:
                msg = "Feature coming soon!"
                
            # Go back button
            keyboard = [[InlineKeyboardButton("← Go Back", callback_data="start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if callback_data == "start":
                # Return to main menu
                await self.start_command(update, context)
                return
                
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=query.message.message_id,
                text=msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in button_handler: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **SecureDealzBot Help**

**Commands:**
/start - Main menu
/help - This help message

**Features:**
• Secure escrow transactions
• Multi-crypto support (USDT, BTC, LTC)
• Dispute resolution
• Top seller verification

**Support:** Available 24/7
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

def create_simple_application(flask_app):
    """Create a simple telegram application"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found")
        return None, None
        
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Create handler
    handler = SimpleBotHandler(flask_app)
    
    # Add handlers
    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("help", handler.help_command))
    application.add_handler(CallbackQueryHandler(handler.button_handler))
    
    return application, handler

def initialize_simple_bot(flask_app):
    """Initialize simple bot for webhook mode"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is required!")
        return False
    
    logger.info("🚀 Starting Simple SecureDealz Bot...")
    
    try:
        # Test database connection
        with flask_app.app_context():
            db.create_all()
            logger.info("✅ Database connection successful")
        
        # Create application
        application, handler = create_simple_application(flask_app)
        if not application:
            return False
            
        # Store in flask app for webhook handling
        flask_app.telegram_application = application
        flask_app.bot_handler = handler
        
        # Create event loop
        flask_app.event_loop = asyncio.new_event_loop()
        
        def run_event_loop():
            asyncio.set_event_loop(flask_app.event_loop)
            flask_app.event_loop.run_forever()
        
        # Start event loop in background
        import threading
        loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        loop_thread.start()
        
        # Initialize application
        async def init_app():
            await application.initialize()
            await application.start()
            logger.info("✅ Simple bot initialized successfully")
        
        # Run initialization
        future = asyncio.run_coroutine_threadsafe(init_app(), flask_app.event_loop)
        future.result(timeout=20)
        
        logger.info("🎉 Simple SecureDealz Bot ready for Railway!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Simple bot initialization failed: {e}")
        return False