import pandas as pd
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext
from datetime import datetime, date

TELEGRAM_BOT_TOKEN = "7562092255:AAHqP1_pk2hlSjnQeWbpL6tJXw9hCvSknyk"

# === Load Menu Data ===
MENU_FILE = "menu.csv"
ORDER_FILE = "orders.csv"

menu_df = pd.read_csv(MENU_FILE, delimiter='\t')

def get_malls():
    return sorted(menu_df['mall'].unique())

def get_stalls(mall):
    return sorted(menu_df[menu_df['mall'] == mall]['stall'].unique())

def get_dishes(mall, stall):
    return sorted(menu_df[(menu_df['mall'] == mall) & (menu_df['stall'] == stall)]['dish'].unique())

def log_order(username, mall, stall, dish):
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_entry = pd.DataFrame([[username, mall, stall, dish, time]], columns=['username', 'mall', 'stall', 'dish', 'timestamp'])
    try:
        orders_df = pd.read_csv(ORDER_FILE)
        orders_df = pd.concat([orders_df, new_entry], ignore_index=True)
    except FileNotFoundError:
        orders_df = new_entry
    orders_df.to_csv(ORDER_FILE, index=False)

def read_orders():
    try:
        return pd.read_csv(ORDER_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=['username', 'mall', 'stall', 'dish', 'timestamp'])

async def start(update: Update, context: CallbackContext):
    # If coming from the back button, check if it's a callback or message
    if update.message:
        # This case happens when the user starts from the main command
        keyboard = [[InlineKeyboardButton(mall, callback_data=f"mall:{mall}")] for mall in get_malls()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a mall:", reply_markup=reply_markup)
    else:
        # Handle callback query when coming back
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton(mall, callback_data=f"mall:{mall}")] for mall in get_malls()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a mall:", reply_markup=reply_markup)

async def mall_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    mall = query.data.split(":")[1]
    context.user_data['mall'] = mall
    stalls = get_stalls(mall)
    keyboard = [[InlineKeyboardButton(stall, callback_data=f"stall:{stall}")] for stall in stalls]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back:main")])
    await query.edit_message_text(text=f"Select a stall in {mall}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def stall_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stall = query.data.split(":")[1]
    mall = context.user_data['mall']
    context.user_data['stall'] = stall
    dishes = get_dishes(mall, stall)
    keyboard = [[InlineKeyboardButton(dish, callback_data=f"dish:{dish}")] for dish in dishes]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back:mall")])
    await query.edit_message_text(text=f"Menu for {stall}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def dish_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    dish = query.data.split(":")[1]
    mall = context.user_data['mall']
    stall = context.user_data['stall']
    username = query.from_user.first_name
    log_order(username, mall, stall, dish)
    await query.edit_message_text(text=f"✅ {username} ordered {dish} from {stall} at {mall}.")

async def back_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Ensure this is awaited
    target = query.data.split(":")[1]

    if target == "main":
        await start(update, context)
    elif target == "mall":
        mall = context.user_data.get("mall")
        if mall:
            await mall_handler(update, context)
    elif target == "stall":
        stall = context.user_data.get("stall")
        if stall:
            await stall_handler(update, context)

async def summary(update: Update, context: CallbackContext):
    df = read_orders()
    if df.empty:
        await update.message.reply_text("No orders have been placed yet.")
    else:
        today_str = date.today().strftime('%Y-%m-%d')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_today = df[df['timestamp'].dt.strftime('%Y-%m-%d') == today_str]

        if df_today.empty:
            await update.message.reply_text("No orders for today.")
        else:
            summary_text = "\n".join([f"{row['username']} ordered {row['dish']} from {row['stall']} ({row['mall']})"
                                     for _, row in df_today.iterrows()])
            await update.message.reply_text(f"Today's orders:\n{summary_text}")

async def reset(update: Update, context: CallbackContext):
    try:
        orders_df = pd.read_csv(ORDER_FILE)
        today_str = date.today().strftime('%Y-%m-%d')
        orders_df['timestamp'] = pd.to_datetime(orders_df['timestamp'])
        orders_df = orders_df[orders_df['timestamp'].dt.strftime('%Y-%m-%d') != today_str]
        orders_df.to_csv(ORDER_FILE, index=False)
        await update.message.reply_text("✅ Today's orders have been reset.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to reset: {str(e)}")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(mall_handler, pattern="^mall:"))
    app.add_handler(CallbackQueryHandler(stall_handler, pattern="^stall:"))
    app.add_handler(CallbackQueryHandler(dish_handler, pattern="^dish:"))
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back:"))

    await app.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
