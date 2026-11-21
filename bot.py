import os
import asyncio
import httpx # برای درخواست به API
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from TelegramGifts import TelegramGifts

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# همچنان از این کتابخانه برای گرفتن لیست اولیه استفاده میکنیم
gifts_lib = TelegramGifts(cache_mode="http", asset_mode="lazy")

@dp.message(Command("gifts"))
async def show_gifts(message: types.Message):
    await message.answer("از مینی‌اپ استفاده کن!")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# تابع کمکی برای گرفتن اطلاعات دقیق از TonAPI
async def get_tonapi_details(gift_name: str):
    # لینک API تون برای کلکسیون گیفت‌ها
    url = f"https://tonapi.io/v2/nfts/collections?collection_name={gift_name}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # اگر API چیزی برگردوند، اولین نتیجه رو میگیریم
                if data and len(data) > 0:
                    collection = data[0]
                    metadata = collection.get('metadata', {})
                    
                    # لینک اختصاصی
                    slug = metadata.get('name', '').lower().replace(' ', '-')
                    link = f"https://t.me/nft/{slug}"
                    
                    # گرفتن رنگ پس‌زمینه از متادیتا
                    # رنگ در تون معمولا به صورت عدد یا هگز در فیلدهای مختلف ذخیره میشه
                    bg_color = metadata.get('background_color', '')
                    if bg_color and not str(bg_color).startswith('#'):
                         bg_color = f"#{bg_color}"
                    
                    # عکس با کیفیت
                    image = metadata.get('image', '')
                    
                    return {
                        "link": link,
                        "bg_color": bg_color,
                        "image": image
                    }
        except Exception as e:
            print(f"TonAPI Error for {gift_name}: {e}")
    return None

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        regular_gifts = gifts_lib.get_regular_gifts()
        result = []
        seen = set()

        for gift in regular_gifts:
            try:
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    if name not in seen:
                        seen.add(name)
                        
                        # قیمت از کتابخانه
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        # گرفتن لینک، رنگ و عکس از TonAPI
                        ton_data = await get_tonapi_details(gift.full_name)
                        
                        if ton_data:
                            gift_link = ton_data['link']
                            bg_color = ton_data['bg_color']
                            img_url = ton_data['image']
                        else:
                            # اگر TonAPI جواب نداد، از دیتای خود کتابخانه استفاده میکنیم
                            links = info.get('links', {})
                            img_url = links.get('webp', '') or links.get('png', '')
                            gift_link = ""
                            bg_color = ""

                        result.append({
                            "name": name,
                            "price": price,
                            "link": gift_link,
                            "image_url": img_url,
                            "bg_color": bg_color 
                        })
                        
                        print(f"--- {name} ---")
                        print(f"Link: {gift_link}")
                        print(f"Color: {bg_color}")

            except Exception as e:
                print(f"Error on {gift.full_name}: {e}")
                continue
            
            if len(result) >= 600:
                break

        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": f"خطای کلی: {str(e)}"}

async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
