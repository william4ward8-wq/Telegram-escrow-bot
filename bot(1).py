"""
DEPRECATED: This file is replaced by bot_simple.py for Railway deployment
Keep this minimal stub for backward compatibility only
"""
import logging

logger = logging.getLogger(__name__)

# DEPRECATED: Use bot_simple.py for Railway deployment
def initialize_bot_webhook(app_instance):
    """DEPRECATED: Use bot_simple.py initialize_simple_bot() instead"""
    logger.warning("⚠️ initialize_bot_webhook is deprecated - use bot_simple.py")
    logger.warning("⚠️ For Railway deployment, use: from bot_simple import initialize_simple_bot")
    return False

# All other bot functionality moved to bot_simple.py for clean Railway deployment