import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx # برای ارتباط با API کلودفلر نیاز داریم

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔴 توکن خودت رو اینجا بذار
PORTALS_TOKEN = "tma query_id=AAFtFsxzAwAAAG0WzHNu5skJ&user=..."

# 🔴 این دو متغیر رو باید از داشبورد کلودفلر بگیری (توضیح در ادامه)
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "اینجا_اکانت_آیدی_رو_بذار")
CLOUDFLARE_KV_NAMESPACE_ID = os.getenv("CLOUDFLARE_KV_NAMESPACE_ID", "اینجا_آیدی_کی_وی_رو_بذار")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "اینجا_توکن_ای_پی_آی_رو_بذار")

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
# ---------------------------------------------

@app.get("/api/gifts")
async def get_gifts_api(offset: int = 0, limit: int = 50):
    # این بخش همون کدهای قبلی خودت هست و دست نخورده
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

# --- بخش جدید: ساخت دعوت‌نامه ---
@app.get("/api/invite/create")
async def create_invite(user_id: str):
    # ساخت یک کد رندوم ۶ حرفی
    import random, string
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # ذخیره در کلودفلر KV به همراه آیدی کاربری که دعوتش کرده
    success = await save_to_kv(invite_code, f"user_{user_id}")
    
    if success:
        return {"status": "success", "invite_code": invite_code, "link": f"https://t.me/YourBot?start={invite_code}"}
    else:
        return {"status": "error", "message": "خطا در ذخیره دعوت‌نامه"}

# --- بخش جدید: بررسی دعوت‌نامه ---
@app.get("/api/invite/check")
async def check_invite(code: str):
    # خوندن از کلودفلر KV
    value = await get_from_kv(code)
    
    if value:
        return {"status": "success", "valid": True, "invited_by": value}
    else:
        return {"status": "success", "valid": False, "message": "کد دعوت نامعتبر است"}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
