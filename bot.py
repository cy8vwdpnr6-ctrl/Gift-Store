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

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("این دستور از مینی‌اپ استفاده کن!")

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
        # لیست تمام گیفت‌های معمولی را می‌گیریم تا اسم‌ها را داشته باشیم
        all_regular = gifts_lib.get_regular_gifts()
        
        result = []
        seen_names = set() # برای جلوگیری از تکرار

        for gift in all_regular:
            try:
                # حالا نسخه آپگرید شده (NFT) همان گیفت را جستجو می‌کنیم
                upgraded = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if upgraded:
                    # استخراج نام و قیمت از دیکشنری برگشتی
                    name = upgraded.get('full_name', gift.full_name)
                    
                    # قیمت را از دیکشنری prices می‌خوانیم
                    prices = upgraded.get('prices', {})
                    price = prices.get('tgmrkt_price_ton', 0)
                    
                    if name not in seen_names:
                        seen_names.add(name)
                        result.append({
                            "name": name,
                            "price": price,
                            "image_url": "" 
                        })
            except Exception:
                # اگر برای یک گیفت خاص خطایی رخ داد، از آن رد شو
                continue
            
            # سقف ۶۰۰ تا برای اینکه سرور کند نشود
            if len(result) >= 600:
                break
                
        if not result:
            return {"status": "error", "message": "No upgraded gifts found. The library might be returning an empty list."}
            
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
