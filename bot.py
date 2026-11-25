import json
from urllib.parse import urlparse, parse_qs
from js import Object, Headers, fetch as js_fetch, Date
from workers import WorkerEntrypoint, Response

# =========================================================
# توابع کمکی
# =========================================================
async def cf_fetch_json(url, method="GET", headers=None, body=None):
    try:
        js_headers = Headers.new()
        if headers:
            for k, v in headers.items():
                js_headers.append(k, str(v))

        opts = Object.fromEntries([
            ["method", method],
            ["headers", js_headers]
        ])

        if body is not None:
            opts.body = json.dumps(body)
            js_headers.append("Content-Type", "application/json")

        res = await js_fetch(url, opts)
        text = await res.text()
        status = res.status

        try:
            return json.loads(text), status
        except Exception:
            return {"raw": text}, status
    except Exception as e:
        print(f"Fetch Error: {e}")
        return {"error": str(e)}, 500


async def save_to_kv(env, key: str, value: str, expiration_ttl=None):
    try:
        if expiration_ttl:
            await env.MY_KV_NAMESPACE.put(key, value, {"expirationTtl": expiration_ttl})
        else:
            await env.MY_KV_NAMESPACE.put(key, value)
    except Exception as e:
        print(f"KV Save Error: {e}")


async def get_from_kv(env, key: str):
    try:
        return await env.MY_KV_NAMESPACE.get(key)
    except Exception as e:
        print(f"KV Get Error: {e}")
        return None


