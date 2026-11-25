import os
import json
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from workers import asgi

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORTALS_TOKEN = os.getenv("PORTALS_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YOUR_CHAT_ID = os.getenv("YOUR_CHAT_ID", "")

BOT_USERNAME = "NftsHubbot" 
INVITE_REWARD = 0.5           
MIN_DEPOSIT_FOR_WITHDRAW = 1.0  

COLOR_MAP = {
    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000", "Gold": "#FFD700"
}

# =========================================================
# Cloudflare KV Helper
# =========================================================
async def save_to_kv(key: str, value: str):
    try:
        from js import MY_KV_NAMESPACE
        await MY_KV_NAMESPACE.put(key, value)
        return True
    except Exception as e:
        print(f"KV Save Error: {e}")
        return False

async def get_from_kv(key: str):
    try:
        from js import MY_KV_NAMESPACE
        val = await MY_KV_NAMESPACE.get(key)
        return val
    except Exception as e:
        print(f"KV Get Error: {e}")
        return None

# =========================================================
# ذخیره و بازیابی اطلاعات کاربر
# =========================================================
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

# =========================================================
# تلگرام
# =========================================================
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

FIXED_END_TIME = "2026-11-28T23:59:59+00:00"

# =========================================================
# سرو کردن فرانت‌اند (index.html)
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found!</h1>"

# =========================================================
# API ها
# =========================================================
@app.get("/api/gifts")
async def get_gifts_api(offset: int = 0, limit: int = 50):
    try:
        # 🌟 تغییر اصلی: آدرس دقیق و صحیح API پورتالز 🌟
        url = "https://portal-market.com/api/v1/marketplace/gifts" 
        
        headers = {
            "Authorization": f"Bearer {PORTALS_TOKEN}",
            "Accept": "application/json"
        }
        params = {
            "offset": offset, 
            "limit": limit, 
            "sort": "price_asc"
        }
        
        async with httpx.AsyncClient() as client:
            # ارسال درخواست با تنظیمات جدید
            res = await client.get(url, headers=headers, params=params, timeout=15.0)
            
            # بررسی دقیق خطاها
            if res.status_code == 401:
                return {"status": "error", "message": "توکن پورتالز نامعتبر است (401). لطفاً PORTALS_TOKEN را بررسی کنید."}
            elif res.status_code == 404:
                return {"status": "error", "message": "آدرس API پیدا نشد (404). مسیر را بررسی کنید."}
            elif res.status_code != 200:
                return {"status": "error", "message": f"خطای سرور پورتالز: {res.status_code} - {res.text}"}
            
            # استخراج دیتا (ممکن است ساختار پاسخ کمی متفاوت باشد)
            response_data = res.json()
            # اگر پاسخ مستقیماً لیست نبود، داخل کلید data یا gifts می‌گردیم
            listings = response_data if isinstance(response_data, list) else response_data.get("data", response_data.get("gifts", []))

        result = []
        seen_links = set()
        
        for gift in listings:
            # استخراج فیلدها با مقادیر پیش‌فرض ایمن
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
            
            result.append({
                "name": name, 
                "price": price, 
                "link": link, 
                "image_url": img_url, 
                "bg_color": bg_color
            })
            
        return {"status": "success", "data": result}
        
    except httpx.TimeoutException:
        return {"status": "error", "message": "زمان درخواست به پورتالز به پایان رسید (Timeout)."}
    except Exception as e:
        return {"status": "error", "message": f"خطای داخلی سرور: {str(e)}"}

@app.get("/api/timer")
async def get_timer():
    end_time = datetime.fromisoformat(FIXED_END_TIME)
    now = datetime.now(timezone.utc)
    remaining = max(0, (end_time - now).total_seconds())
    return {"status": "success", "end_time": FIXED_END_TIME, "remaining_seconds": int(remaining)}

@app.post("/api/webapp/login")
async def webapp_login(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        username = data.get("username", "No Username")
        first_name = data.get("first_name", "")
        start_param = data.get("start_param", None)
        platform = data.get("platform", "unknown")
        version = data.get("version", "unknown")
        client_ip_from_frontend = data.get("ip_address", "Unknown")

        if not user_id or user_id == "Unknown":
            raise HTTPException(status_code=400, detail="user_id required")

        client_ip = request.headers.get("cf-connecting-ip", client_ip_from_frontend)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        user_data = await get_user_data(user_id)

        if start_param and start_param.startswith("ref_"):
            referrer_id = start_param.replace("ref_", "")
            if referrer_id != user_id and user_data["invited_by"] is None:
                user_data["invited_by"] = referrer_id
                await save_user_data(user_id, user_data)
                referrer_data = await get_user_data(referrer_id)
                if user_id not in referrer_data["invited_users"]:
                    referrer_data["invited_users"].append(user_id)
                    referrer_data["balance"] += INVITE_REWARD
                    referrer_data["rewards_earned"] += INVITE_REWARD
                    await save_user_data(referrer_id, referrer_data)
        elif start_param and start_param.isdigit() and start_param != user_id:
            referrer_id = start_param
            if user_data["invited_by"] is None:
                user_data["invited_by"] = referrer_id
                await save_user_data(user_id, user_data)
                referrer_data = await get_user_data(referrer_id)
                if user_id not in referrer_data["invited_users"]:
                    referrer_data["invited_users"].append(user_id)
                    referrer_data["balance"] += INVITE_REWARD
                    referrer_data["rewards_earned"] += INVITE_REWARD
                    await save_user_data(referrer_id, referrer_data)

        message_text = (
            f"🚪 <b>ورود جدید به مینی‌اپ</b>\n\n"
            f"👤 <b>اسم تلگرام:</b> {first_name}\n"
            f"📱 <b>نام کاربری:</b> @{username}\n"
            f"🆔 <b>آیدی عددی:</b> <code>{user_id}</code>\n"
            f"🌐 <b>آی‌پی:</b> <code>{client_ip}</code>\n"
            f"📟 <b>دستگاه:</b> {platform} (نسخه {version})\n"
            f"💰 <b>موجودی فعلی:</b> <b>{user_data['balance']:.2f} TON</b>\n"
            f"🔗 <b>لینک ورودی:</b> {start_param or 'ندارد'}\n"
            f"⏰ <b>زمان ورود:</b> {now_str}"
        )
        await send_telegram_message(message_text)

        return {
            "status": "success",
            "balance": user_data["balance"],
            "can_withdraw": check_can_withdraw(user_data),
            "user_data": user_data
        }
    except Exception as e:
        print(f"Login Error: {e}")
        return {"status": "error", "message": str(e)}

def check_can_withdraw(user_data: dict) -> bool:
    return (user_data["balance"] >= MIN_DEPOSIT_FOR_WITHDRAW) or (user_data["total_purchases"] > 0) or (user_data["total_deposited"] >= MIN_DEPOSIT_FOR_WITHDRAW)

@app.get("/api/user/balance")
async def get_balance(user_id: str):
    data = await get_user_data(user_id)
    return {"status": "success", "balance": data["balance"], "can_withdraw": check_can_withdraw(data), "user_data": data}

@app.post("/api/transaction/record")
async def record_transaction(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        amount = float(data.get("amount", 0))
        tx_type = data.get("type", "deposit")
        description = data.get("description", "")
        
        if not user_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid data")

        user_data = await get_user_data(user_id)

        if tx_type == "deposit":
            user_data["balance"] += amount
            user_data["total_deposited"] += amount
        elif tx_type == "purchase":
            user_data["total_purchases"] += 1

        await save_user_data(user_id, user_data)

        await send_telegram_message(
            f"💸 <b>تراکنش جدید</b>\n\n"
            f"👤 کاربر: <code>{user_id}</code>\n"
            f"📊 نوع: {tx_type}\n"
            f"💵 مبلغ: {amount} TON\n"
            f"📝 توضیح: {description}\n"
            f"💰 موجودی جدید: <b>{user_data['balance']:.2f} TON</b>"
        )

        return {"status": "success", "balance": user_data["balance"], "can_withdraw": check_can_withdraw(user_data)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/withdraw")
async def request_withdraw(request: Request):
    try:
        data = await request.json()
        user_id = str(data.get("user_id", ""))
        amount = float(data.get("amount", 0))
        wallet_address = data.get("wallet_address", "")

        user_data = await get_user_data(user_id)

        if not check_can_withdraw(user_data):
            return {"status": "error", "code": "NOT_ELIGIBLE", "message": "To withdraw, you must have at least one TON in your balance or have made at least one purchase."}

        if amount <= 0:
            return {"status": "error", "message": "Invalid amount"}
        if user_data["balance"] < amount:
            return {"status": "error", "message": "Insufficient balance"}

        user_data["balance"] -= amount
        await save_user_data(user_id, user_data)

        await send_telegram_message(
            f"🔴 <b>درخواست برداشت</b>\n\n"
            f"👤 کاربر: <code>{user_id}</code>\n"
            f"💵 مبلغ: {amount} TON\n"
            f"👛 کیف پول: <code>{wallet_address}</code>"
        )

        return {"status": "success", "message": "Withdrawal request submitted", "new_balance": user_data["balance"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# Entrypoint برای Cloudflare Workers
# =========================================================
Default = asgi.entrypoint(app)
