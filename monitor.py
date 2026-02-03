import os
import json
import re
import requests
from bs4 import BeautifulSoup
import time

# --- CONFIGURAÇÃO DOS PRODUTOS ---
PRODUCTS = [
    {
        "name": "Produto de Teste (Estável)",
        # Usando uma página que não bloqueia para validar seu Telegram
        "url": "https://www.google.com/search?q=preco+iphone+15", 
        "css_selector": None, 
        "target_price": 10000.00
    },
]

# --- CONFIGURAÇÃO DO TELEGRAM ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def parse_price(price_str):
    """Converte strings como 'R$ 1.234,56' em float 1234.56"""
    if not price_str:
        return None
    # Remove tudo que não é dígito, vírgula ou ponto
    cleaned = re.sub(r'[^\d,\.]', '', price_str)
    # Se houver ponto e vírgula (formato brasileiro), remove o ponto e troca vírgula por ponto
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    # Se só houver vírgula, troca por ponto
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def extract_price_from_html(html, selector=None):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Tenta pelo seletor CSS se fornecido
    if selector:
        element = soup.select_one(selector)
        if element:
            price_val = parse_price(element.get_text())
            if price_val:
                return price_val

    # 2. Fallback 1: Busca em tags meta (comum em lojas como Amazon/Shopee para SEO)
    meta_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
    if meta_price:
        return parse_price(meta_price.get("content"))

    # 3. Fallback 2: Regex agressivo no HTML bruto
    # Procura por R$ ou RS seguido de números, pontos e vírgulas
    matches = re.findall(r'(?:R\$|RS)\s?(\d{1,3}(?:\.\d{3})*,\d{2})', html)
    if matches:
        # Filtra valores muito baixos (provavelmente frete) se houver múltiplos
        valid_prices = [parse_price(m) for m in matches if parse_price(m) > 10.0]
        if valid_prices:
            return valid_prices[0]
    
    return None

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token ou Chat ID não configurados.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def main():
    state = load_state()
    new_state = state.copy()
    
    print(f"Iniciando monitoramento de {len(PRODUCTS)} produtos...")
    
    for product in PRODUCTS:
        name = product['name']
        url = product['url']
        selector = product.get('css_selector')
        target = product.get('target_price')
        
        print(f"Verificando: {name}...")
        
        try:
            response = requests.get(url, headers=get_headers(), timeout=20)
            response.raise_for_status()
            
            current_price = extract_price_from_html(response.text, selector)
            
            if current_price is None:
                error_msg = f"⚠️ [AVISO] Não foi possível encontrar o preço para {name}. Verifique se o CSS Selector '{selector}' ainda é válido ou se o site mudou."
                print(error_msg)
                # Opcional: Descomente a linha abaixo se quiser receber erro no Telegram também
                # send_telegram_message(error_msg)
                continue

            last_price = state.get(url)
            
            msg = None
            if last_price is None:
                # MUDANÇA: Avisa quando o produto é monitorado pela primeira vez
                msg = f"✅ *Monitoramento Iniciado!*\n\n*Produto:* {name}\n*Preço atual:* R$ {current_price:.2f}\n\nAgora estou vigiando este preço de hora em hora para você!"
                print(f"  Preço inicial detectado: R$ {current_price:.2f}")
                new_state[url] = current_price
            elif abs(current_price - last_price) > 0.01: # Pequena margem para evitar avisos por centavos de arredondamento
                diff = current_price - last_price
                trend = "aumentou 📈" if diff > 0 else "baixou 📉"
                msg = f"🔔 *Alteração de Preço!*\n\n*Produto:* {name}\n*De:* R$ {last_price:.2f}\n*Para:* R$ {current_price:.2f} ({trend})\n\n[Ver no site]({url})"
                print(f"  [MUDANÇA] R$ {last_price:.2f} -> R$ {current_price:.2f}")
                new_state[url] = current_price
            else:
                print(f"  Sem alteração relevante: R$ {current_price:.2f}")

            # Alerta de valor alvo
            if target and current_price <= target:
                target_msg = f"🎯 *Preço Alvo Atingido!*\n\n*Produto:* {name}\n*Preço atual:* R$ {current_price:.2f}\n*Alvo:* R$ {target:.2f}\n\n[Comprar Agora]({url})"
                send_telegram_message(target_msg)

            if msg:
                send_telegram_message(msg)
                
        except Exception as e:
            print(f"  [ERRO] Falha ao processar {name}: {e}")
            
    save_state(new_state)
    print("Monitoramento concluído.")

if __name__ == "__main__":
    main()
