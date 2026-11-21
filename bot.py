import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/gifts")
async def get_gifts_api():
    result = []
    # از API گت‌گمز برای گرفتن لیست کامل استفاده میکنیم
    url = "https://api.getgems.io/public-api/v1/nfts/collections"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                # فیلتر کردن گیفت‌های تلگرام
                for item in data:
                    # چک کردن اینکه آیا این آیتم گیفت تلگرام هست یا نه
                    if item.get('type') == 'gift' or 'gift' in str(item.get('metadata', {}).get('name', '')).lower():
                        metadata = item.get('metadata', {})
                        name = metadata.get('name', 'Unknown Gift')
                        
                        # لینک واقعی از گت‌گمز (اسم کلکسیون)
                        slug = item.get('address', '') 
                        link = f"https://t.me/nft/{slug}" if slug else ""
                        
                        # قیمت (تبدیل از نانو به تون)
                        price_nano = item.get('floor_price', 0)
                        price = float(price_nano) / 1e9 if price_nano else 0
                        
                        # عکس
                        img_url = metadata.get('image', '')
                        
                        # رنگ بک‌گراند
                        bg_color = metadata.get('background_color', '#1c1c1e')
                        if bg_color and not bg_color.startswith('#'):
                            bg_color = f"#{bg_color}"

                        result.append({
                            "name": name,
                            "price": round(price, 4), # گرد کردن قیمت
                            "link": link,
                            "image_url": img_url,
                            "bg_color": bg_color
                        })
        except Exception as e:
            print(f"API Error: {e}")
            return {"status": "error", "message": str(e)}
                
    return {"status": "success", "data": result}

async def main():
    # گرفتن پورت از محیط Railway (پیش‌فرض 8080)
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
