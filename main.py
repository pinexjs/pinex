import requests
import time
import telebot
import threading
import os
import json
from flask import Flask
from collections import Counter
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ===========================
# ⚙️ কনফিগারেশন
# ===========================
BOT_TOKEN = "8519395029:AAFOKD3PUjngyl5Z08s5kEmPlCu5q1V7p4A" # আপনার দেওয়া টোকেন
CHANNEL_ID = "-1003561654748" # আপনার দেওয়া চ্যানেল আইডি
FIREBASE_URL = "https://hidndnd-default-rtdb.firebaseio.com"
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"

# Flask অ্যাপ (Render এর জন্য)
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
session = requests.Session()

# ক্যাশ ভেরিয়েবল
analysis_cache = {}
last_prediction = None
win_streak = 0
loss_streak = 0

@app.route('/')
def health():
    return "✅ SYSTEM ACTIVE: Bot & AI Logic Running..."

# ==========================================
# 🔍 ১. SCAN FEATURE (Telegram Bot)
# ==========================================
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("🔍 Scan Period (ইস্কন)"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "💎 **PINEX AI BOT Ready!**\nনিচের বাটন দিয়ে ম্যানুয়ালি চেক করতে পারেন।", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "🔍 Scan Period (ইস্কন)")
def ask_period(message):
    msg = bot.send_message(message.chat.id, "🔢 আপনি যে পিরিয়ডটি চেক করতে চান তার পুরো নাম্বার দিন:")
    bot.register_next_step_handler(msg, process_scan)

def process_scan(message):
    period_id = message.text.strip()
    try:
        resp = session.get(f"{FIREBASE_URL}/wingo_records/{period_id}.json")
        data = resp.json()
        
        if data:
            size = data.get('size', 'N/A')
            num = data.get('num', '?')
            icon = "🌕" if size == "BIG" else "🌑"
            msg = (f"✅ **Period Found!**\n━━━━━━━━━━━━━━━\n"
                   f"📍 Period: `{period_id}`\n"
                   f"🎯 Result: **{size} {icon}**\n"
                   f"🔢 Number: `{num}`\n━━━━━━━━━━━━━━━")
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ দুঃখিত! এই পিরিয়ডটি ডাটাবেজে পাওয়া যায়নি।")
    except:
        bot.send_message(message.chat.id, "⚠️ ডাটাবেজ এরর।")

# ==========================================
# 🧠 ২. ADVANCED AI ANALYSIS (6 Pattern Logic)
# ==========================================
def get_detailed_analysis():
    try:
        resp = session.get(f"{FIREBASE_URL}/wingo_records.json", timeout=10)
        data = resp.json()
        if not data or len(data) < 20: return None

        sorted_keys = sorted(data.keys())
        all_sizes = [data[k]['size'] for k in sorted_keys]
        
        # ৬ প্যাটার্ন চেক লজিক
        p_len = 6
        if len(all_sizes) < p_len + 1: return None

        current_pattern = all_sizes[-p_len:] # শেষের ৬টি রেকর্ড
        next_outcomes = []
        matched_periods = []

        # পুরো হিস্ট্রি চেক করা
        for i in range(len(all_sizes) - (p_len + 1)):
            if all_sizes[i:i+p_len] == current_pattern:
                period_id = sorted_keys[i+p_len]
                result = all_sizes[i+p_len]
                next_outcomes.append(result)
                matched_periods.append(f"`{period_id}` -> {result}")
        
        # যদি কোনো ম্যাচ না পাওয়া যায় -> SKIP
        if not next_outcomes:
            return {'predict': 'SKIP', 'matches': 0, 'acc': 0, 'history_list': []}

        # ম্যাচ পাওয়া গেলে ক্যালকুলেশন
        counts = Counter(next_outcomes)
        total = len(next_outcomes)
        big_p = round((counts.get('BIG', 0) / total) * 100, 2)
        small_p = round((counts.get('SMALL', 0) / total) * 100, 2)

        prediction = "BIG" if big_p >= small_p else "SMALL"
        acc = big_p if prediction == "BIG" else small_p

        return {
            'predict': prediction,
            'big_p': big_p,
            'small_p': small_p,
            'acc': acc,
            'matches': total,
            'history_list': matched_periods[-10:]
        }
    except Exception as e:
        print(f"Analysis Error: {e}")
        return None

