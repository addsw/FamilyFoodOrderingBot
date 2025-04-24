import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from datetime import datetime, date

TELEGRAM_BOT_TOKEN = "7562092255:AAHqP1_pk2hlSjnQeWbpL6tJXw9hCvSknyk"

# === Load Menu Data ===
MENU_FILE = "menu.xlsx"
ORDER_FILE = "orders.xlsx"

menu_df = pd.read_excel(MENU_FILE)

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
        orders_df = pd.read_excel(ORDER_FILE)
        orders_df = pd.concat([orders_df, new_entry], ignore_index=True)
    except FileNotFoundError:
        orders_df = new_entry
    orders_df.to_excel(ORDER_FILE, index=False)

def read_orders():
    try:
        return pd.read_excel(ORDER_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=['username', 'mall', 'stall', 'dish', 'timestamp'])

def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton(mall, callback_data=f"mall:{mall}")] for mall in get_malls()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Select a mall:", reply_markup=reply_markup)

def mall_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    mall = query.data.split(":")[1]
    context.user_data['mall'] = mall
    stalls = get_stalls(mall)
    keyboard = [[InlineKeyboardButton(stall, callback_data=f"stall:{stall}")] for stall in stalls]
    query.edit_message_text(text=f"Select a stall in {mall}:", reply_markup=InlineKeyboardMarkup(keyboard))

def stall_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    stall = query.data.split(":")[1]
    mall = context.user_data['mall']
    context.user_data['stall'] = stall
    dishes = get_dishes(mall, stall)
    keyboard = [[InlineKeyboardButton(dish, callback_data=f"dish:{dish}")] for dish in dishes]
    query.edit_message_text(text=f"Menu for {stall}:", reply_markup=InlineKeyboardMarkup(keyboard))

def dish_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    dish = query.data.split(":")[1]
    mall = context.user_data['mall']
    stall = context.user_data['stall']
    username = query.from_user.first_name
    log_order(username, mall, stall, dish)
    query.edit_message_text(text=f"✅ {username}, you ordered {dish} from {stall} at {mall}.")

def summary(update: Update, context: CallbackContext):
    df = read_orders()
    if df.empty:
        update.message.reply_text("No orders have been placed yet.")
    else:
        today_str = date.today().strftime('%Y-%m-%d')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_today = df[df['timestamp'].dt.strftime('%Y-%m-%d') == today_str]

        if df_today.empty:
            update.message.reply_text("No orders for today.")
        else:
            summary_text = "\n".join([
                f"{row['username']} ordered {row['dish']} from {row['stall']} ({row['mall']})"
                for _, row in df_today.iterrows()
            ])
            update.message.reply_text(f"Today's orders:\n{summary_text}")

def reset(update: Update, context: CallbackContext):
    try:
        orders_df = pd.read_excel(ORDER_FILE)
        today_str = date.today().strftime('%Y-%m-%d')
        orders_df['timestamp'] = pd.to_datetime(orders_df['timestamp'])
        orders_df = orders_df[orders_df['timestamp'].dt.strftime('%Y-%m-%d') != today_str]
        orders_df.to_excel(ORDER_FILE, index=False)
        update.message.reply_text("✅ Today's orders have been reset.")
    except Exception as e:
        update.message.reply_text(f"❌ Failed to reset: {str(e)}")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("summary", summary))
    dp.add_handler(CommandHandler("reset", reset))
    dp.add_handler(CallbackQueryHandler(mall_handler, pattern="^mall:"))
    dp.add_handler(CallbackQueryHandler(stall_handler, pattern="^stall:"))
    dp.add_handler(CallbackQueryHandler(dish_handler, pattern="^dish:"))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
