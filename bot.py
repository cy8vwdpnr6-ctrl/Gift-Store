import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 🔴 توکن خودت
PORTALS_TOKEN = "tma ..." 

@app.get("/api/gifts")
async def get_gifts_api():
    try:
        import aportalsmp
        
        # 🔴 فعلا پروکسی رو برداشتیم
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
            bg_color = getattr(gift, 'backdrop', '') or "#1c1c1e"
            
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
