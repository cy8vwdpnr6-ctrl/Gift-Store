import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from TelegramGifts import TelegramGifts

# توکن رو از متغیرهای محیطی Railway می‌خونیم (امنیت بالا)
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
gifts_lib = TelegramGifts()

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("⏳ در حال دریافت لیست گیفت‌ها، لطفاً صبر کنید...")
    
    try:
        all_gifts = gifts_lib.get_regular_gifts()
        target_gifts = all_gifts[:600]  # ۶۰۰ تای اول
        
        # فقط ۱۰ تای اول رو می‌فرستیم که ربات بلاک نشه
        for gift in target_gifts[:10]:
            try:
                # تبدیل اسم به فرمت مناسب برای دانلود عکس
                file_name = gift.full_name.lower().replace(" ", "_")
                img_path = gifts_lib.download_image(file_name, ext="webp")
                
                photo = FSInputFile(img_path)
                caption = f"🎁 {gift.full_name}\n💰 قیمت: {gift.floor_price} TON"
                await message.answer_photo(photo=photo, caption=caption)
            except Exception as e:
                await message.answer(f"⚠️ خطا در دریافت {gift.full_name}: {e}")
                
    except Exception as e:
        await message.answer(f"❌ خطای کلی: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