# ==========================================
# 🔄 ৩. MAIN ENGINE (Data Loop)
# ==========================================
def start_engine():
    global last_prediction, analysis_cache, win_streak, loss_streak
    print("🚀 PINEX SYSTEM STARTED...")
    last_processed_issue = None
    
    # নতুন API তে হেডার সাধারণত সিম্পল থাকে
    headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile)'}

    while True:
        try:
            # টাইমস্ট্যাম্প সহ রিকোয়েস্ট
            response = session.get(API_URL, headers=headers, params={'ts': int(time.time()*1000)}, timeout=15)
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get('data') and json_data['data'].get('list'):
                    res = json_data['data']['list'][0]
                    issue = str(res.get('issueNumber')) # ফুল পিরিয়ড নাম্বার

                    if issue != last_processed_issue:
                        num = int(res.get('number', 0))
                        size = "BIG" if num >= 5 else "SMALL"
                        
                        # ১. ডাটাবেসে সেভ করা
                        session.put(f"{FIREBASE_URL}/wingo_records/{issue}.json", json={'size': size, 'num': num}, timeout=10)
                        
                        # ২. আগের রেজাল্ট চেক করা (Win/Loss)
                        if last_prediction and last_prediction['period'] == issue:
                            if last_prediction['predict'] == "SKIP":
                                res_text = f"⏩ **SKIPPED** | `{issue}`\nResult: **{size}**"
                            elif last_prediction['predict'] == size:
                                win_streak += 1
                                loss_streak = 0
                                res_text = f"💎 **WIN SUCCESS** | `{issue}`\n🎯 Result: **{size}**\n✅ Streak: **{win_streak}**"
                            else:
                                loss_streak += 1
                                win_streak = 0
                                res_text = f"❌ **LOSS** | `{issue}`\n🎯 Result: **{size}**\n🔻 Loss Streak: **{loss_streak}**"
                            
                            bot.send_message(CHANNEL_ID, res_text, parse_mode='Markdown')

                        # ৩. নতুন প্যাটার্ন এনালাইসিস
                        analysis = get_detailed_analysis()
                        next_p = str(int(issue) + 1) # পরবর্তী পিরিয়ড

                        if analysis:
                            if analysis['predict'] == "SKIP":
                                # প্যাটার্ন না মিললে
                                msg = (f"⚠️ **PATTERN NOT FOUND**\n"
                                       f"📍 Period: `{next_p}`\n"
                                       f"🚫 Signal: **SKIP (Risk)**\n"
                                       f"🔍 Database matches: 0")
                                bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown')
                                last_prediction = {'period': next_p, 'predict': "SKIP"}
                            else:
                                # প্যাটার্ন মিললে
                                icon = "🌕" if analysis['predict'] == "BIG" else "🌑"
                                msg = (f"👑 **PINEX PREMIUM SIGNAL**\n━━━━━━━━━━━━━━━━━━━━\n"
                                       f"📍 Period: `{next_p}`\n"
                                       f"🎯 Prediction: **{analysis['predict']} {icon}**\n\n"
                                       f"📊 Matches Found: `{analysis['matches']}`\n"
                                       f"🔥 Accuracy: `{analysis['acc']}%`\n━━━━━━━━━━━━━━━━━━━━")
                                
                                # বাটন সেট করা
                                analysis_cache[next_p] = analysis['history_list']
                                markup = InlineKeyboardMarkup()
                                markup.add(InlineKeyboardButton("📊 History Matches", callback_data=f"view_history:{next_p}"))
                                
                                bot.send_message(CHANNEL_ID, msg, parse_mode='Markdown', reply_markup=markup)
                                last_prediction = {'period': next_p, 'predict': analysis['predict']}
                        
                        last_processed_issue = issue

        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(5)
        
        time.sleep(3)

# কলব্যাক হ্যান্ডলার (হিস্ট্রি দেখার জন্য)
@bot.callback_query_handler(func=lambda call: call.data.startswith("view_history"))
def callback_history(call):
    try:
        period = call.data.split(":")[1]
        if period in analysis_cache:
            details = "\n".join(analysis_cache[period])
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"📊 **Match History:**\n{details}", parse_mode='Markdown')
        else:
            bot.answer_callback_query(call.id, "Old Data")
    except: pass

# ===========================
# 🔥 সার্ভার রানার
# ===========================
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    t1 = threading.Thread(target=start_engine, daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=run_flask, daemon=True)
    t2.start()
    
    bot.infinity_polling()
