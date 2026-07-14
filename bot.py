import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import sqlite3
import datetime
import re
import logging
import time
import random

# ============ কনফিগারেশন ============
BOT_TOKEN = "8259931774:AAHDDs_nTMgwtds7EW0TAKYeloXgvU3HRCc"
API_URL = "http://148.251.193.195/~ivgqasuc/Api.php"
ADMIN_IDS = [1849126202, 8525591614]
DEFAULT_CHANNEL_USERNAME = "@your_channel"
DEFAULT_CHANNEL_LINK = "https://t.me/your_channel"
DEV_NAME = "NOOBXVAU"
DEV_TELEGRAM = "@noobxvau"
DEV_GITHUB = "https://github.com/noobxvau"
BOT_NAME = "NHBD LOG HUNT"

# ============ ইমোজি ============
EMOJI = {
    'search': '🔍', 'profile': '👤', 'refer': '👥', 'latest': '📰',
    'developer': '👨‍💻', 'channel': '📢', 'admin': '⚙️', 'coins': '🪙',
    'success': '✅', 'error': '❌', 'loading': '⏳', 'back': '🔙',
    'menu': '📋', 'sparkle': '✨', 'link': '🔗', 'copy': '📋',
    'warning': '⚠️', 'lock': '🔒', 'refresh': '🔄', 'star': '⭐️',
    'diamond': '💎', 'heart': '❤️', 'trophy': '🏆', 'magic': '🪄',
}

# ============ ডেটাবেস ============
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        coins INTEGER DEFAULT 5,
        join_date TIMESTAMP,
        referred_by INTEGER DEFAULT NULL,
        is_verified INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        total_searches INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        refer_date TIMESTAMP,
        is_valid INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        search_term TEXT,
        search_date TIMESTAMP,
        coins_used INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        target_user INTEGER,
        details TEXT,
        log_date TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS channel_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO channel_settings (setting_key, setting_value) VALUES (?, ?)", 
              ('channel_username', DEFAULT_CHANNEL_USERNAME))
    c.execute("INSERT OR IGNORE INTO channel_settings (setting_key, setting_value) VALUES (?, ?)", 
              ('channel_link', DEFAULT_CHANNEL_LINK))
    conn.commit()
    conn.close()
    print("✅ ডেটাবেস তৈরি হয়েছে!")

init_db()

# ============ চ্যানেল ============
_channel_cache = None

def get_channel_username():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT setting_value FROM channel_settings WHERE setting_key = 'channel_username'")
    result = c.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_CHANNEL_USERNAME

def get_channel_link():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT setting_value FROM channel_settings WHERE setting_key = 'channel_link'")
    result = c.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_CHANNEL_LINK

def get_cached_channel():
    global _channel_cache
    if _channel_cache is None:
        _channel_cache = {'username': get_channel_username(), 'link': get_channel_link()}
    return _channel_cache

def update_channel_settings(username, link):
    try:
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute("UPDATE channel_settings SET setting_value = ? WHERE setting_key = 'channel_username'", (username,))
        c.execute("UPDATE channel_settings SET setting_value = ? WHERE setting_key = 'channel_link'", (link,))
        conn.commit()
        conn.close()
        global _channel_cache
        _channel_cache = None
        return True
    except Exception as e:
        print(f"❌ চ্যানেল আপডেট করতে ব্যর্থ: {e}")
        return False

# ============ ইউজার ফাংশন ============
def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY join_date DESC")
    users = c.fetchall()
    conn.close()
    return users

