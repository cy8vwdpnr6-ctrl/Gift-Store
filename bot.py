import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aportalsmp
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=[""], allow_methods=[""], allow_headers=["*"])
🔴 توکنی که از مرورگر کپی کردی رو اینجا بذار (دقیقا بین دابل کوتیشن)
PORTALS_TOKEN = "tma query_id=AAFtFsxzAwAAAG0WzHNu5skJ&user=%7B%22id%22%3A8385205869%2C%22first_name%22%3A%22-%20Raeef%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22sisixeni%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FTGRc8X2zuCX0Cfg7BKG-WEIo4oxRnV1fZ-ZKWBL3nHD3kTtgmdF6Ta3RaXExNVQC.svg%22%7D&auth_date=1795281433&signature=BQxx9DjeTzfEgIUduOVfiZj_MkJFums2Jq6-75GKKoa7q_BB4h-hzUeyetyfnJzQAR36CDzMqzrvOqXc1bHqCQ&hash=5e50f9042b3535860305073b1a8567681448ea32d3f440bf0dd3aa588b846cb5"
@app.get("/api/gifts")
async def get_gifts_api():
result = []
try:
# گرفتن دیتا از مارکت‌پلیس پورتالز
# ما اینجا دنبال همه گیفت‌ها میگردیم
listings = await aportalsmp.search(
authData=PORTALS_TOKEN,
gift_name="",
limit=100
)
    for gift in listings:
        # استخراج اطلاعات دقیق
        name = getattr(gift, 'name', 'Unknown Gift')
        price = getattr(gift, 'price', 0)
        
        # لینک واقعی با سریال نامبر
        serial = getattr(gift, 'serial', '')
        slug = name.replace(" ", "").replace("'", "")
        link = f"https://t.me/nft/{slug}-{serial}" if serial else f"https://t.me/nft/{slug}"
        
        # عکس
        img_url = getattr(gift, 'image_url', '')
        
        # رنگ بک‌گراند (پورتالز دقیق میده)
        bg_color = getattr(gift, 'backdrop', '') or "#1c1c1e"
        
        result.append({
            "name": name,
            "price": round(price, 4),
            "link": link,
            "image_url": img_url,
            "bg_color": bg_color
        })
        
    return {"status": "success", "data": result}
    
except Exception as e:
    print(f"Error: {e}")
    return {"status": "error", "message": str(e)}
async def main():
port = int(os.getenv("PORT", 8080))
config = uvicorn.Config(app, host="0.0.0.0", port=port)
server = uvicorn.Server(config)
await server.serve()
if name == "main":
asyncio.run(main())
