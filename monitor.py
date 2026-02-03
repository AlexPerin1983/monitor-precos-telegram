import os
import json
import re
import requests
from bs4 import BeautifulSoup
import time
from supabase import create_client, Client

# --- CONFIGURAÇÃO DO SUPABASE ---
SUPABASE_URL = "https://whbhxexafjdfumcondmi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndoYmh4ZXhhZmpkZnVtY29uZG1pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAxMjgxNTgsImV4cCI6MjA4NTcwNDE1OH0.vpo0ntHufGI0_8aTgwi5f3Zwq4YoqRVTkC1DY52umCY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURAÇÃO DO TELEGRAM ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

def parse_price(price_str):
    if not price_str: return None
    cleaned = re.sub(r'[^\d,\.]', '', str(price_str))
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None

def extract_price_from_html(html, selector=None):
    soup = BeautifulSoup(html, 'html.parser')
    if selector:
        element = soup.select_one(selector)
        if element:
            price_val = parse_price(element.get_text())
            if price_val: return price_val

    meta_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
    if meta_price:
        return parse_price(meta_price.get("content"))

    matches = re.findall(r'(?:R\$|RS)\s?(\d{1,3}(?:\.\d{3})*,\d{2})', html)
    if matches:
        valid_prices = [parse_price(m) for m in matches if parse_price(m) > 10.0]
        if valid_prices: return valid_prices[0]
    return None

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def main():
    # 1. Busca produtos do Supabase
    response = supabase.table("products").select("*").execute()
    products = response.data
    
    print(f"Iniciando monitoramento de {len(products)} produtos via Supabase...")
    
    for product in products:
        p_id = product['id']
        name = product['name']
        url = product['url']
        selector = product.get('css_selector')
        target = product.get('target_price')
        last_price = product.get('current_price') # Usamos o current_price do banco como o 'último'
        
        print(f"Verificando: {name}...")
        
        try:
            resp = requests.get(url, headers=get_headers(), timeout=20)
            current_price = extract_price_from_html(resp.text, selector)
            
            if current_price is None:
                print(f"  [AVISO] Preço não encontrado")
                continue

            # Atualiza no banco de dados
            supabase.table("products").update({
                "current_price": current_price,
                "last_price": last_price
            }).eq("id", p_id).execute()

            # Lógica de Notificação
            if not last_price or last_price == 0:
                send_telegram_message(f"✅ *Monitoramento Iniciado!*\n\n*Produto:* {name}\n*Preço atual:* R$ {current_price:.2f}")
            elif abs(current_price - last_price) > 0.01:
                diff = current_price - last_price
                trend = "aumentou 📈" if diff > 0 else "baixou 📉"
                msg = f"🔔 *Alteração de Preço!*\n\n*Produto:* {name}\n*De:* R$ {last_price:.2f}\n*Para:* R$ {current_price:.2f} ({trend})\n\n[Ver no site]({url})"
                send_telegram_message(msg)

            if target and current_price <= target:
                send_telegram_message(f"🎯 *Preço Alvo Atingido!*\n\n*Produto:* {name}\n*Preço:* R$ {current_price:.2f}\n*Alvo:* R$ {target:.2f}")

        except Exception as e:
            print(f"  [ERRO] {name}: {e}")

if __name__ == "__main__":
    main()
