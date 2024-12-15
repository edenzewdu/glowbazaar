import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Bot token
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot('7980677707:AAHOjt7GRuPsMEaI623OtauJ_XRuWA6V_t8')

# List of admin user IDs
admins = [709031839]  # Replace with actual admin IDs

# Dictionary to track product data for each admin
product_data = {}

# Channel username or ID where product details are posted
channel_id = "@glowbazaartest"  # Replace with your channel's username or ID

# Function to post a product to the channel with markup
def post_product_to_channel(photo_path, caption, buy_link, description):
    try:
        # Prepare markup with buttons
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Buy Product", url=buy_link))

        # Send the photo to the channel with the markup
        bot.send_photo(
            chat_id=channel_id,
            photo=open(photo_path, 'rb'),
            caption=f"{caption}\n\nDescription:\n{description}",
            reply_markup=markup
        )
        logging.info("Product posted successfully!")
    except Exception as e:
        logging.error(f"Failed to post product: {e}")

# Command to start product posting
@bot.message_handler(commands=["post_product"])
def start_product_posting(message):
    if message.from_user.id in admins:
        product_data[message.from_user.id] = {}
        bot.send_message(message.chat.id, "Please send the product photo.")
    else:
        bot.send_message(message.chat.id, "You are not authorized to perform this action.")

# Step 1: Handle photo upload from admin
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.from_user.id in product_data and "photo" not in product_data[message.from_user.id], content_types=["photo"])
def handle_photo(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Save the file to a local path
    photo_path = f"photos/photo_{message.from_user.id}.jpg"
    with open(photo_path, "wb") as new_file:
        new_file.write(downloaded_file)

    product_data[message.from_user.id]["photo"] = photo_path
    bot.send_message(message.chat.id, "Photo received! Now send me the product caption (description).")

# Step 2: Handle product caption
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.from_user.id in product_data and "caption" not in product_data[message.from_user.id])
def handle_caption(message):
    product_data[message.from_user.id]["caption"] = message.text
    bot.send_message(message.chat.id, "Caption received! Now send me the buy link.")

# Step 3: Handle buy link
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.from_user.id in product_data and "buy_link" not in product_data[message.from_user.id])
def handle_buy_link(message):
    product_data[message.from_user.id]["buy_link"] = message.text

    # Generate description automatically
    caption = product_data[message.from_user.id]["caption"]
    product_data[message.from_user.id]["description"] = f"This amazing product is available now! {caption}. Don't miss out on this great deal."

    bot.send_message(message.chat.id, "Buy link received! Do you want to post this product? (yes/no)")
    product_data[message.from_user.id]["ready"] = True

# Step 4: Handle confirmation to post
@bot.message_handler(func=lambda message: message.from_user.id in admins and product_data.get(message.from_user.id, {}).get("ready"))
def handle_post_confirmation(message):
    if message.text.lower() == "yes":
        data = product_data[message.from_user.id]

        # Post the product to the channel
        post_product_to_channel(data["photo"], data["caption"], data["buy_link"], data["description"])

        bot.send_message(message.chat.id, "Product posted successfully!")
        del product_data[message.from_user.id]  # Clear the admin's data after posting
    elif message.text.lower() == "no":
        bot.send_message(message.chat.id, "Product posting canceled.")
        del product_data[message.from_user.id]  # Clear the admin's data
    else:
        bot.send_message(message.chat.id, "Please reply with 'yes' or 'no'.")

# Handle messages from users
@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    user_id = message.from_user.id
    user_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

    # Notify admins about the new interaction
    for admin_id in admins:
        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton("Respond to user", callback_data=f"respond_{user_id}")
        markup.add(button)
        bot.send_message(
            admin_id,
            f"New user interaction: {user_name}",
            reply_markup=markup
        )

    # Reply to the user
    bot.send_message(user_id, "Hello! How can I help you today?")


# Handle admin responses
@bot.callback_query_handler(func=lambda call: call.data.startswith("respond_"))
def handle_admin_response(call):
    user_id = int(call.data.split("_")[1])
    admin_id = call.from_user.id

    if user_id in active_users:
        # If another admin is already assisting
        bot.answer_callback_query(call.id, "This user is already being assisted by another admin.")
    else:
        # Assign the user to the current admin
        active_users[user_id] = admin_id
        bot.answer_callback_query(call.id, "You are now assisting this user.")

        # Notify the admin that they are connected to the user
        bot.send_message(admin_id, f"You are now assisting the user with ID: {user_id}")


# Command for admins to stop assistance
@bot.message_handler(commands=["stop"])
def stop_assistance(message):
    admin_id = message.from_user.id

    # Check if the admin is assisting a user
    for user_id, assisting_admin in list(active_users.items()):
        if assisting_admin == admin_id:
            del active_users[user_id]
            bot.send_message(admin_id, "You have ended the conversation.")
            return

    # If the admin wasn't assisting anyone
    bot.send_message(admin_id, "You are not assisting any user currently.")
    
# Start the bot
if __name__ == "__main__":
    logging.info("Bot is running...")
    bot.polling()
