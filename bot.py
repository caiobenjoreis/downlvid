import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
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

# Store video URLs temporarily for download callbacks
video_cache = {}

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
    """Shows region selection buttons for viral videos."""
    keyboard = [
        [
            InlineKeyboardButton("🌎 Mundial", callback_data="viral_US"),
            InlineKeyboardButton("🇧🇷 Brasil", callback_data="viral_BR"),
        ],
        [
            InlineKeyboardButton("🇺🇸 EUA", callback_data="viral_US"),
            InlineKeyboardButton("🇯🇵 Japão", callback_data="viral_JP"),
        ],
        [
            InlineKeyboardButton("🇬🇧 Reino Unido", callback_data="viral_GB"),
            InlineKeyboardButton("🇫🇷 França", callback_data="viral_FR"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔥 *Vídeos Virais do TikTok*\n\n"
        "Escolha a região:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def viral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles region selection and shows viral videos."""
    query = update.callback_query
    await query.answer()
    
    region = query.data.replace("viral_", "")
    
    region_names = {
        'US': 'Mundial',
        'BR': 'Brasil',
        'JP': 'Japão',
        'GB': 'Reino Unido',
        'FR': 'França'
    }
    
    region_name = region_names.get(region, region)
    
    await query.edit_message_text(f"🔥 Buscando vídeos virais ({region_name})... aguarde!")
    
    try:
        # Fetch videos
        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, get_tiktok_trending, 15, 5, region)
        
        if not videos:
            await query.edit_message_text("❌ Não foi possível buscar os vídeos virais no momento.")
            return
        
        await query.edit_message_text(f"📤 Enviando {len(videos)} vídeos virais de {region_name}...")
        
        # Helper function to format numbers
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Send each video as a photo with download button
        for i, v in enumerate(videos, 1):
            try:
                # Store video URL in cache for download callback
                video_id = v['url'].split('/')[-1]
                video_cache[video_id] = v['url']
                
                # Format stats
                likes = format_number(v['digg_count'])
                views = format_number(v['play_count'])
                
                # Create caption
                title = v['title'][:100] + "..." if len(v['title']) > 100 else v['title']
                caption = (
                    f"🔥 *Vídeo #{i}*\n\n"
                    f"📝 {title}\n\n"
                    f"👤 {v['author']}\n"
                    f"❤️ {likes} curtidas\n"
                    f"👁️ {views} visualizações\n\n"
                    f"🔗 [Ver no TikTok]({v['url']})"
                )
                
                # Create download button
                keyboard = [[InlineKeyboardButton("📥 Baixar Vídeo", callback_data=f"download_{video_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send photo with caption and button
                if v.get('cover'):
                    try:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=v['cover'],
                            caption=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception as photo_error:
                        # If photo fails, send as text
                        logger.warning(f"Failed to send photo: {photo_error}")
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup,
                            disable_web_page_preview=False
                        )
                else:
                    # No cover, send as text
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        parse_mode='Markdown',
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error sending video {i}: {e}")
                continue
        
        # Delete the "Sending..." message
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Error in viral_callback: {e}")
        await query.edit_message_text("❌ Ocorreu um erro ao buscar os vídeos.")

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles download button clicks."""
    query = update.callback_query
    await query.answer("📥 Iniciando download...")
    
    video_id = query.data.replace("download_", "")
    video_url = video_cache.get(video_id)
    
    if not video_url:
        await query.answer("❌ Link expirado. Use /viral novamente.", show_alert=True)
        return
    
    status_msg = await query.message.reply_text("⏳ Baixando vídeo... aguarde!")
    
    try:
        # Send typing action
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=ChatAction.UPLOAD_VIDEO)
        
        # Download video
        loop = asyncio.get_running_loop()
        
        try:
            file_path = await loop.run_in_executor(None, download_video, video_url)
        except DownloadError as e:
            # Try alternative method for TikTok
            if "tiktok.com" in video_url:
                await status_msg.edit_text("⏳ Tentando método alternativo...")
                try:
                    file_path = await loop.run_in_executor(None, download_tiktok_alternative, video_url)
                except Exception:
                    raise e
            else:
                raise e
        
        if not os.path.exists(file_path):
            await status_msg.edit_text("❌ Erro: Arquivo não encontrado.")
            return
        
        # Send video
        await status_msg.edit_text("📤 Enviando vídeo...")
        
        with open(file_path, 'rb') as video_file:
            await query.message.reply_video(
                video=video_file,
                caption="✅ Download concluído! 🎥",
                write_timeout=60,
                read_timeout=60
            )
        
        await status_msg.delete()
        
    except DownloadError as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text(f"❌ Erro no download:\n\n{str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in download: {e}")
        await status_msg.edit_text("❌ Erro inesperado ao baixar o vídeo.")
    finally:
        # Cleanup
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup: {e}")


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
    
    # Callback handlers for buttons
    viral_callback_handler = CallbackQueryHandler(viral_callback, pattern='^viral_')
    download_callback_handler = CallbackQueryHandler(download_callback, pattern='^download_')

    application.add_handler(start_handler)
    application.add_handler(viral_handler)
    application.add_handler(viral_callback_handler)
    application.add_handler(download_callback_handler)
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
