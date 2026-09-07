import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import Database
from datetime import datetime

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Bot token
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Helper function to create main menu keyboard
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data='balance'),
         InlineKeyboardButton("📊 Stake", callback_data='stake')],
        [InlineKeyboardButton("🎁 Claim Rewards", callback_data='claim'),
         InlineKeyboardButton("📈 Stats", callback_data='stats')],
        [InlineKeyboardButton("📜 History", callback_data='history'),
         InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("❓ Help", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username or "NoUsername"
    first_name = user.first_name or "User"
    
    # Register user
    db.register_user(user_id, username, first_name)
    
    welcome_message = f"""
🎁 Welcome to Prizes_6bot, {first_name}! 

💰 Stake your crypto and earn rewards!
📈 Track your portfolio
🎁 Claim rewards automatically

Use the buttons below to get started:

✅ Earn 5% rewards per hour on staked tokens
✅ Secure and transparent
✅ Instant withdrawals
"""
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard()
    )

# Balance command
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    if user:
        balance_text = f"""
💰 *Your Balance*

💵 Available: {user[3]:.2f} tokens
🔒 Staked: {user[4]:.2f} tokens
🎁 Total Earned: {user[6]:.2f} tokens

*Total Value:* {user[3] + user[4]:.2f} tokens
"""
        await query.edit_message_text(
            balance_text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

# Stake command
async def stake_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💰 Stake 10 tokens", callback_data='stake_10')],
        [InlineKeyboardButton("💰 Stake 50 tokens", callback_data='stake_50')],
        [InlineKeyboardButton("💰 Stake 100 tokens", callback_data='stake_100')],
        [InlineKeyboardButton("💰 Custom Amount", callback_data='stake_custom')],
        [InlineKeyboardButton("🔓 Unstake All", callback_data='unstake')],
        [InlineKeyboardButton("⬅️ Back", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = db.get_user(query.from_user.id)
    staked = user[4] if user else 0
    
    await query.edit_message_text(
        f"📊 *Staking Menu*\n\n"
        f"Current Staked: {staked:.2f} tokens\n"
        f"Reward Rate: 5% per hour\n\n"
        f"Choose an option below:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stake_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    try:
        amount = float(query.data.split('_')[1])
        user_id = query.from_user.id
        user = db.get_user(user_id)
        
        if not user or user[3] < amount:
            await query.edit_message_text(
                f"❌ Insufficient balance! You have {user[3] if user else 0:.2f} tokens available.",
                reply_markup=get_main_keyboard()
            )
            return
        
        if db.stake_tokens(user_id, amount):
            updated_user = db.get_user(user_id)
            await query.edit_message_text(
                f"✅ Successfully staked {amount:.2f} tokens!\n\n"
                f"💵 New Balance: {updated_user[3]:.2f} tokens\n"
                f"🔒 Total Staked: {updated_user[4]:.2f} tokens\n\n"
                f"🎁 You'll earn 5% rewards per hour!",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Failed to stake tokens. Please try again.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Error: {str(e)}",
            reply_markup=get_main_keyboard()
        )

async def stake_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💰 Enter the amount of tokens you want to stake:\n\n"
        "Send a number (e.g., 25) in the chat.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Cancel", callback_data='stake')]
        ])
    )
    context.user_data['awaiting_stake'] = True

