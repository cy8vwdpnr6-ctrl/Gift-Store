# ... (کدهای قبلی)

        for gift in regular_gifts:
            try:
                info = gifts_lib.get_gift(gift.full_name, gift_type="upgraded")
                
                if info:
                    name = info.get('full_name', gift.full_name)
                    if name not in seen:
                        seen.add(name)
                        
                        prices = info.get('prices', {})
                        price = prices.get('tgmrkt_price_ton') or prices.get('fragment_price_ton') or 0
                        
                        # 🔴 استخراج لینک (slug)
                        slug = info.get('slug', '')
                        if not slug:
                            slug = name.lower().replace(" ", "").replace("'", "")
                        gift_link = f"https://t.me/nft/{slug}"
                        
                        # 🔴 استخراج عکس
                        links = info.get('links', {})
                        img_url = links.get('webp', '') or links.get('png', '') or links.get('jpg', '')
                        
                        # 🔴 استخراج بک‌گراند از فیلد backdrop
                        backdrop = info.get('backdrop', {})
                        bg_color = ""
                        
                        if isinstance(backdrop, dict):
                            # تلگرام رنگ‌ها را به صورت عدد RGB24 می‌دهد
                            # کتابخانه ممکن است آن را به gradient_from/to تبدیل کرده باشد
                            c_from = backdrop.get('gradient_from') or backdrop.get('center_color')
                            c_to = backdrop.get('gradient_to') or backdrop.get('edge_color')
                            
                            if c_from:
                                # تبدیل عدد به هگز (اگر عدد باشد)
                                if isinstance(c_from, int):
                                    bg_color = f"#{c_from:06x}"
                                elif isinstance(c_from, str) and not c_from.startswith('#'):
                                    bg_color = f"#{c_from}"
                                elif isinstance(c_from, str):
                                    bg_color = c_from
                                    
                                # اگر رنگ دوم هم بود، یک گرادیانت می‌سازیم
                                if c_to:
                                    if isinstance(c_to, int):
                                        c_to_hex = f"#{c_to:06x}"
                                    elif isinstance(c_to, str) and not c_to.startswith('#'):
                                        c_to_hex = f"#{c_to}"
                                    else:
                                        c_to_hex = c_to
                                    bg_color = f"linear-gradient(135deg, {bg_color}, {c_to_hex})"
                        
                        # اگر backdrop خالی بود، از فیلدهای دیگر تلاش کن
                        if not bg_color:
                            bg_color = info.get('background_color', '') or info.get('bg_color', '')
                            if bg_color and not str(bg_color).startswith('#'):
                                bg_color = f"#{bg_color}"

                        result.append({
                            "name": name,
                            "price": price,
                            "link": gift_link,
                            "image_url": img_url,
                            "bg_color": bg_color 
                        })
            except Exception as e:
                print(f"Error {gift.full_name}: {e}")
                continue
            
            if len(result) >= 100:
                break

# ... (بقیه کد)
