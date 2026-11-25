import os
import json
import httpx
from datetime import datetime, timezone
from workers import WorkerEntrypoint, Response
from js import MY_KV_NAMESPACE

# =========================================================
# تنظیمات اولیه
# =========================================================
PORTALS_TOKEN = os.getenv("PORTALS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID", "")

BOT_USERNAME = "NftsHubbot" 
INVITE_REWARD = 0.5           
MIN_DEPOSIT_FOR_WITHDRAW = 1.0  
FIXED_END_TIME = "2026-11-28T23:59:59+00:00"

COLOR_MAP = {
    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000", "Gold": "#FFD700"
}

# =========================================================
# توابع کمکی دیتابیس (KV)
# =========================================================
async def save_to_kv(key: str, value: str):
    try:
        await MY_KV_NAMESPACE.put(key, value)
    except Exception as e:
        print(f"KV Save Error: {e}")

async def get_from_kv(key: str):
    try:
        return await MY_KV_NAMESPACE.get(key)
    except Exception as e:
        print(f"KV Get Error: {e}")
        return None

async def get_user_data(user_id: str) -> dict:
    raw = await get_from_kv(f"user_data_{user_id}")
    if raw:
        try:
            return json.loads(raw)
        except:
            pass
    return {
        "user_id": user_id, "balance": 0.0, "total_deposited": 0.0,
        "total_purchases": 0, "invited_by": None, "invited_users": [],
        "rewards_earned": 0.0, "created_at": datetime.now(timezone.utc).isoformat()
    }

async def save_user_data(user_id: str, data: dict):
    await save_to_kv(f"user_data_{user_id}", json.dumps(data))

async def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not YOUR_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")

def check_can_withdraw(user_data: dict) -> bool:
    return (user_data["balance"] >= MIN_DEPOSIT_FOR_WITHDRAW) or \
           (user_data["total_purchases"] > 0) or \
           (user_data["total_deposited"] >= MIN_DEPOSIT_FOR_WITHDRAW)

