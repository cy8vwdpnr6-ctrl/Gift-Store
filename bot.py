import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from TelegramGifts import TelegramGifts

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
gifts_lib = TelegramGifts()

# --- بخش ربات ---
@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("این دستور از مینی‌اپ استفاده کن!")

# --- بخش API برای مینی‌اپ ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        # لیست تمام گیفت‌های معمولی رو می‌گیریم
        all_regular = gifts_lib.get_regular_gifts()
        
        result = []
        for gift in all_regular:
            # جستجوی نسخه آپگرید شده (NFT) با استفاده از نام گیفت
            upgraded = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
            
            if upgraded:
                # استخراج قیمت از دیکشنری prices
                prices = upgraded.get('prices', {})
                price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                
                result.append({
                    "name": upgraded.get('full_name', gift.full_name),
                    "price": price,
                    "image_url": "" 
                })
            
            # سقف ۶۰۰ تا برای اینکه سرور کند نشه
            if len(result) >= 600:
                break
                
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- اجرای همزمان ربات و وب‌سرور ---
async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