def get_user_count():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_coins(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_referral_count(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND is_valid = 1", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_referral_link(user_id):
    try:
        bot_username = bot.get_me().username
        return f"https://t.me/{bot_username}?start=ref_{user_id}"
    except:
        return f"https://t.me/your_bot?start=ref_{user_id}"

def add_coins(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def use_coins(user_id, amount=1):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins - ?, total_searches = total_searches + 1 WHERE user_id = ? AND coins >= ?", 
              (amount, user_id, amount))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def check_channel_membership(user_id):
    try:
        channel = get_cached_channel()['username']
        member = bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_user_verified(user_id):
    user = get_user(user_id)
    return user[7] == 1 if user else False

# ============ রেফারেল সিস্টেম ============
def add_user(user_id, username, first_name, last_name, referred_by=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if c.fetchone():
        conn.close()
        return False, None
    
    join_date = datetime.datetime.now()
    
    c.execute("""INSERT INTO users (user_id, username, first_name, last_name, coins, join_date, referred_by) 
                 VALUES (?, ?, ?, ?, 5, ?, ?)""",
              (user_id, username, first_name, last_name, join_date, referred_by))
    
    if referred_by:
        c.execute("SELECT * FROM referrals WHERE referred_id = ?", (user_id,))
        if not c.fetchone():
            c.execute("""INSERT INTO referrals (referrer_id, referred_id, refer_date, is_valid) 
                         VALUES (?, ?, ?, 0)""",
                      (referred_by, user_id, datetime.datetime.now()))
            c.execute("UPDATE users SET coins = coins + 3 WHERE user_id = ?", (referred_by,))
    
    conn.commit()
    conn.close()
    return True, referred_by

def verify_referral(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    c.execute("SELECT id, referrer_id FROM referrals WHERE referred_id = ? AND is_valid = 0", (user_id,))
    referral = c.fetchone()
    
    if referral:
        c.execute("UPDATE referrals SET is_valid = 1 WHERE id = ?", (referral[0],))
        c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
        c.execute("UPDATE users SET coins = coins + 3 WHERE user_id = ?", (referral[1],))
        
        conn.commit()
        conn.close()
        return True, referral[1]
    
    conn.close()
    return False, None

# ============ বট ============
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
logging.basicConfig(level=logging.INFO)

# ============ পার্মানেন্ট বাটন ============
def get_permanent_keyboard(user_id=None):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton(f"{EMOJI['search']} সার্চ করুন"),
        KeyboardButton(f"{EMOJI['profile']} প্রোফাইল")
    )
    keyboard.add(
        KeyboardButton(f"{EMOJI['refer']} রেফার করুন"),
        KeyboardButton(f"{EMOJI['latest']} লেটেস্ট")
    )
    keyboard.add(
        KeyboardButton(f"{EMOJI['developer']} ডেভেলপার"),
        KeyboardButton(f"{EMOJI['channel']} চ্যানেল")
    )
    if user_id and is_admin(user_id):
        keyboard.add(
            KeyboardButton(f"{EMOJI['admin']} অ্যাডমিন প্যানেল")
        )
    return keyboard

def get_inline_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(f"{EMOJI['search']} নতুন সার্চ", callback_data="new_search"),
        InlineKeyboardButton(f"{EMOJI['back']} মেনু", callback_data="back_main")
    )
    return keyboard

def send_verification_request(message):
    channel = get_cached_channel()
    text = f"""
{EMOJI['lock']} <b>চ্যানেল ভেরিফিকেশন প্রয়োজন!</b>

{EMOJI['warning']} বট ব্যবহার করতে হলে আমাদের চ্যানেল জয়েন করতে হবে।

{EMOJI['channel']} <b>চ্যানেল:</b> {channel['username']}
{EMOJI['link']} <b>লিংক:</b> {channel['link']}

1️⃣ চ্যানেল জয়েন করুন
2️⃣ "ভেরিফাই করেছি" বাটন চাপুন
    """
    bot.reply_to(message, text, parse_mode='HTML', 
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(f"{EMOJI['channel']} চ্যানেল জয়েন", url=channel['link']),
                    InlineKeyboardButton(f"{EMOJI['success']} ভেরিফাই করেছি", callback_data="verify_me")
                ))

def coin_display(user_id):
    return f"{EMOJI['coins']} কয়েন: {get_coins(user_id)}"

# ============ ডাটা পার্সার - Owner বাদ ============
def extract_all_data(text):
    """Owner বাদ দিয়ে বাকি সব ডাটা নেয়"""
    lines = text.split('\n')
    data_list = []
    current_url = None
    
    for line in lines:
        if len(data_list) >= 20:
            break
            
        line = line.strip()
        if not line:
            continue
        
        # Owner বাদ
        if line.lower().startswith('owner:'):
            continue
        
        # URL ধরবো
        if line.startswith('http://') or line.startswith('https://'):
            current_url = line
            data_list.append({'type': 'url', 'value': line})
            continue
        
        # ইউজারনেম:পাসওয়ার্ড ফরম্যাট
        if ':' in line:
            parts = line.split(':')
            if len(parts) >= 2:
                username = parts[0].strip()
                password = ':'.join(parts[1:]).strip()
                if username and password:
                    data_list.append({
                        'type': 'credential',
                        'username': username,
                        'password': password,
                        'url': current_url if current_url else ''
                    })
                    current_url = None
                    continue
        
        # অন্য সব কিছু
        if line:
            data_list.append({'type': 'text', 'value': line})
    
    return data_list

# ============ API কল ============
def call_api(url=None):
    try:
        params = {}
        if url:
            params['url'] = url
        
        print(f"📡 কল হচ্ছে: {API_URL}")
        
        response = requests.get(API_URL, params=params, stream=True, timeout=30)
        
        print(f"📊 স্ট্যাটাস: {response.status_code}")
        
        if response.status_code == 200:
            content = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                content += chunk
                if len(content) > 500000:
                    break
            
            print(f"📄 রেসপন্স লেন্থ: {len(content)} অক্ষর")
            
            # JSON চেষ্টা
            try:
                data = json.loads(content)
                if data:
                    results = []
                    if data.get('status') == 'success':
                        items = data.get('data', [])
                        if items:
                            for item in items[:20]:
                                if isinstance(item, str):
                                    # Owner বাদ
                                    if item.lower().startswith('owner:'):
                                        continue
                                    if ':' in item:
                                        parts = item.split(':')
                                        if len(parts) >= 2:
                                            results.append({
                                                'type': 'credential',
                                                'username': parts[0].strip(),
                                                'password': ':'.join(parts[1:]).strip()
                                            })
                                    else:
                                        results.append({'type': 'text', 'value': item})
                            if results:
                                random.shuffle(results)
                                return {'status': 'success', 'data': results[:20]}
                    return {'status': 'success', 'data': results}
            except:
                pass
            
            # টেক্সট পার্স
            all_data = extract_all_data(content)
            if all_data:
                credentials = [d for d in all_data if d.get('type') == 'credential']
                if credentials:
                    random.shuffle(credentials)
                    return {'status': 'success', 'data': credentials[:20]}
                else:
                    return {'status': 'success', 'data': all_data[:20]}
            else:
                return {'status': 'error', 'message': 'কোন ডেটা পাওয়া যায়নি', 'data': []}
        else:
            return {'status': 'error', 'message': f'HTTP {response.status_code}', 'data': []}
            
    except requests.exceptions.Timeout:
        print("❌ টাইমআউট!")
        return {'status': 'error', 'message': 'টাইমআউট! আবার চেষ্টা করুন', 'data': []}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'status': 'error', 'message': str(e), 'data': []}