# =========================================================
# روتینگ و منطق اصلی (بدون نیاز به FastAPI)
# =========================================================
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        method = request.method
        
        # استخراج مسیر (Path) از URL
        path = url.split("?")[0].replace("https://", "").replace("http://", "")
        path = "/" + path.split("/", 1)[1] if "/" in path else "/"
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        
        # مدیریت درخواست‌های CORS
        if method == "OPTIONS":
            return Response("", headers={
                **headers, 
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS", 
                "Access-Control-Allow-Headers": "*"
            })

        try:
            # --- 1. صفحه اصلی ---
            if path == "/" and method == "GET":
                return Response("<h1>Backend is Running!</h1>", headers={"Content-Type": "text/html"})

            # --- 2. دریافت گیفت‌ها ---
            elif path == "/api/gifts" and method == "GET":
                api_url = "https://portal-market.com/api/v1/marketplace/gifts"
                req_headers = {"Authorization": f"Bearer {PORTALS_TOKEN}", "Accept": "application/json"}
                async with httpx.AsyncClient() as client:
                    res = await client.get(api_url, headers=req_headers, params={"offset": 0, "limit": 50, "sort": "price_asc"}, timeout=15.0)
                    if res.status_code != 200:
                        return Response(json.dumps({"status": "error", "message": f"Server error: {res.status_code}"}), headers=headers, status=res.status_code)
                    
                    response_data = res.json()
                    listings = response_data if isinstance(response_data, list) else response_data.get("data", response_data.get("gifts", []))
                
                result, seen_links = [], set()
                for gift in listings:
                    name = gift.get('name', gift.get('title', 'Unknown'))
                    price = gift.get('price', gift.get('price_ton', 0))
                    tg_id = gift.get('tg_id', gift.get('id', ''))
                    clean_name = name.replace(" ", "").replace("'", "")
                    link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else f"https://t.me/nft/{clean_name}"
                    
                    if link in seen_links: continue
                    seen_links.add(link)
                    
                    img_url = gift.get('photo_url', gift.get('image', '')) or ""
                    color_name = gift.get('backdrop', gift.get('background', ''))
                    bg_color = COLOR_MAP.get(color_name, "#1c1c1e")
                    
                    result.append({"name": name, "price": price, "link": link, "image_url": img_url, "bg_color": bg_color})
                return Response(json.dumps({"status": "success", "data": result}), headers=headers)

            # --- 3. تایمر ---
            elif path == "/api/timer" and method == "GET":
                end_time = datetime.fromisoformat(FIXED_END_TIME)
                now = datetime.now(timezone.utc)
                remaining = max(0, (end_time - now).total_seconds())
                return Response(json.dumps({"status": "success", "end_time": FIXED_END_TIME, "remaining_seconds": int(remaining)}), headers=headers)

            # --- 4. ورود مینی‌اپ ---
            elif path == "/api/webapp/login" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                username = data.get("username", "No Username")
                first_name = data.get("first_name", "")
                start_param = data.get("start_param", None)
                
                if not user_id or user_id == "Unknown":
                    return Response(json.dumps({"status": "error", "message": "user_id required"}), headers=headers, status=400)

                user_data = await get_user_data(user_id)

                if start_param:
                    referrer_id = start_param.replace("ref_", "") if start_param.startswith("ref_") else start_param
                    if referrer_id.isdigit() and referrer_id != user_id and user_data.get("invited_by") is None:
                        user_data["invited_by"] = referrer_id
                        await save_user_data(user_id, user_data)
                        referrer_data = await get_user_data(referrer_id)
                        if user_id not in referrer_data["invited_users"]:
                            referrer_data["invited_users"].append(user_id)
                            referrer_data["balance"] += INVITE_REWARD
                            referrer_data["rewards_earned"] += INVITE_REWARD
                            await save_user_data(referrer_id, referrer_data)

                await send_telegram_message(f"🚪 ورود جدید:\n👤 {first_name}\n🆔 {user_id}\n💰 {user_data['balance']:.2f} TON")
                return Response(json.dumps({"status": "success", "balance": user_data["balance"], "can_withdraw": check_can_withdraw(user_data), "user_data": user_data}), headers=headers)

            # --- 5. موجودی کاربر ---
            elif path == "/api/user/balance" and method == "GET":
                query = url.split("?")[1] if "?" in url else ""
                user_id = ""
                for param in query.split("&"):
                    if param.startswith("user_id="): user_id = param.split("=")[1]
                
                data = await get_user_data(user_id)
                return Response(json.dumps({"status": "success", "balance": data["balance"], "can_withdraw": check_can_withdraw(data), "user_data": data}), headers=headers)

            # --- 6. ثبت تراکنش ---
            elif path == "/api/transaction/record" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                amount = float(data.get("amount", 0))
                tx_type = data.get("type", "deposit")
                
                if not user_id or amount <= 0:
                    return Response(json.dumps({"status": "error", "message": "Invalid data"}), headers=headers, status=400)

                user_data = await get_user_data(user_id)
                if tx_type == "deposit":
                    user_data["balance"] += amount
                    user_data["total_deposited"] += amount
                elif tx_type == "purchase":
                    user_data["total_purchases"] += 1

                await save_user_data(user_id, user_data)
                return Response(json.dumps({"status": "success", "balance": user_data["balance"], "can_withdraw": check_can_withdraw(user_data)}), headers=headers)

            # --- 7. درخواست برداشت ---
            elif path == "/api/withdraw" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                amount = float(data.get("amount", 0))
                user_data = await get_user_data(user_id)

                if not check_can_withdraw(user_data):
                    return Response(json.dumps({"status": "error", "code": "NOT_ELIGIBLE", "message": "شرایط برداشت را ندارید."}), headers=headers)
                if amount <= 0 or user_data["balance"] < amount:
                    return Response(json.dumps({"status": "error", "message": "مبلغ نامعتبر یا موجودی ناکافی"}), headers=headers)

                user_data["balance"] -= amount
                await save_user_data(user_id, user_data)
                return Response(json.dumps({"status": "success", "message": "Withdrawal request submitted", "new_balance": user_data["balance"]}), headers=headers)

            # --- 8. خطای 404 ---
            else:
                return Response(json.dumps({"status": "error", "message": "Not Found"}), headers=headers, status=404)
                
        except Exception as e:
            print(f"Global Error: {e}")
            return Response(json.dumps({"status": "error", "message": str(e)}), headers=headers, status=500)
