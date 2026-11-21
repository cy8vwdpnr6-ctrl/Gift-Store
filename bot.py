import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import random
import string

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔴 توکن پورتال خودت (همون که داشتی)
PORTALS_TOKEN = "tma query_id=AAFtFsxzAwAAAG0WzHNu5skJ&user=%7B%22id%22%3A8385205869..."

# 🔴 متغیرهای کلودفلر (همون‌هایی که تو تنظیمات Railway گذاشتی)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_KV_NAMESPACE_ID = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# 🔴 (اختیاری) اگر می‌خوای اطلاعات کاربر به تلگرام خودت هم ارسال بشه، این دو خط رو پر کن
TELEGRAM_BOT_TOKEN = os.getenv("9260686530:AAH8qKecqQ0uPtfYmRpI3LpNJUPvq_trrGs", "") # توکن رباتی که میخوای پیام برات بفرسته
YOUR_CHAT_ID = os.getenv("6973598061", "") # آیدی عددی خودت در تلگرام

COLOR_MAP = {
    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000", "Gold": "#FFD700"
}

# --- توابع کمکی برای کار با Cloudflare KV ---
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

# --- تابع ارسال پیام به تلگرام ---
async def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not YOUR_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": YOUR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)


# ==========================================
# ۱. بخش لیست هدایا (کد قبلی خودت)
# ==========================================
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

# ==========================================
# ۲. بخش دعوت‌نامه‌ها (کد قبلی خودت)
# ==========================================
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

# ==========================================
# ۳. بخش جدید: دریافت اطلاعات کاربر مینی‌اپ
# ==========================================
@app.post("/api/webapp/login")
async def webapp_login(request: Request):
    try:
        data = await request.json()
        
        # دریافت اطلاعاتی که فرانت‌اند (مینی اپ) به این API می‌فرسته
        user_id = data.get("user_id", "Unknown")
        username = data.get("username", "No Username")
        first_name = data.get("first_name", "")
        
        # دریافت IP کاربر
        client_ip = request.client.host
        
        # ذخیره اطلاعات در کلودفلر KV
        user_data = f"name: {first_name} | username: @{username} | ip: {client_ip}"
        await save_to_kv(f"user_info_{user_id}", user_data)
        
        # (اختیاری) ارسال پیام به تلگرام خودت
        message_text = (
            f"👤 <b>کاربر جدید در مینی‌اپ:</b>\n\n"
            f"🆔 <b>آیدی:</b> <code>{user_id}</code>\n"
            f"🔗 <b>یوزرنیم:</b> @{username}\n"
            f"📝 <b>نام:</b> {first_name}\n"
            f"🌐 <b>IP:</b> <code>{client_ip}</code>"
        )
        await send_telegram_message(message_text)
        
        return {"status": "success", "message": "اطلاعات با موفقیت دریافت شد"}
        
    except Exception as e:
        return {"status": "error", "message": f"خطا در دریافت اطلاعات: {str(e)}"}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
