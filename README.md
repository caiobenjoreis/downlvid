# 🎬 Bot de Download de Vídeos (Instagram & TikTok)

Bot do Telegram profissional para baixar vídeos do Instagram (Reels, Posts, IGTV) e TikTok sem marca d'água.

## ✨ Funcionalidades

- ✅ Download de vídeos do Instagram (Reels, Posts, IGTV)
- ✅ Download de vídeos do TikTok (sem marca d'água)
- ✅ Detecção automática de plataforma
- ✅ Download na melhor qualidade disponível
- ✅ Múltiplos métodos de fallback para maior confiabilidade
- ✅ Mensagens de erro detalhadas e amigáveis
- ✅ Interface em português com emojis

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Token do Bot do Telegram (obtenha com [@BotFather](https://t.me/BotFather))
- FFmpeg (opcional, mas recomendado para melhor compatibilidade)

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone <seu-repositorio>
cd bot_download_videos
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure o Token do Bot

Crie um arquivo `.env` na raiz do projeto:

```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
```

**Como obter o token:**
1. Abra o Telegram e procure por [@BotFather](https://t.me/BotFather)
2. Envie `/newbot` e siga as instruções
3. Copie o token fornecido
4. Cole no arquivo `.env`

### 4. Execute o bot

```bash
python bot.py
```

Você verá a mensagem: `Bot iniciado...`

## 💡 Como Usar

1. Abra o bot no Telegram
2. Envie `/start` para ver as instruções
3. Copie o link de um vídeo do Instagram ou TikTok
4. Envie o link para o bot
5. Aguarde o download e receba o vídeo!

### Exemplos de links suportados:

**Instagram:**
- `https://www.instagram.com/reel/ABC123/`
- `https://www.instagram.com/p/ABC123/`
- `https://www.instagram.com/tv/ABC123/`

**TikTok:**
- `https://www.tiktok.com/@user/video/123456789`
- `https://vm.tiktok.com/ABC123/`

## 🛠️ Tecnologias Utilizadas

- **python-telegram-bot**: Framework para bots do Telegram
- **yt-dlp**: Ferramenta poderosa para download de vídeos
- **requests**: Para requisições HTTP alternativas
- **python-dotenv**: Gerenciamento de variáveis de ambiente

## 📁 Estrutura do Projeto

```
bot_download_videos/
├── bot.py              # Lógica principal do bot
├── downloader.py       # Módulo de download de vídeos
├── requirements.txt    # Dependências Python
├── .env               # Variáveis de ambiente (criar manualmente)
├── downloads/         # Pasta temporária (criada automaticamente)
└── README.md          # Este arquivo
```

## ⚠️ Limitações

- **Vídeos privados**: Apenas vídeos públicos podem ser baixados
- **Tamanho máximo**: O Telegram limita vídeos a 50 MB
- **Contas privadas**: Não é possível baixar de contas privadas
- **Stories**: Stories do Instagram não são suportados

## 🌐 Hospedagem (Deploy)

### ⭐ Opção 1: Fly.io (Recomendado - Gratuito)

**Melhor opção para este bot!** Plano gratuito robusto sem necessidade de cartão de crédito.

📖 **[Guia Completo de Deploy no Fly.io](./DEPLOY_GUIDE.md)**  
⚡ **[Guia Rápido de Referência](./DEPLOY_QUICK_REFERENCE.md)**

**Vantagens:**
- ✅ 100% gratuito (sem cartão necessário)
- ✅ Servidor no Brasil (São Paulo)
- ✅ Deploy simples via CLI
- ✅ Logs em tempo real
- ✅ Auto-scaling

**Início Rápido:**
```powershell
# Instalar Fly CLI
iwr https://fly.io/install.ps1 -useb | iex

# Login
fly auth login

# Deploy
fly deploy
```

### Opção 2: Railway

1. Crie uma conta em [Railway.app](https://railway.app/)
2. Conecte seu repositório GitHub
3. Adicione a variável de ambiente `TELEGRAM_BOT_TOKEN`
4. Deploy automático!

### Opção 3: Render

1. Crie uma conta em [Render.com](https://render.com/)
2. Crie um novo "Background Worker"
3. Conecte seu repositório
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Adicione a variável `TELEGRAM_BOT_TOKEN`

### Opção 4: VPS (DigitalOcean, AWS, etc.)

```bash
# Instale Python e dependências
sudo apt update
sudo apt install python3 python3-pip ffmpeg -y

# Clone o projeto
git clone <seu-repositorio>
cd bot_download_videos

# Instale dependências
pip3 install -r requirements.txt

# Configure o .env
nano .env
# Cole: TELEGRAM_BOT_TOKEN=seu_token

# Execute com screen ou tmux
screen -S bot
python3 bot.py
# Ctrl+A+D para desanexar
```

### Opção 5: Docker

O projeto já inclui um `Dockerfile` configurado. Execute:

```bash
# Build da imagem
docker build -t bot-download .
docker run -d --env-file .env bot-download
```

## 🔧 Solução de Problemas

### Erro: "TELEGRAM_BOT_TOKEN não encontrado"
- Verifique se o arquivo `.env` existe
- Confirme que o token está correto
- Reinicie o bot

### Erro: "Este vídeo é privado"
- O vídeo deve ser público
- Verifique se a conta não é privada

### Erro: "Arquivo muito grande"
- O Telegram limita vídeos a 50 MB
- Tente um vídeo menor

### Bot não responde
- Verifique se o bot está rodando
- Confirme que o token está correto
- Veja os logs para erros

## 📝 Logs

O bot gera logs detalhados no console. Para salvar em arquivo:

```bash
python bot.py > bot.log 2>&1
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Enviar pull requests

## 📄 Licença

Este projeto é de código aberto e está disponível sob a licença MIT.

## ⚖️ Aviso Legal

Este bot é apenas para fins educacionais. Respeite os direitos autorais e os termos de serviço das plataformas. Use por sua conta e risco.

---

**Desenvolvido com ❤️ para a comunidade**