# ============ অ্যাডমিন ফাংশন ============
def is_admin(user_id):
    return user_id in ADMIN_IDS

def ban_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def unban_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def log_admin_action(admin_id, action, target_user, details=""):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("""INSERT INTO admin_logs (admin_id, action, target_user, details, log_date) 
                 VALUES (?, ?, ?, ?, ?)""",
              (admin_id, action, target_user, details, datetime.datetime.now()))
    conn.commit()
    conn.close()

def refund_coins(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ============ START কমান্ড ============
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    user = get_user(user_id)
    if user and user[8] == 1:
        bot.reply_to(message, f"{EMOJI['error']} আপনি ব্যান!", reply_markup=get_permanent_keyboard())
        return
    
    referrer_id = None
    if message.text:
        text = message.text
        if 'ref_' in text:
            try:
                import re
                match = re.search(r'ref_(\d+)', text)
                if match:
                    referrer_id = int(match.group(1))
                    if referrer_id == user_id:
                        referrer_id = None
            except:
                pass
    
    if not user:
        success, ref_id = add_user(user_id, username, first_name, last_name, referrer_id)
        
        if ref_id:
            try:
                referrer = get_user(ref_id)
                if referrer:
                    new_coins = get_coins(ref_id)
                    bot.send_message(ref_id, 
                        f"{EMOJI['sparkle']} <b>রেফারেল সফল!</b>\n\n"
                        f"👤 {first_name} আপনার লিংক থেকে জয়েন করেছে!\n"
                        f"{EMOJI['coins']} আপনি <b>৩ কয়েন</b> পেয়েছেন!\n"
                        f"{EMOJI['diamond']} বর্তমান কয়েন: {new_coins}",
                        parse_mode='HTML')
            except:
                pass
        
        if not check_channel_membership(user_id):
            welcome_text = f"""
{EMOJI['sparkle']} <b>স্বাগতম {first_name}!</b>

{EMOJI['menu']} <b>{BOT_NAME}</b>

━━━━━━━━━━━━━━━
{EMOJI['success']} অ্যাকাউন্ট তৈরি!
{EMOJI['coins']} বোনাস: ৫ কয়েন

{EMOJI['lock']} <b>চ্যানেল ভেরিফিকেশন প্রয়োজন!</b>

বট ব্যবহার করতে চ্যানেল জয়েন করুন।
            """
            bot.reply_to(message, welcome_text, parse_mode='HTML', 
                        reply_markup=get_permanent_keyboard(user_id))
            send_verification_request(message)
            return
        
        verified, ref_id2 = verify_referral(user_id)
        if verified and ref_id2:
            try:
                referrer = get_user(ref_id2)
                if referrer:
                    new_coins = get_coins(ref_id2)
                    bot.send_message(ref_id2, 
                        f"{EMOJI['success']} <b>রেফারেল সম্পূর্ণ!</b>\n\n"
                        f"👤 {first_name} চ্যানেল জয়েন করেছে!\n"
                        f"{EMOJI['coins']} আপনি আরো <b>৩ কয়েন</b> পেয়েছেন!",
                        parse_mode='HTML')
            except:
                pass
        
        welcome_text = f"""
{EMOJI['sparkle']} <b>স্বাগতম {first_name}!</b>

{EMOJI['menu']} <b>{BOT_NAME}</b>

━━━━━━━━━━━━━━━
{EMOJI['success']} অ্যাকাউন্ট তৈরি!
{EMOJI['coins']} বোনাস: ৫ কয়েন
{EMOJI['success']} চ্যানেল ভেরিফাইড! ✅

<b>কয়েন নিয়ম:</b>
• {EMOJI['search']} প্রতি সার্চে ১ কয়েন
• {EMOJI['profile']} নতুন পায় ৫ কয়েন
• {EMOJI['refer']} রেফারার পায় ৩+৩ কয়েন

{coin_display(user_id)}
        """
        bot.reply_to(message, welcome_text, parse_mode='HTML', 
                    reply_markup=get_permanent_keyboard(user_id))
        return
    
    if not check_channel_membership(user_id):
        send_verification_request(message)
        return
    
    if not is_user_verified(user_id):
        verified, ref_id = verify_referral(user_id)
        if verified and ref_id:
            try:
                referrer = get_user(ref_id)
                if referrer:
                    user_data = get_user(user_id)
                    bot.send_message(ref_id, 
                        f"{EMOJI['success']} <b>রেফারেল সম্পূর্ণ!</b>\n\n"
                        f"👤 {user_data[2]} চ্যানেল জয়েন করেছে!\n"
                        f"{EMOJI['coins']} আপনি <b>৩ কয়েন</b> পেয়েছেন!",
                        parse_mode='HTML')
            except:
                pass
            bot.reply_to(message, 
                f"{EMOJI['success']} চ্যানেল ভেরিফাইড! ✅\n{coin_display(user_id)}",
                parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
            return
    
    bot.reply_to(message, 
        f"{EMOJI['sparkle']} স্বাগতম {first_name}!\n{coin_display(user_id)}",
        parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))

# ============ চ্যানেল সেটিংস কমান্ড ============
@bot.message_handler(commands=['setchannel'])
def set_channel_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, f"{EMOJI['error']} আপনি অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(user_id))
        return
    
    try:
        parts = message.text.split()
        
        if len(parts) < 3:
            current_channel = get_cached_channel()
            help_text = f"""
{EMOJI['channel']} <b>চ্যানেল সেটিংস</b>

বর্তমান চ্যানেল:
📢 ইউজারনেম: {current_channel['username']}
🔗 লিংক: {current_channel['link']}

━━━━━━━━━━━━━━━
<code>/setchannel [ইউজারনেম] [লিংক]</code>
            """
            bot.reply_to(message, help_text, parse_mode='HTML', 
                        reply_markup=get_permanent_keyboard(user_id))
            return
        
        username = parts[1].strip()
        link = parts[2].strip()
        
        if not username.startswith('@'):
            username = '@' + username
        
        if not link.startswith('https://'):
            link = 'https://t.me/' + link.replace('@', '')
        
        if update_channel_settings(username, link):
            log_admin_action(user_id, "CHANNEL_SETTINGS", 0, f"Updated: {username} - {link}")
            channel = get_cached_channel()
            
            success_text = f"""
{EMOJI['success']} <b>চ্যানেল সেটিংস আপডেট করা হয়েছে!</b>

📢 <b>নতুন চ্যানেল ইউজারনেম:</b> {channel['username']}
🔗 <b>নতুন চ্যানেল লিংক:</b> {channel['link']}
            """
            bot.reply_to(message, success_text, parse_mode='HTML', 
                        reply_markup=get_permanent_keyboard(user_id))
        else:
            bot.reply_to(message, f"{EMOJI['error']} চ্যানেল আপডেট করতে ব্যর্থ হয়েছে!", 
                        reply_markup=get_permanent_keyboard(user_id))
                
    except Exception as e:
        bot.reply_to(message, f"{EMOJI['error']} ভুল ফরম্যাট!\n<code>/setchannel [ইউজারনেম] [লিংক]</code>", 
                    parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))

