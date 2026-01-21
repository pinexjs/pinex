import os
import telebot

# আমরা টোকেনটি রেলওয়ে থেকে নেব যেন কোডটি সুরক্ষিত থাকে
API_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "হাই মাদারি")

print("বট চলছে...")
bot.infinity_polling()