async def get_user_data(env, user_id: str) -> dict:
    raw = await get_from_kv(env, f"user_data_{user_id}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    now_iso = Date.new().toISOString()
    return {
        "user_id": user_id,
        "balance": 0.0,
        "total_deposited": 0.0,
        "total_purchases": 0,
        "invited_by": None,
        "invited_users": [],
        "rewards_earned": 0.0,
        "created_at": now_iso
    }


async def save_user_data(env, user_id: str, data: dict):
    await save_to_kv(env, f"user_data_{user_id}", json.dumps(data))


async def send_telegram_message(env, text: str):
    bot_token = getattr(env, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(env, "YOUR_CHAT_ID", None)
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        await cf_fetch_json(url, method="POST", body=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")


def check_can_withdraw(user_data: dict) -> bool:
    MIN_DEPOSIT = 1.0
    return (user_data.get("balance", 0) >= MIN_DEPOSIT) or \
           (user_data.get("total_purchases", 0) > 0) or \
           (user_data.get("total_deposited", 0) >= MIN_DEPOSIT)


def cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400"
    }


# =========================================================
# Worker اصلی (استایل جدید و استاندارد Cloudflare)
# =========================================================
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        env = self.env
        url = request.url
        method = request.method

        parsed = urlparse(url)
        path = parsed.path or "/"
        query = parse_qs(parsed.query)

        headers = cors_headers()

        # CORS preflight
        if method == "OPTIONS":
            return Response("", headers=headers, status=204)

        try:
            # ---------- Health ----------
            if path == "/" and method == "GET":
                return Response("<h1>Backend is Running!</h1>", headers={"Content-Type": "text/html"})

            # ---------- Gifts (با کش KV) ----------
            if path == "/api/gifts" and method == "GET":
                portals_token = getattr(env, "PORTALS_TOKEN", None)
                if not portals_token:
                    return Response(
                        json.dumps({"status": "error", "message": "PORTALS_TOKEN is not set"}),
                        headers=headers, status=500
                    )

                # سعی می‌کنیم از کش بخونیم
                cache_key = "gifts_cache_v1"
                cached = await get_from_kv(env, cache_key)
                listings = None

                if cached:
                    try:
                        listings = json.loads(cached)
                    except Exception:
                        listings = None

                if listings is None:
                    # اگر کش نبود، از API بکش
                    api_url = "https://portal-market.com/api/v1/marketplace/gifts"
                    req_headers = {
                        "Authorization": f"Bearer {portals_token}",
                        "Accept": "application/json"
                    }
                    res_data, status_code = await cf_fetch_json(api_url, headers=req_headers)

                    if status_code != 200:
                        return Response(
                            json.dumps({
                                "status": "error",
                                "message": f"Upstream error: {status_code}",
                                "details": res_data
                            }),
                            headers=headers, status=status_code
                        )

                    if isinstance(res_data, list):
                        listings = res_data
                    else:
                        listings = res_data.get("data") or res_data.get("gifts") or res_data.get("results") or []

                    # کش برای ۶۰ ثانیه
                    await save_to_kv(env, cache_key, json.dumps(listings), expiration_ttl=60)

                # صفحه‌بندی
                try:
                    offset = int(query.get("offset", ["0"])[0])
                except Exception:
                    offset = 0
                try:
                    limit = int(query.get("limit", ["50"])[0])
                except Exception:
                    limit = 50

                limit = max(1, min(limit, 100))
                offset = max(0, offset)

                paginated = listings[offset:offset + limit]

                result = []
                seen_links = set()

                COLOR_MAP = {
                    "Pine Green": "#017561", "Mystic Pearl": "#E6E0D4", "Silver Blue": "#8A9A9D",
                    "French Blue": "#0072BB", "Ranger Green": "#444C38", "Pacific Cyan": "#1CA9C9",
                    "Seal Brown": "#59260B", "French Violet": "#8806CE", "Onyx Black": "#0F0F0F",
                    "Crimson Red": "#990000", "Gold": "#FFD700"
                }

                for gift in paginated:
                    name = gift.get("name") or gift.get("title") or "Unknown"
                    price = gift.get("price") or gift.get("price_ton") or 0
                    tg_id = gift.get("tg_id") or gift.get("id") or ""
                    clean_name = name.replace(" ", "").replace("'", "")
                    link = f"https://t.me/nft/{clean_name}-{tg_id}" if tg_id else f"https://t.me/nft/{clean_name}"

                    if link in seen_links:
                        continue
                    seen_links.add(link)

                    img_url = gift.get("photo_url") or gift.get("image") or gift.get("image_url") or ""
                    color_name = gift.get("backdrop") or gift.get("background") or ""
                    bg_color = COLOR_MAP.get(color_name, "#1c1c1e")

                    result.append({
                        "name": name,
                        "price": price,
                        "link": link,
                        "image_url": img_url,
                        "bg_color": bg_color
                    })

                return Response(
                    json.dumps({"status": "success", "data": result, "total": len(listings)}),
                    headers=headers
                )

            # ---------- Timer ----------
            if path == "/api/timer" and method == "GET":
                return Response(
                    json.dumps({
                        "status": "success",
                        "end_time": "2026-11-28T23:59:59+00:00",
                        "remaining_seconds": 1000000
                    }),
                    headers=headers
                )

            # ---------- Login ----------
            if path == "/api/webapp/login" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                first_name = data.get("first_name", "")
                start_param = data.get("start_param")

                if not user_id or user_id == "Unknown":
                    return Response(
                        json.dumps({"status": "error", "message": "user_id required"}),
                        headers=headers, status=400
                    )

                user_data = await get_user_data(env, user_id)

                if start_param:
                    referrer_id = start_param.replace("ref_", "") if start_param.startswith("ref_") else start_param
                    if referrer_id.isdigit() and referrer_id != user_id and user_data.get("invited_by") is None:
                        user_data["invited_by"] = referrer_id
                        await save_user_data(env, user_id, user_data)

                        referrer_data = await get_user_data(env, referrer_id)
                        if user_id not in referrer_data.get("invited_users", []):
                            referrer_data.setdefault("invited_users", []).append(user_id)
                            referrer_data["balance"] = referrer_data.get("balance", 0) + 0.5
                            referrer_data["rewards_earned"] = referrer_data.get("rewards_earned", 0) + 0.5
                            await save_user_data(env, referrer_id, referrer_data)

                await send_telegram_message(
                    env,
                    f"🚪 ورود جدید:\n👤 {first_name}\n🆔 {user_id}\n💰 {user_data.get('balance', 0):.2f} TON"
                )

                return Response(
                    json.dumps({
                        "status": "success",
                        "balance": user_data.get("balance", 0),
                        "can_withdraw": check_can_withdraw(user_data),
                        "user_data": user_data
                    }),
                    headers=headers
                )

            # ---------- Balance ----------
            if path == "/api/user/balance" and method == "GET":
                user_id = query.get("user_id", [""])[0]
                data = await get_user_data(env, user_id)
                return Response(
                    json.dumps({
                        "status": "success",
                        "balance": data.get("balance", 0),
                        "can_withdraw": check_can_withdraw(data),
                        "user_data": data
                    }),
                    headers=headers
                )

            # ---------- Record Transaction ----------
            if path == "/api/transaction/record" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                amount = float(data.get("amount", 0))
                tx_type = data.get("type", "deposit")

                if not user_id or amount <= 0:
                    return Response(
                        json.dumps({"status": "error", "message": "Invalid data"}),
                        headers=headers, status=400
                    )

                user_data = await get_user_data(env, user_id)
                if tx_type == "deposit":
                    user_data["balance"] = user_data.get("balance", 0) + amount
                    user_data["total_deposited"] = user_data.get("total_deposited", 0) + amount
                elif tx_type == "purchase":
                    user_data["total_purchases"] = user_data.get("total_purchases", 0) + 1

                await save_user_data(env, user_id, user_data)
                return Response(
                    json.dumps({
                        "status": "success",
                        "balance": user_data.get("balance", 0),
                        "can_withdraw": check_can_withdraw(user_data)
                    }),
                    headers=headers
                )

            # ---------- Withdraw ----------
            if path == "/api/withdraw" and method == "POST":
                data = await request.json()
                user_id = str(data.get("user_id", ""))
                amount = float(data.get("amount", 0))
                user_data = await get_user_data(env, user_id)

                if not check_can_withdraw(user_data):
                    return Response(
                        json.dumps({
                            "status": "error",
                            "code": "NOT_ELIGIBLE",
                            "message": "شرایط برداشت را ندارید."
                        }),
                        headers=headers
                    )

                if amount <= 0 or user_data.get("balance", 0) < amount:
                    return Response(
                        json.dumps({"status": "error", "message": "مبلغ نامعتبر یا موجودی ناکافی"}),
                        headers=headers
                    )

                user_data["balance"] = user_data.get("balance", 0) - amount
                await save_user_data(env, user_id, user_data)

                return Response(
                    json.dumps({
                        "status": "success",
                        "message": "Withdrawal request submitted",
                        "new_balance": user_data["balance"]
                    }),
                    headers=headers
                )

            # ---------- 404 ----------
            return Response(
                json.dumps({"status": "error", "message": "Not Found"}),
                headers=headers, status=404
            )

        except Exception as e:
            print(f"Global Error: {e}")
            return Response(
                json.dumps({"status": "error", "message": str(e)}),
                headers=headers, status=500
            )
