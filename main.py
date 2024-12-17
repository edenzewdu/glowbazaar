import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Bot token
TELEGRAM_BOT_TOKEN = '7980677707:AAHOjt7GRuPsMEaI623OtauJ_XRuWA6V_t8'

# Initialize bot
if not TELEGRAM_BOT_TOKEN:
    logging.error("Bot token is missing! Please set the TELEGRAM_BOT_TOKEN variable.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# List of admin user IDs
admins = [709031839]  # Replace with actual admin IDs

# Dictionary to track product data for each admin
product_data = {}

# Track ongoing user-admin conversations
active_chats = {}

# Channel username or ID where product details are posted
channel_id = "@glowbazaartest"  # Replace with your channel's username or ID

# Ensure the 'photos' directory exists
if not os.path.exists("photos"):
    os.makedirs("photos")

# Function to post a product to the channel with markup
def post_product_to_channel(photo_path, product_name, description):
    try:
        # Prepare markup with a callback button
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Buy Product", callback_data=f"buy_product|{product_name}|{description}"))  # Updated callback

        # Send the photo to the channel with the markup
        bot.send_photo(
            chat_id=channel_id,
            photo=open(photo_path, 'rb'),
            caption=f"{product_name}\n\nDescription:\n{description}",
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
    bot.send_message(message.chat.id, "Photo received! Now send me the product name.")

# Step 2: Handle product name
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.from_user.id in product_data and "name" not in product_data[message.from_user.id])
def handle_product_name(message):
    product_data[message.from_user.id]["name"] = message.text
    bot.send_message(message.chat.id, "Product name received! Now send me the product description.")

# Step 3: Handle product description (caption)
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.from_user.id in product_data and "description" not in product_data[message.from_user.id])
def handle_description(message):
    product_data[message.from_user.id]["description"] = message.text
    bot.send_message(message.chat.id, "Description received! Type 'post' to post the product.")

# Step 4: Handle posting confirmation
@bot.message_handler(func=lambda message: message.from_user.id in admins and message.text.lower() == "post")
def handle_post(message):
    if message.from_user.id in product_data:
        data = product_data[message.from_user.id]
        post_product_to_channel(data["photo"], data["name"], data["description"])
        bot.send_message(message.chat.id, "Product posted successfully!")
        del product_data[message.from_user.id]  # Clear the admin's data after posting
    else:
        bot.send_message(message.chat.id, "No product data to post.")

# Step 5: Handle "Buy Product" button click
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_product"))
def handle_buy_product_click(call):
    try:
        # Parse the callback data (product name and description)
        _, product_name, description = call.data.split("|", 2)
        user_id = call.from_user.id
        user_name = f"{call.from_user.first_name} {call.from_user.last_name or ''}".strip()
        user_username = call.from_user.username

        # Send product details to admins (background notification)
        for admin_id in admins:
            bot.send_message(
                admin_id,
                f"User {user_name} (ID: {user_id}) is interested in the following product:\n\n"
                f"Product: {product_name}\n\nDescription: {description}\n\n"
                f"User Info:\nUsername: @{user_username}\nName: {user_name}\nID: {user_id}"
            )

        # Track the active chat between the user and the admin
        active_chats[user_id] = {"product": product_name}

        # Send a direct message to the user's inbox confirming the inquiry
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Back to Bot", url=f"t.me/{bot.get_me().username}"))  # Redirect to the bot

        # Directly send a message to the user's inbox (personal chat)
        bot.send_message(
            user_id,
            f"Thank you for your interest in {product_name}!\n\n"
            f"An admin will contact you soon to assist with your inquiry.\n\n"
            f"Please stay tuned.",
            reply_markup=markup
        )

        # Optionally, send a follow-up message to the user in their inbox (for example, asking for confirmation)
        bot.send_message(
            user_id,
            f"To proceed with your interest in {product_name}, an admin will get in touch with you shortly."
        )

    except Exception as e:
        logging.error(f"Failed to handle 'Buy Product' click: {e}")


# Function to relay messages from user to admin and vice versa
@bot.message_handler(func=lambda message: message.from_user.id in active_chats, content_types=["text", "photo", "video", "voice", "audio"])
def relay_message(message):
    chat_data = active_chats[message.from_user.id]

    # Determine whether the message is from the user or admin
    if message.from_user.id == chat_data.get("user"):
        recipient_id = chat_data.get("admin")  # Send to admin if the user is sending a message
    else:
        recipient_id = chat_data.get("user")  # Send to user if the admin is responding

    if message.content_type == "text":
        bot.send_message(recipient_id, f"Message from {message.from_user.first_name}:\n\n{message.text}")
    else:
        # Relay media message (photo, video, voice, etc.)
        relay_media_message(message, recipient_id, message.content_type)

# Admin responses to users using /respond command
@bot.message_handler(commands=["respond"])
def respond_to_user(message):
    try:
        # Command format: /respond <user_id> <message>
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.send_message(message.chat.id, "Usage: /respond <user_id> <message>")
            return

        user_id = int(args[1])
        response_message = args[2]

        # Send the response to the user
        bot.send_message(user_id, f"Admin Response:\n\n{response_message}")
        bot.send_message(message.chat.id, "Message sent to the user.")
    except Exception as e:
        logging.error(f"Failed to send admin response: {e}")
        bot.send_message(message.chat.id, "An error occurred while sending the message.")

# Start the bot
if __name__ == "__main__":
    logging.info("Bot is running...")
    bot.polling()