async def handle_stake_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get('awaiting_stake'):
        return
    
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        user = db.get_user(user_id)
        
        if amount <= 0:
            await update.message.reply_text("❌ Please enter a positive number.")
            return
        
        if not user or user[3] < amount:
            await update.message.reply_text(
                f"❌ Insufficient balance! You have {user[3] if user else 0:.2f} tokens available."
            )
            return
        
        if db.stake_tokens(user_id, amount):
            updated_user = db.get_user(user_id)
            await update.message.reply_text(
                f"✅ Successfully staked {amount:.2f} tokens!\n\n"
                f"💵 New Balance: {updated_user[3]:.2f} tokens\n"
                f"🔒 Total Staked: {updated_user[4]:.2f} tokens",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text("❌ Failed to stake tokens.")
            
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
    
    context.user_data['awaiting_stake'] = False

async def unstake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    if not user or user[4] <= 0:
        await query.edit_message_text(
            "❌ You don't have any staked tokens.",
            reply_markup=get_main_keyboard()
        )
        return
    
    if db.unstake_tokens(user_id):
        updated_user = db.get_user(user_id)
        await query.edit_message_text(
            f"✅ Successfully unstaked all tokens!\n\n"
            f"💵 New Balance: {updated_user[3]:.2f} tokens\n"
            f"🔒 Staked: 0 tokens",
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Failed to unstake tokens.",
            reply_markup=get_main_keyboard()
        )

# Claim rewards
async def claim_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    reward = db.claim_rewards(user_id)
    
    if reward > 0:
        user = db.get_user(user_id)
        await query.edit_message_text(
            f"🎁 *Rewards Claimed!*\n\n"
            f"💰 Reward Amount: {reward:.2f} tokens\n"
            f"💵 New Balance: {user[3]:.2f} tokens\n"
            f"🔒 Staked: {user[4]:.2f} tokens\n\n"
            f"Keep staking to earn more!",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ No rewards available to claim.\n\n"
            "Make sure you have tokens staked for at least 1 hour.",
            reply_markup=get_main_keyboard()
        )

# Stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    total_users, total_staked, total_rewards = db.get_stats()
    
    stats_text = f"""
📈 *Bot Statistics*

👥 Total Users: {total_users}
💰 Total Staked: {total_staked:.2f} tokens
🎁 Total Rewards Paid: {total_rewards:.2f} tokens
💎 Reward Rate: 5% per hour

*Top Stakers:*
"""
    
    top_stakers = db.get_top_stakers()
    for i, (user_id, amount) in enumerate(top_stakers, 1):
        user = db.get_user(user_id)
        username = user[1] if user else "Unknown"
        stats_text += f"{i}. @{username}: {amount:.2f} tokens\n"
    
    await query.edit_message_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# History
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    transactions = db.get_transactions(query.from_user.id)
    
    if not transactions:
        await query.edit_message_text(
            "📜 No transaction history found.",
            reply_markup=get_main_keyboard()
        )
        return
    
    history_text = "📜 *Transaction History*\n\n"
    for trans_type, amount, timestamp, desc in transactions:
        emoji = "💰" if trans_type in ['REWARD', 'STAKE'] else "🔓"
        history_text += f"{emoji} {trans_type}: {amount:.2f} tokens\n"
        history_text += f"   📅 {timestamp[:10]}\n"
    
    await query.edit_message_text(
        history_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Leaderboard
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    top_stakers = db.get_top_stakers(10)
    
    if not top_stakers:
        await query.edit_message_text(
            "🏆 No stakers yet. Be the first!",
            reply_markup=get_main_keyboard()
        )
        return
    
    leaderboard_text = "🏆 *Staking Leaderboard*\n\n"
    for i, (user_id, amount) in enumerate(top_stakers, 1):
        user = db.get_user(user_id)
        username = user[1] if user else "Unknown"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{medal} @{username}: {amount:.2f} tokens\n"
    
    await query.edit_message_text(
        leaderboard_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    help_text = """
❓ *How to use Prizes_6bot*

💰 *Balance* - Check your token balance
📊 *Stake* - Stake your tokens to earn rewards
🎁 *Claim Rewards* - Collect your staking rewards
📈 *Stats* - View bot statistics
📜 *History* - View your transaction history
🏆 *Leaderboard* - See top stakers

*Staking Rewards:*
• Earn 5% per hour on staked tokens
• Rewards compound automatically
• No minimum staking period

*Commands:*
/start - Start the bot
/balance - Check balance
/stake - Stake tokens
/claim - Claim rewards
/help - Show this message
"""
    
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Back to main
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    username = user[1] if user else "User"
    
    await query.edit_message_text(
        f"🏠 *Main Menu*\n\nWelcome back, {username}!",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# Text message handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle custom stake input
    if context.user_data.get('awaiting_stake'):
        await handle_stake_input(update, context)
        return
    
    # Default response
    await update.message.reply_text(
        "Use the buttons below to navigate the bot!",
        reply_markup=get_main_keyboard()
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=get_main_keyboard()
        )

def main() -> None:
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start))
        
        # Register callback query handlers
        application.add_handler(CallbackQueryHandler(balance, pattern='balance'))
        application.add_handler(CallbackQueryHandler(stake_menu, pattern='stake'))
        application.add_handler(CallbackQueryHandler(stake_amount, pattern='stake_\\d+'))
        application.add_handler(CallbackQueryHandler(stake_custom, pattern='stake_custom'))
        application.add_handler(CallbackQueryHandler(unstake, pattern='unstake'))
        application.add_handler(CallbackQueryHandler(claim_rewards, pattern='claim'))
        application.add_handler(CallbackQueryHandler(stats, pattern='stats'))
        application.add_handler(CallbackQueryHandler(history, pattern='history'))
        application.add_handler(CallbackQueryHandler(leaderboard, pattern='leaderboard'))
        application.add_handler(CallbackQueryHandler(help_command, pattern='help'))
        application.add_handler(CallbackQueryHandler(back_to_main, pattern='back_to_main'))
        
        # Register text message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Register error handler
        application.add_error_handler(error_handler)

        # Start the Bot
        print("🤖 Prizes_6bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
