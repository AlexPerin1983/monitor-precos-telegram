# Price Monitor Telegram 🚀

Este projeto monitora preços de produtos em sites de e-commerce e envia notificações via Telegram quando o preço muda ou atinge um valor-alvo. Funciona 100% grátis usando GitHub Actions.

## 🛠️ Como configurar

### 1. Criar o Bot no Telegram
1. Fale com o [@BotFather](https://t.me/botfather) no Telegram.
2. Envie `/newbot` e siga as instruções para criar seu bot.
3. Copie o **API Token** gerado.

### 2. Obter seu Chat ID
1. Comece uma conversa com o seu bot recém-criado.
2. Envie qualquer mensagem para ele.
3. Acesse a URL: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates` (substitua `<SEU_TOKEN>` pelo token do passo anterior).
4. Procure no JSON retornado pelo campo `"id"` dentro do objeto `"chat"`. Esse é o seu **CHAT ID**.

### 3. Configurar no GitHub
1. Vá até o seu repositório no GitHub.
2. Clique em **Settings** > **Secrets and variables** > **Actions**.
3. Crie dois segredos:
   - `TELEGRAM_TOKEN`: Cole o token do bot.
   - `TELEGRAM_CHAT_ID`: Cole o seu ID numérico.

### 4. Personalizar os Produtos
Edite o arquivo `monitor.py` na seção `PRODUCTS`.
```python
PRODUCTS = [
    {
        "name": "Nome do Produto",
        "url": "https://url-do-produto.com.br",
        "css_selector": ".classe-do-preco", # Opcional: use o inspetor do navegador para achar
        "target_price": 500.00 # Opcional: preço alvo para alerta
    }
]
```

#### Como descobrir o `css_selector`? 🔎
1. Abra o site do produto no Chrome/Edge.
2. Clique com o botão direito sobre o preço e selecione **Inspecionar**.
3. No painel que abrir, o HTML do elemento estará selecionado. Procure pela classe (ex: `class="price-value"`) ou ID.
4. O seletor seria `.price-value` para classes ou `#id-do-elemento` para IDs.

## 🚀 Como testar localmente
1. Instale o Python 3.11+.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Defina as variáveis de ambiente (Windows PowerShell):
   ```powershell
   $env:TELEGRAM_TOKEN="seu_token"
   $env:TELEGRAM_CHAT_ID="seu_chat_id"
   ```
4. Rode o script:
   ```bash
   python monitor.py
   ```

## ⚙️ Funcionamento
- O script roda automaticamente **a cada hora** via GitHub Actions.
- Se o preço mudar em relação à última execução, você recebe uma mensagem.
- Se o preço baixar do seu `target_price`, você recebe um alerta especial.
- O estado dos preços é salvo no arquivo `state.json` automaticamente no repositório.

## ⚠️ Boas Práticas
- Não monitore centenas de produtos de uma vez para evitar bloqueios por IP.
- Respeite os termos de uso dos sites.
- A frequência de 1 hora é segura para a maioria dos sites grandes.
