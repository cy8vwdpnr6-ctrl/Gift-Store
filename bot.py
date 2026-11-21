import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from TelegramGifts import TelegramGifts

# اضافه کردن کتابخانه‌های وب‌سرور
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
gifts_lib = TelegramGifts()

# --- بخش اول: کد ربات تلگرام ---
@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("این دستور از مینی‌اپ استفاده کن!")

# --- بخش دوم: وب‌سرور (API) برای مینی‌اپ ---
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
        # 🔴 اینجا تغییر مهم است: استفاده از لیست کالکتیبل‌ها به جای معمولی‌ها
        # این متد معمولاً لیست مدل‌های آپگرید شده (NFT) را برمی‌گرداند
        all_gifts = gifts_lib.get_upgraded_gifts() 
        
        # اگر کتابخانه متد بالا را نداشت، از این استفاده کن:
        # all_gifts = gifts_lib.get_regular_gifts() 
        
        target_gifts = all_gifts[:600]
        
        result = []
        for gift in target_gifts:
            # برای گیفت‌های کالکتیبل، قیمت معمولاً به TON است
            # اگر فیلد قیمت متفاوت بود، با توجه به داکیومنت کتابخانه اصلاحش کن
            price = getattr(gift, 'floor_price', 0)
            
            result.append({
                "name": gift.full_name,
                "price": price,
                # لینک عکس رو فعلاً خالی می‌ذاریم تا فرانت‌اند از آواتار استفاده کنه
                "image_url": "" 
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- بخش سوم: اجرای همزمان ربات و وب‌سرور ---
async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
