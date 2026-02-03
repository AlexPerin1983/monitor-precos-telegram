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
        "Referer": "https://www.google.com.br/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1"
    }

def parse_price(price_str):
    if not price_str: return None
    # Remove tudo que não é número, ponto ou vírgula
    cleaned = re.sub(r'[^\d,\.]', '', str(price_str))
    
    if not cleaned: return None

    # Caso 1: Formato 1.545,00 ou 1.545
    if ',' in cleaned:
        # Se tem vírgula, assume que é o decimal brasileiro
        parts = cleaned.split(',')
        inteira = parts[0].replace('.', '')
        decimal = parts[1] if len(parts) > 1 else '00'
        cleaned = f"{inteira}.{decimal}"
    else:
        # Se não tem vírgula, remove pontos de milhar
        cleaned = cleaned.replace('.', '')
        
    try:
        return float(cleaned)
    except ValueError:
        return None

def extract_price_from_html(html, name=""):
    soup = BeautifulSoup(html, 'html.parser')
    
    # --- DIAGNÓSTICO ---
    title = soup.title.string.strip() if soup.title else "Sem Título"
    if "Acesso Negado" in title or "Access Denied" in title or "Robot" in title or "Captcha" in title:
        print(f"  [BLOQUEIO DETECTADO] O site bloqueou o robô. Título: {title}")
        return None

    # 1. Tenta por JSON-LD (DADOS ESTRUTURADOS) - A forma mais estável
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string)
            # Pode ser um dicionário ou uma lista de dicionários
            items = data if isinstance(data, list) else [data]
            for item in items:
                # Procura por 'offers' -> 'price'
                offers = item.get("offers")
                if offers:
                    if isinstance(offers, dict):
                        p = parse_price(offers.get("price"))
                        if p: return p
                    elif isinstance(offers, list):
                        p = parse_price(offers[0].get("price"))
                        if p: return p
        except:
            continue

    # 2. Tenta por seletores específicos das maiores lojas
    specific_selectors = [
        ".andes-money-amount__fraction", 
        ".a-price-whole", 
        "[itemprop='price']",
        "span.priceTag--price",
        ".price-tag-fraction"
    ]
    
    for s in specific_selectors:
        element = soup.select_one(s)
        if element:
            p = parse_price(element.get_text())
            if p: return p

    # 3. Tenta por Meta Tags
    meta_tags = [
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "og:price:amount"}),
        ("meta", {"itemprop": "price"}),
    ]
    for tag, attrs in meta_tags:
        element = soup.find(tag, attrs)
        if element:
            p = parse_price(element.get("content"))
            if p: return p

    # 4. Fallback: Busca via padrões JSON/Script (Onde o preço fica escondido)
    # Procura por "price":1545 ou "amount":1545
    json_patterns = [
        r'"price":\s?(\d+(?:\.\d+)?)',
        r'"amount":\s?(\d+(?:\.\d+)?)',
        r'"price_amount":\s?(\d+(?:\.\d+)?)'
    ]
    for pattern in json_patterns:
        match = re.search(pattern, html)
        if match:
            p = parse_price(match.group(1))
            if p and p > 100.0: return p

    # 5. Busca Ultra-Agressiva no texto limpo (sem tags)
    text_clean = soup.get_text(separator=' ')
    # Procura R$ 1.545 ou R$ 1545
    matches = re.findall(r'(?:R\$|RS)\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', text_clean)
    if not matches:
        # Tenta sem o R$ apenas números grandes perto de palavras-chave
        matches = re.findall(r'(?:preço|valor|total|por)\s?:?\s?R?\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)', text_clean, re.IGNORECASE)
    
    if matches:
        for m in matches:
            val = parse_price(m)
            if val and val > 100.0: return val

    print(f"  [DEBUG] Não achei preço em {name}. Título da página: {title}")
    return None

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def main():
    # Cria uma sessão para manter cookies (parece mais um humano navegando)
    session = requests.Session()
    session.headers.update(get_headers())
    
    # 1. Busca produtos do Supabase
    response = supabase.table("products").select("*").execute()
    products = response.data
    
    print(f"Iniciando monitoramento de {len(products)} produtos via Supabase...")
    
    for product in products:
        time.sleep(3) # Pausa maior para não assustar o servidor
        p_id = product['id']
        name = product['name']
        url = product['url']
        last_price = product.get('current_price')
        
        print(f"Verificando: {name}...")
        
        try:
            # Tenta carregar a página com a sessão
            resp = session.get(url, timeout=30)
            
            # Verifica se fomos redirecionados para a home ou login
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string if soup.title else ""
            
            # Se o título for só "Mercado Livre", tenta um segundo acesso (às vezes o 2º passa)
            if title.strip() == "Mercado Livre":
                print(f"  [RE-TENTATIVA] O site tentou nos desviar. Tentando novamente...")
                time.sleep(2)
                resp = session.get(url, timeout=30)

            current_price = extract_price_from_html(resp.text, name)
            
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
