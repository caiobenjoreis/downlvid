import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError
from downloader import download_video, DownloadError, download_instagram_alternative, download_tiktok_alternative, get_tiktok_trending

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    welcome_message = (
        "🎬 *Bem-vindo ao Bot de Download de Vídeos!*\n\n"
        "📱 *Plataformas suportadas:*\n"
        "• Instagram (Reels, Posts, IGTV)\n"
        "• TikTok\n\n"
        "🔥 *Novidade:*\n"
        "Use /viral para ver os vídeos mais bombados do TikTok!\n\n"
        "📝 *Como usar:*\n"
        "1. Copie o link do vídeo\n"
        "2. Envie para mim\n"
        "3. Aguarde o download\n\n"
        "⚠️ *Importante:*\n"
        "• O vídeo deve ser público\n"
        "• Links privados não funcionam\n\n"
        "Envie um link para começar! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def viral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a list of trending TikTok videos."""
    status_msg = await update.message.reply_text("🔥 Buscando vídeos virais do TikTok... aguarde!")
    
    try:
        # Run in executor to avoid blocking
        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, get_tiktok_trending, 15, 5)
        
        if not videos:
            await status_msg.edit_text("❌ Não foi possível buscar os vídeos virais no momento. Tente novamente mais tarde.")
            return
            
        message = "🔥 *Top 15 Vídeos Virais do TikTok (Brasil)* 🔥\n"
        message += "📅 *Últimos 5 dias*\n\n"
        
        for i, v in enumerate(videos, 1):
            # Format numbers (e.g. 1.2M)
            def format_number(num):
                if num >= 1000000:
                    return f"{num/1000000:.1f}M"
                elif num >= 1000:
                    return f"{num/1000:.1f}K"
                return str(num)
                
            likes = format_number(v['digg_count'])
            views = format_number(v['play_count'])
            
            # Escape markdown characters in title and author
            title = v['title'][:50] + "..." if len(v['title']) > 50 else v['title']
            title = title.replace("*", "").replace("_", "").replace("`", "")
            author = v['author'].replace("*", "").replace("_", "").replace("`", "")
            
            message += f"{i}. [{title}]({v['url']})\n"
            message += f"   👤 {author} | ❤️ {likes} | 👁️ {views}\n\n"
            
        await status_msg.edit_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in viral command: {e}")
        await status_msg.edit_text("❌ Ocorreu um erro ao buscar os vídeos.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages containing URLs."""
    url = update.message.text.strip()
    
    # Basic validation
    if not ("instagram.com" in url or "tiktok.com" in url):
        await update.message.reply_text(
            "❌ *Link inválido!*\n\n"
            "Por favor, envie um link válido do:\n"
            "• Instagram (instagram.com)\n"
            "• TikTok (tiktok.com)",
            parse_mode='Markdown'
        )
        return

    status_msg = await update.message.reply_text("⏳ Processando seu vídeo...\n\nIsso pode levar alguns segundos.")
    
    file_path = None
    
    try:
        # Send typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
        
        # Download video
        # Run in executor to avoid blocking the async loop
        loop = asyncio.get_running_loop()
        
        try:
            file_path = await loop.run_in_executor(None, download_video, url)
        except DownloadError as e:
            # If main method fails, try alternative methods
            if "instagram.com" in url:
                await status_msg.edit_text("⏳ Tentando método alternativo de download...")
                try:
                    file_path = await loop.run_in_executor(None, download_instagram_alternative, url)
                except Exception:
                    raise e  # Re-raise original error
            elif "tiktok.com" in url:
                await status_msg.edit_text("⏳ Tentando método alternativo de download...")
                try:
                    file_path = await loop.run_in_executor(None, download_tiktok_alternative, url)
                except Exception:
                    raise e  # Re-raise original error
            else:
                raise e
        
        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Erro: O arquivo não foi encontrado após o download.")
            return

        # Update status
        await status_msg.edit_text("📤 Enviando vídeo...")

        # Send video
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Aqui está seu vídeo! 🎥\n\n💡 Envie outro link para baixar mais vídeos.",
                write_timeout=60,
                read_timeout=60
            )
        
        # Cleanup
        await status_msg.delete()
        
    except DownloadError as e:
        logger.error(f"Download error for URL {url}: {e}")
        error_message = f"❌ *Erro no download:*\n\n{str(e)}\n\n💡 *Dicas:*\n• Verifique se o vídeo é público\n• Tente copiar o link novamente\n• Certifique-se de que o vídeo ainda existe"
        await status_msg.edit_text(error_message, parse_mode='Markdown')
        
    except TelegramError as e:
        logger.error(f"Telegram error for URL {url}: {e}")
        await status_msg.edit_text(
            f"❌ *Erro ao enviar o vídeo:*\n\n"
            f"O vídeo pode ser muito grande para o Telegram.\n"
            f"Tamanho máximo: 50 MB\n\n"
            f"Detalhes: {str(e)}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Unexpected error processing URL {url}: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ *Erro inesperado:*\n\n"
            f"{str(e)}\n\n"
            f"Por favor, tente novamente ou entre em contato com o suporte.",
            parse_mode='Markdown'
        )
    
    finally:
        # Cleanup file if it exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

def main():
    if not TOKEN:
        print("Erro: TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
        return

    # Ensure downloads directory exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    viral_handler = CommandHandler('viral', viral)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(viral_handler)
    application.add_handler(msg_handler)

    # Start dummy web server for Render
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running!')

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

    def start_web_server():
        port = int(os.environ.get('PORT', 8080))
        try:
            server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
            print(f"Server started on port {port}")
            server.serve_forever()
        except Exception as e:
            print(f"Error starting web server: {e}")

    # Run web server in background
    thread = Thread(target=start_web_server)
    thread.daemon = True
    thread.start()

    print("Bot iniciado...")
    application.run_polling()

if __name__ == '__main__':
    main()
