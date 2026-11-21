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
    # ... (همون کد قبلی که برای ربات نوشتیم، می‌تونی نگهش داری یا حذفش کنی)
    await message.answer("این دستور از مینی‌اپ استفاده کن!")

# --- بخش دوم: وب‌سرور (API) برای مینی‌اپ ---
app = FastAPI()

# این تنظیمات اجازه می‌ده مینی‌اپت از هر دامنه‌ای به این سرور وصل بشه
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        all_gifts = gifts_lib.get_regular_gifts()
        target_gifts = all_gifts[:600]
        
        result = []
        for gift in target_gifts:
            # اسم فایل عکس رو می‌سازیم
            file_name = gift.full_name.lower().replace(" ", "_")
            # لینک عکس رو می‌سازیم (چون مینی‌اپ نمی‌تونه فایل لوکال رو لود کنه، از یه سرویس CDN تلگرام یا Fragment استفاده می‌کنیم)
            # *نکته: اینجا باید لینک مستقیم عکس رو پیدا کنیم*
            
            result.append({
                "name": gift.full_name,
                "price": gift.floor_price,
                # این خط رو بعداً باید با لینک واقعی عکس جایگزین کنیم
                "image_url": f"https://example.com/{file_name}.webp" 
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- بخش سوم: اجرای همزمان ربات و وب‌سرور ---
async def main():
    # اجرای وب‌سرور در پس‌زمینه
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    
    # ربات و سرور رو با هم اجرا می‌کنیم
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
