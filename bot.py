import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# API رسمی Gift Asset که دیتای کامل تلگرام رو داره
GIFT_ASSET_API = "https://api.giftasset.io/v1/gifts"

@app.get("/api/gifts")
async def get_gifts_api():
    result = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # گرفتن لیست کامل گیفت‌ها از API
            res = await client.get(GIFT_ASSET_API)
            if res.status_code == 200:
                data = res.json()
                for gift in data.get('gifts', []):
                    # استخراج اطلاعات دقیق
                    name = gift.get('name', 'Unknown')
                    
                    # لینک واقعی: Gift Asset فیلد slug رو میده
                    slug = gift.get('slug', '')
                    link = f"https://t.me/nft/{slug}" if slug else ""
                    
                    # رنگ بک‌گراند: Gift Asset فیلدهای رنگ رو میده
                    bg_color = gift.get('background_color', '') or gift.get('backdrop', {}).get('center_color', '')
                    if bg_color and isinstance(bg_color, int):
                        bg_color = f"#{bg_color:06x}"
                    
                    # قیمت
                    price = gift.get('price', 0) or gift.get('floor_price', 0)
                    
                    # عکس
                    image = gift.get('image_url', '') or gift.get('image', '')

                    result.append({
                        "name": name,
                        "price": price,
                        "link": link,
                        "image_url": image,
                        "bg_color": bg_color
                    })
        except Exception as e:
            print(f"API Error: {e}")
                
    return {"status": "success", "data": result}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
