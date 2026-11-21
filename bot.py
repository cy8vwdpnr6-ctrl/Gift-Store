import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔴 توکن خودت
PORTALS_TOKEN = "tma query_id=AAFtFsxzAwAAAG0WzHNu5skJ&user=%7B%22id%22%3A8385205869%2C%22first_name%22%3A%22-%20Raeef%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22sisixeni%22%2C%22language_code%22%3A%22en%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FTGRc8X2zuCX0Cfg7BKG-WEIo4oxRnV1fZ-ZKWBL3nHD3kTtgmdF6Ta3RaXExNVQC.svg%22%7D&auth_date=1795281433&signature=BQxx9DjeTzfEgIUduOVfiZj_MkJFums2Jq6-75GKKoa7q_BB4h-hzUeyetyfnJzQAR36CDzMqzrvOqXc1bHqCQ&hash=5e50f9042b3535860305073b1a8567681448ea32d3f440bf0dd3aa588b846cb5"

# 🎨 نقشه تبدیل اسم رنگ‌های تلگرام به کد Hex
COLOR_MAP = {
    "Pine Green": "#017561",
    "Mystic Pearl": "#E6E0D4",
    "Silver Blue": "#8A9A9D",
    "French Blue": "#0072BB",
    "Ranger Green": "#444C38",
    "Pacific Cyan": "#1CA9C9",
    "Seal Brown": "#59260B",
    "French Violet": "#8806CE",
    "Onyx Black": "#0F0F0F",
    "Crimson Red": "#990000",
    "Gold": "#FFD700"
}

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        import aportalsmp
        
        listings = await aportalsmp.search(
            authData=PORTALS_TOKEN,
            gift_name="",
            limit=50,
            sort="price_asc"
        )
        
        result = []
        for gift in listings:
            name = getattr(gift, 'name', 'Unknown')
            price = getattr(gift, 'price', 0)
            
            tg_id = getattr(gift, 'tg_id', '')
            clean_name = name.replace(" ", "").replace("'", "")
            link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else ""
            
            img_url = getattr(gift, 'photo_url', '')
            
            # تبدیل اسم رنگ به کد Hex
            color_name = getattr(gift, 'backdrop', '')
            bg_color = COLOR_MAP.get(color_name, "#1c1c1e") # اگه پیدا نشد، پیش‌فرض
            
            result.append({
                "name": name,
                "price": price,
                "link": link,
                "image_url": img_url,
                "bg_color": bg_color
            })
            
        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": f"خطا: {str(e)}"}

async def main():
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
