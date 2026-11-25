import os
import json
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from workers import WorkerEntrypoint, Response

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
# API ها (FastAPI Routes)
# =========================================================
@app.get("/api/gifts")
async def get_gifts_api(offset: int = 0, limit: int = 50):
    try:
        url = "https://portal-market.com/api/v1/marketplace/gifts" 
        
        headers = {
            "Authorization": f"Bearer {PORTALS_TOKEN}",
            "Accept": "application/json"
        }
        params = {"offset": offset, "limit": limit, "sort": "price_asc"}
        
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params, timeout=15.0)
            
            if res.status_code == 401:
                return {"status": "error", "message": "توکن پورتالز نامعتبر است (401)."}
            elif res.status_code == 404:
                return {"status": "error", "message": "آدرس API پیدا نشد (404)."}
            elif res.status_code != 200:
                return {"status": "error", "message": f"خطای سرور: {res.status_code}"}
            
            response_data = res.json()
            listings = response_data if isinstance(response_data, list) else response_data.get("data", response_data.get("gifts", []))

        result = []
        seen_links = set()
        
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
            
            result.append({
                "name": name, "price": price, "link": link, "image_url": img_url, "bg_color": bg_color
            })
            
        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": f"خطای داخلی: {str(e)}"}

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
        
        if not user_id or user_id == "Unknown":
            raise HTTPException(status_code=400, detail="user_id required")

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

        return {
            "status": "success",
            "balance": user_data["balance"],
            "can_withdraw": check_can_withdraw(user_data),
            "user_data": user_data
        }
    except Exception as e:
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
        
        if not user_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid data")

        user_data = await get_user_data(user_id)

        if tx_type == "deposit":
            user_data["balance"] += amount
            user_data["total_deposited"] += amount
        elif tx_type == "purchase":
            user_data["total_purchases"] += 1

        await save_user_data(user_id, user_data)
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
            return {"status": "error", "code": "NOT_ELIGIBLE", "message": "شرایط برداشت را ندارید."}

        if amount <= 0 or user_data["balance"] < amount:
            return {"status": "error", "message": "مبلغ نامعتبر یا موجودی ناکافی"}

        user_data["balance"] -= amount
        await save_user_data(user_id, user_data)
        return {"status": "success", "message": "Withdrawal request submitted", "new_balance": user_data["balance"]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# Entrypoint استاندارد و تضمینی برای Cloudflare Workers
# =========================================================
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # تبدیل درخواست Cloudflare به درخواست ASGI برای FastAPI
        from workers import asgi
        asgi_handler = asgi.entrypoint(app)
        return await asgi_handler.fetch(request)