@bot.message_handler(commands=['channelinfo'])
def channel_info_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, f"{EMOJI['error']} আপনি অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(user_id))
        return
    
    channel = get_cached_channel()
    text = f"""
{EMOJI['channel']} <b>চ্যানেল তথ্য</b>

📢 <b>ইউজারনেম:</b> {channel['username']}
🔗 <b>লিংক:</b> {channel['link']}
    """
    bot.reply_to(message, text, parse_mode='HTML', 
                reply_markup=get_permanent_keyboard(user_id))

# ============ টেক্সট হ্যান্ডলার ============
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text and text.startswith('/'):
        return
    
    user = get_user(user_id)
    if not user:
        bot.reply_to(message, f"{EMOJI['warning']} দয়া করে /start দিন প্রথমে।", 
                    reply_markup=get_permanent_keyboard())
        return
    
    if user[8] == 1:
        bot.reply_to(message, f"{EMOJI['error']} আপনি ব্যান!", reply_markup=get_permanent_keyboard())
        return
    
    if not check_channel_membership(user_id):
        send_verification_request(message)
        return
    
    # ===== পার্মানেন্ট বাটন =====
    if text == f"{EMOJI['search']} সার্চ করুন":
        bot.reply_to(message, 
            f"{EMOJI['search']} <b>ইউআরএল দিন</b>\n\n"
            f"যে ইউআরএল থেকে ডেটা আনতে চান সেটি পাঠান।\n\n"
            f"<code>https://www.example.com</code>\n\n"
            f"{coin_display(user_id)}",
            parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    elif text == f"{EMOJI['profile']} প্রোফাইল":
        user = get_user(user_id)
        if user:
            text = f"""
{EMOJI['profile']} <b>প্রোফাইল</b>

👤 নাম: {user[2]} {user[3] or ''}
🆔 আইডি: {user[0]}
{EMOJI['coins']} কয়েন: {user[4]}
{EMOJI['refer']} রেফারেল: {get_referral_count(user_id)}
{EMOJI['search']} সার্চ: {user[9]}
📅 জয়েন: {user[5][:10]}
✅ স্ট্যাটাস: {'ভেরিফাইড ✅' if user[7] else '⏳'}
            """
            bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    elif text == f"{EMOJI['refer']} রেফার করুন":
        link = get_referral_link(user_id)
        channel = get_cached_channel()
        text = f"""
{EMOJI['refer']} <b>রেফারেল সিস্টেম</b>

{EMOJI['link']} <b>আপনার লিংক:</b>
<code>{link}</code>

━━━━━━━━━━━━━━━
প্রতি রেফারে <b>৩+৩ = ৬ কয়েন</b>!

{EMOJI['profile']} <b>মোট রেফারেল:</b> {get_referral_count(user_id)}
{coin_display(user_id)}
        """
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    elif text == f"{EMOJI['latest']} লেটেস্ট":
        if get_coins(user_id) < 1:
            bot.reply_to(message, f"{EMOJI['error']} কয়েন নেই!", reply_markup=get_permanent_keyboard(user_id))
            return
        
        if use_coins(user_id, 1):
            msg = bot.reply_to(message, f"{EMOJI['loading']} ডেটা আনতে হচ্ছে...", parse_mode='HTML')
            
            data = call_api()
            
            if data and data.get('status') == 'success':
                results = data.get('data', [])
                if results:
                    response = f"{EMOJI['latest']} <b>লেটেস্ট ডেটা:</b>\n\n"
                    for i, item in enumerate(results, 1):
                        if isinstance(item, dict):
                            if item.get('type') == 'credential':
                                if item.get('url'):
                                    response += f"{i}. <b>URL:</b> {item['url']}\n"
                                response += f"   <b>Username:</b> {item['username']}\n"
                                response += f"   <b>Password:</b> {item['password']}\n\n"
                            elif item.get('type') == 'url':
                                response += f"{i}. <b>URL:</b> {item['value']}\n\n"
                            else:
                                response += f"{i}. {item.get('value', '')}\n\n"
                        else:
                            response += f"{i}. {item}\n"
                    response += f"\n📊 মোট {len(results)}টি পাওয়া গেছে\n{coin_display(user_id)}"
                else:
                    response = f"{EMOJI['error']} কোনো ডেটা পাওয়া যায়নি!\nকয়েন ফেরত"
                    refund_coins(user_id)
            else:
                error_msg = data.get('message', 'Unknown Error') if data else 'No Response'
                response = f"{EMOJI['error']} ব্যর্থ!\n{error_msg}\nকয়েন ফেরত"
                refund_coins(user_id)
            
            bot.edit_message_text(response, message.chat.id, msg.message_id,
                parse_mode='HTML', reply_markup=get_inline_menu())
        return
    
    elif text == f"{EMOJI['developer']} ডেভেলপার":
        text = f"""
{EMOJI['developer']} <b>ডেভেলপার</b>

বট: {BOT_NAME}
ডেভেলপার: {DEV_NAME}
টেলিগ্রাম: {DEV_TELEGRAM}
গিটহাব: {DEV_GITHUB}
        """
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    elif text == f"{EMOJI['channel']} চ্যানেল":
        channel = get_cached_channel()
        text = f"""
{EMOJI['channel']} <b>চ্যানেল</b>

{EMOJI['link']} {channel['link']}
        """
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    elif text == f"{EMOJI['admin']} অ্যাডমিন প্যানেল":
        if not is_admin(user_id):
            bot.reply_to(message, f"{EMOJI['error']} আপনি অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(user_id))
            return
        text = f"""
{EMOJI['admin']} <b>অ্যাডমিন প্যানেল</b>

👥 মোট ইউজার: {get_user_count()}

━━━━━━━━━━━━━━━
<code>/addcoins [আইডি] [সংখ্যা]</code>
<code>/ban [আইডি]</code>
<code>/unban [আইডি]</code>
<code>/setchannel [ইউজারনেম] [লিংক]</code>
        """
        bot.reply_to(message, text, parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
        return
    
    # ===== ইউআরএল সার্চ =====
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    
    if urls:
        if get_coins(user_id) < 1:
            bot.reply_to(message, f"{EMOJI['error']} কয়েন নেই!", reply_markup=get_permanent_keyboard(user_id))
            return
        
        if use_coins(user_id, 1):
            url = urls[0]
            msg = bot.reply_to(message, f"{EMOJI['loading']} প্রসেসিং...\n<code>{url}</code>", parse_mode='HTML')
            
            data = call_api(url)
            
            if data and data.get('status') == 'success':
                results = data.get('data', [])
                if results:
                    response = f"{EMOJI['success']} সফল!\n\n"
                    for i, item in enumerate(results, 1):
                        if isinstance(item, dict):
                            if item.get('type') == 'credential':
                                if item.get('url'):
                                    response += f"{i}. <b>URL:</b> {item['url']}\n"
                                response += f"   <b>Username:</b> {item['username']}\n"
                                response += f"   <b>Password:</b> {item['password']}\n\n"
                            elif item.get('type') == 'url':
                                response += f"{i}. <b>URL:</b> {item['value']}\n\n"
                            else:
                                response += f"{i}. {item.get('value', '')}\n\n"
                        else:
                            response += f"{i}. {item}\n"
                    response += f"\n📊 মোট {len(results)}টি পাওয়া গেছে\n{coin_display(user_id)}"
                else:
                    response = f"{EMOJI['error']} কোনো ডেটা পাওয়া যায়নি!\nকয়েন ফেরত"
                    refund_coins(user_id)
            else:
                error_msg = data.get('message', 'Unknown Error') if data else 'No Response'
                response = f"{EMOJI['error']} ব্যর্থ!\n{error_msg}\nকয়েন ফেরত"
                refund_coins(user_id)
            
            bot.edit_message_text(response, message.chat.id, msg.message_id,
                parse_mode='HTML', reply_markup=get_inline_menu())
        return
    
    bot.reply_to(message, 
        f"{EMOJI['menu']} <b>মেইন মেনু</b>\n\n{coin_display(user_id)}",
        parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))

# ============ CALLBACK ============
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    if user and user[8] == 1:
        bot.answer_callback_query(call.id, "ব্যান!", show_alert=True)
        return
    
    if call.data == "verify_me":
        if check_channel_membership(user_id):
            verified, ref_id = verify_referral(user_id)
            if verified and ref_id:
                try:
                    user_data = get_user(user_id)
                    referrer = get_user(ref_id)
                    if referrer and user_data:
                        bot.send_message(ref_id, 
                            f"{EMOJI['success']} <b>রেফারেল সম্পূর্ণ!</b>\n\n"
                            f"👤 {user_data[2]} চ্যানেল জয়েন করেছে!\n"
                            f"{EMOJI['coins']} আপনি <b>৩ কয়েন</b> পেয়েছেন!",
                            parse_mode='HTML')
                except:
                    pass
                text = f"{EMOJI['success']} ভেরিফাইড!\n\n{coin_display(user_id)}"
            else:
                text = f"{EMOJI['success']} চ্যানেল ভেরিফাইড! ✅\n\n{coin_display(user_id)}"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                parse_mode='HTML')
            bot.send_message(user_id, "মেইন মেনু:", reply_markup=get_permanent_keyboard(user_id))
        else:
            bot.answer_callback_query(call.id, "চ্যানেল জয়েন করেননি!", show_alert=True)
    
    elif call.data == "new_search":
        bot.answer_callback_query(call.id, "🔍 ইউআরএল দিন!")
        bot.send_message(user_id, 
            f"{EMOJI['search']} <b>ইউআরএল দিন</b>\n\n"
            f"যে ইউআরএল থেকে ডেটা আনতে চান সেটি পাঠান।\n\n"
            f"{coin_display(user_id)}",
            parse_mode='HTML', reply_markup=get_permanent_keyboard(user_id))
    
    elif call.data == "back_main":
        bot.edit_message_text(
            f"{EMOJI['menu']} মেইন মেনু\n\n{coin_display(user_id)}",
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML')
        bot.send_message(user_id, "মেইন মেনু:", reply_markup=get_permanent_keyboard(user_id))

# ============ অ্যাডমিন কমান্ড ============
@bot.message_handler(commands=['addcoins'])
def add_coins_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, f"{EMOJI['error']} অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(message.from_user.id))
        return
    try:
        parts = message.text.split()
        target = int(parts[1])
        amount = int(parts[2])
        if add_coins(target, amount):
            log_admin_action(message.from_user.id, "ADD_COINS", target, f"Added {amount} coins")
            bot.reply_to(message, f"✅ {target} কে {amount} কয়েন দেয়া হয়েছে!", reply_markup=get_permanent_keyboard(message.from_user.id))
    except:
        bot.reply_to(message, "❌ /addcoins [আইডি] [সংখ্যা]", reply_markup=get_permanent_keyboard(message.from_user.id))

@bot.message_handler(commands=['ban'])
def ban_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, f"{EMOJI['error']} অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(message.from_user.id))
        return
    try:
        target = int(message.text.split()[1])
        if ban_user(target):
            log_admin_action(message.from_user.id, "BAN", target, "User banned")
            bot.reply_to(message, f"✅ {target} ব্যান!", reply_markup=get_permanent_keyboard(message.from_user.id))
    except:
        bot.reply_to(message, "❌ /ban [আইডি]", reply_markup=get_permanent_keyboard(message.from_user.id))

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, f"{EMOJI['error']} অ্যাডমিন নন!", reply_markup=get_permanent_keyboard(message.from_user.id))
        return
    try:
        target = int(message.text.split()[1])
        if unban_user(target):
            log_admin_action(message.from_user.id, "UNBAN", target, "User unbanned")
            bot.reply_to(message, f"✅ {target} আনব্যান!", reply_markup=get_permanent_keyboard(message.from_user.id))
    except:
        bot.reply_to(message, "❌ /unban [আইডি]", reply_markup=get_permanent_keyboard(message.from_user.id))

# ============ মেইন ============
def main():
    print(f"\n{'='*50}")
    print(f"🚀 {BOT_NAME}")
    print(f"👨‍💻 {DEV_NAME}")
    print(f"{'='*50}")
    print("✅ বট চালু!")
    print(f"📡 API: {API_URL}")
    print("📌 Owner ট্যাগ বাদ দেওয়া হয়েছে")
    print("📌 বাকি সব ডেটা দেখাবে")
    print(f"{'='*50}\n")
    
    try:
        bot.infinity_polling(timeout=10)
    except Exception as e:
        print(f"❌ {e}")

if __name__ == "__main__":
    main()
