import os
import asyncio
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("از مینی‌اپ استفاده کن!")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# این آدرس API غیررسمی فرگمنته که لینک و رنگ و عکس رو با هم میده
FRAGMENT_API = "https://api.fragment-api.com/v1/gifts" 

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        result = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            # گرفتن لیست کامل از فرگمنت
            response = await client.get(FRAGMENT_API)
            
            if response.status_code == 200:
                data = response.json()
                gifts_list = data.get('gifts', [])
                
                for gift in gifts_list:
                    # استخراج اطلاعات
                    name = gift.get('name', 'Unknown Gift')
                    price = gift.get('price', 0)
                    
                    # لینک اختصاصی (مثلا https://t.me/nft/KhabibsPapakha)
                    slug = gift.get('slug', '')
                    link = f"https://t.me/nft/{slug}" if slug else ""
                    
                    # عکس
                    image = gift.get('image_url', '')
                    
                    # رنگ بک‌گراند (اگر API بده)
                    bg_color = gift.get('background_color', '') or gift.get('bg_color', '')
                    if bg_color and not bg_color.startswith('#'):
                        bg_color = f"#{bg_color}"

                    result.append({
                        "name": name,
                        "price": price,
                        "link": link,
                        "image_url": image,
                        "bg_color": bg_color 
                    })
                    
        return {"status": "success", "data": result}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": f"خطای کلی: {str(e)}"}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
