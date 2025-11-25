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
        "🔥 *Recursos de Download:*\n"
        "• `/viral` - Vídeos virais por região\n"
        "• `/viral #hashtag` - Buscar por tema\n"
        "• `/viral #hashtag BR` - Buscar por tema e região\n\n"
        "✨ *Creator Insights:*\n"
        "• `/tendencias` - Tópicos em alta e oportunidades\n"
        "• `/analisar @user` - Análise completa de creator\n"
        "• `/musicas` - Trending sounds do TikTok\n\n"
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
    """Shows region selection buttons for viral videos or searches by hashtag."""
    
    # Check if user provided arguments (hashtag and/or region)
    args = context.args
    
    if args:
        # User provided hashtag/parameters
        hashtag = None
        region = 'US'  # Default region
        
        # Parse arguments
        for arg in args:
            if arg.upper() in ['BR', 'US', 'JP', 'GB', 'FR']:
                region = arg.upper()
            else:
                # Assume it's the hashtag
                hashtag = arg.strip().lstrip('#')
        
        if hashtag:
            # Search by hashtag
            await viral_hashtag_search(update, context, hashtag, region)
            return
    
    # No arguments - show region selection (original behavior)
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
        "Escolha a região:\n\n"
        "💡 *Dica:* Use `/viral #hashtag` para buscar por tema!\n"
        "Exemplo: `/viral #futebol` ou `/viral #receitas BR`",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def viral_hashtag_search(update: Update, context: ContextTypes.DEFAULT_TYPE, hashtag: str, region: str = 'US', sort_by: str = 'likes'):
    """Searches and displays TikTok videos by hashtag."""
    from downloader import search_tiktok_by_hashtag
    
    region_names = {
        'US': 'Mundial',
        'BR': 'Brasil',
        'JP': 'Japão',
        'GB': 'Reino Unido',
        'FR': 'França'
    }
    
    region_name = region_names.get(region, region)
    
    # Send initial message
    status_msg = await update.message.reply_text(
        f"🔍 Buscando vídeos de *#{hashtag}* ({region_name})...\n\n"
        f"Aguarde um momento! ⏳",
        parse_mode='Markdown'
    )
    
    try:
        # Fetch videos
        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, search_tiktok_by_hashtag, hashtag, 15, region, sort_by)
        
        if not videos:
            await status_msg.edit_text(
                f"❌ Nenhum vídeo encontrado para *#{hashtag}*\n\n"
                f"💡 Tente:\n"
                f"• Verificar a ortografia\n"
                f"• Usar hashtags mais populares\n"
                f"• Mudar a região",
                parse_mode='Markdown'
            )
            return
        
        # Create filter buttons
        sort_emoji = {
            'likes': '❤️',
            'views': '👁️',
            'date': '🆕'
        }
        current_emoji = sort_emoji.get(sort_by, '❤️')
        
        filter_keyboard = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'likes' else ''}❤️ Curtidas",
                    callback_data=f"filter_{hashtag}_{region}_likes"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'views' else ''}👁️ Views",
                    callback_data=f"filter_{hashtag}_{region}_views"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'date' else ''}🆕 Recentes",
                    callback_data=f"filter_{hashtag}_{region}_date"
                ),
            ]
        ]
        filter_markup = InlineKeyboardMarkup(filter_keyboard)
        
        await status_msg.edit_text(
            f"📤 Enviando {len(videos)} vídeos de *#{hashtag}* ({region_name})\n\n"
            f"Ordenado por: {current_emoji}",
            parse_mode='Markdown',
            reply_markup=filter_markup
        )
        
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
                    f"🔥 *Vídeo #{i}* - #{hashtag}\n\n"
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
                            chat_id=update.effective_chat.id,
                            photo=v['cover'],
                            caption=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception as photo_error:
                        # If photo fails, send as text
                        logger.warning(f"Failed to send photo: {photo_error}")
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup,
                            disable_web_page_preview=False
                        )
                else:
                    # No cover, send as text
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
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
        
    except Exception as e:
        logger.error(f"Error in viral_hashtag_search: {e}")
        await status_msg.edit_text(
            f"❌ Ocorreu um erro ao buscar vídeos de #{hashtag}\n\n"
            f"Tente novamente mais tarde.",
            parse_mode='Markdown'
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


async def viral_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles filter button clicks for hashtag search results."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: filter_hashtag_region_sortby
    parts = query.data.replace("filter_", "").split("_")
    
    if len(parts) < 3:
        await query.answer("❌ Erro ao processar filtro", show_alert=True)
        return
    
    # Extract parameters
    sort_by = parts[-1]  # Last part is sort_by
    region = parts[-2]   # Second to last is region
    hashtag = "_".join(parts[:-2])  # Everything else is hashtag
    
    from downloader import search_tiktok_by_hashtag
    
    region_names = {
        'US': 'Mundial',
        'BR': 'Brasil',
        'JP': 'Japão',
        'GB': 'Reino Unido',
        'FR': 'França'
    }
    
    region_name = region_names.get(region, region)
    
    await query.edit_message_text(
        f"🔍 Reordenando vídeos de *#{hashtag}* ({region_name})...\n\n"
        f"Aguarde! ⏳",
        parse_mode='Markdown'
    )
    
    try:
        # Fetch videos with new sort order
        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, search_tiktok_by_hashtag, hashtag, 15, region, sort_by)
        
        if not videos:
            await query.edit_message_text(
                f"❌ Nenhum vídeo encontrado para *#{hashtag}*",
                parse_mode='Markdown'
            )
            return
        
        # Create filter buttons with current selection marked
        filter_keyboard = [
            [
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'likes' else ''}❤️ Curtidas",
                    callback_data=f"filter_{hashtag}_{region}_likes"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'views' else ''}👁️ Views",
                    callback_data=f"filter_{hashtag}_{region}_views"
                ),
                InlineKeyboardButton(
                    f"{'✅ ' if sort_by == 'date' else ''}🆕 Recentes",
                    callback_data=f"filter_{hashtag}_{region}_date"
                ),
            ]
        ]
        filter_markup = InlineKeyboardMarkup(filter_keyboard)
        
        sort_emoji = {
            'likes': '❤️',
            'views': '👁️',
            'date': '🆕'
        }
        current_emoji = sort_emoji.get(sort_by, '❤️')
        
        await query.edit_message_text(
            f"📤 Enviando {len(videos)} vídeos de *#{hashtag}* ({region_name})\n\n"
            f"Ordenado por: {current_emoji}",
            parse_mode='Markdown',
            reply_markup=filter_markup
        )
        
        # Helper function to format numbers
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Send each video
        for i, v in enumerate(videos, 1):
            try:
                video_id = v['url'].split('/')[-1]
                video_cache[video_id] = v['url']
                
                likes = format_number(v['digg_count'])
                views = format_number(v['play_count'])
                
                title = v['title'][:100] + "..." if len(v['title']) > 100 else v['title']
                caption = (
                    f"🔥 *Vídeo #{i}* - #{hashtag}\n\n"
                    f"📝 {title}\n\n"
                    f"👤 {v['author']}\n"
                    f"❤️ {likes} curtidas\n"
                    f"👁️ {views} visualizações\n\n"
                    f"🔗 [Ver no TikTok]({v['url']})"
                )
                
                keyboard = [[InlineKeyboardButton("📥 Baixar Vídeo", callback_data=f"download_{video_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if v.get('cover'):
                    try:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=v['cover'],
                            caption=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception:
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=caption,
                            parse_mode='Markdown',
                            reply_markup=reply_markup,
                            disable_web_page_preview=False
                        )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=caption,
                        parse_mode='Markdown',
                        reply_markup=reply_markup,
                        disable_web_page_preview=False
                    )
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error sending video {i}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error in viral_filter_callback: {e}")
        await query.edit_message_text(
            f"❌ Erro ao reordenar vídeos de #{hashtag}",
            parse_mode='Markdown'
        )


async def tendencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows trending topics and content gaps."""
    from downloader import get_trending_topics
    
    # Get category from args if provided
    category = 'all'
    region = 'BR'  # Default to Brazil
    
    if context.args:
        category = context.args[0].lower()
    
    status_msg = await update.message.reply_text(
        f"🔍 Buscando tendências...\n\nAguarde um momento! ⏳",
        parse_mode='Markdown'
    )
    
    try:
        # Fetch trending topics
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, get_trending_topics, category, region, 10)
        
        trending = data.get('trending', [])
        content_gaps = data.get('content_gaps', [])
        
        if not trending:
            await status_msg.edit_text(
                "❌ Não foi possível buscar tendências no momento.\n\n"
                "Tente novamente mais tarde.",
                parse_mode='Markdown'
            )
            return
        
        # Helper function to format numbers
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Build trending topics message
        message = "🔥 *Tendências no TikTok*\n\n📈 *Em Alta:*\n"
        
        for i, topic in enumerate(trending[:5], 1):
            comp_emoji = {
                'ALTA': '🔴',
                'MÉDIA': '🟡',
                'BAIXA': '🟢'
            }.get(topic['competition'], '⚪')
            
            message += (
                f"{i}. #{topic['name']}\n"
                f"   📊 {topic['count']} vídeos\n"
                f"   {comp_emoji} Competição: {topic['competition']}\n"
                f"   👁️ Média: {format_number(topic['avg_views'])} views\n\n"
            )
        
        # Add content gaps if available
        if content_gaps:
            message += "\n💡 *Oportunidades (Content Gaps):*\n\n"
            for i, gap in enumerate(content_gaps[:3], 1):
                pot_emoji = {
                    'ALTO': '🔥',
                    'MÉDIO': '⭐',
                    'BAIXO': '💫'
                }.get(gap['potential'], '💫')
                
                message += (
                    f"{i}. #{gap['name']}\n"
                    f"   {pot_emoji} Potencial: {gap['potential']}\n"
                    f"   🟢 Competição: {gap['competition']}\n"
                    f"   ❤️ Média: {format_number(gap['avg_likes'])} curtidas\n\n"
                )
            
            message += "\n💡 *Dica:* Content gaps são temas com boa demanda\nmas pouca concorrência - perfeito para viralizar!"
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in tendencias: {e}")
        await status_msg.edit_text(
            "❌ Ocorreu um erro ao buscar tendências.\n\n"
            "Tente novamente mais tarde.",
            parse_mode='Markdown'
        )


async def analisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyzes a TikTok creator's profile and performance."""
    from downloader import get_creator_info, get_creator_videos
    
    # Check if username was provided
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso incorreto!*\n\n"
            "Use: `/analisar @username`\n\n"
            "Exemplo: `/analisar @whinderssonnunes`",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0]
    
    status_msg = await update.message.reply_text(
        f"📊 Analisando @{username.lstrip('@')}...\n\nAguarde! ⏳",
        parse_mode='Markdown'
    )
    
    try:
        # Fetch creator info
        loop = asyncio.get_running_loop()
        creator_info = await loop.run_in_executor(None, get_creator_info, username)
        
        if not creator_info:
            await status_msg.edit_text(
                f"❌ Não foi possível encontrar @{username.lstrip('@')}\n\n"
                f"💡 *Verifique:*\n"
                f"• O username está correto\n"
                f"• O perfil é público\n"
                f"• O usuário existe no TikTok",
                parse_mode='Markdown'
            )
            return
        
        # Fetch recent videos
        videos = await loop.run_in_executor(None, get_creator_videos, username, 5)
        
        # Helper function to format numbers
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            return str(num)
        
        # Build analysis message
        verified_badge = "✅" if creator_info.get('verified') else ""
        
        message = (
            f"📊 *Análise de @{creator_info['username']}* {verified_badge}\n\n"
            f"👤 *Perfil:*\n"
            f"• Nome: {creator_info['nickname']}\n"
            f"• Seguidores: {format_number(creator_info['followers'])}\n"
            f"• Seguindo: {format_number(creator_info['following'])}\n"
            f"• Total de likes: {format_number(creator_info['total_likes'])}\n"
            f"• Vídeos: {format_number(creator_info['video_count'])}\n\n"
            f"📈 *Engajamento:*\n"
            f"• Taxa média: {creator_info['engagement_rate']}%\n"
        )
        
        if creator_info['signature']:
            bio = creator_info['signature'][:100]
            if len(creator_info['signature']) > 100:
                bio += "..."
            message += f"\n📝 *Bio:* {bio}\n"
        
        # Add top videos if available
        if videos:
            message += f"\n🎬 *Top {len(videos)} Vídeos Recentes:*\n\n"
            for i, v in enumerate(videos[:3], 1):
                title = v['title'][:50] + "..." if len(v['title']) > 50 else v['title']
                message += (
                    f"{i}. {title}\n"
                    f"   👁️ {format_number(v['play_count'])} views\n"
                    f"   ❤️ {format_number(v['digg_count'])} curtidas\n"
                    f"   💬 {format_number(v['comment_count'])} comentários\n\n"
                )
        
        message += (
            f"\n💡 *Insights:*\n"
            f"• Média de likes por vídeo: {format_number(creator_info['total_likes'] // max(creator_info['video_count'], 1))}\n"
        )
        
        # Send analysis
        if creator_info.get('avatar'):
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=creator_info['avatar'],
                    caption=message,
                    parse_mode='Markdown'
                )
                await status_msg.delete()
            except Exception:
                await status_msg.edit_text(message, parse_mode='Markdown')
        else:
            await status_msg.edit_text(message, parse_mode='Markdown')
        
        # Send top videos with download buttons
        if videos:
            for i, v in enumerate(videos[:3], 1):
                try:
                    # Store video URL in cache
                    video_id = v['url'].split('/')[-1]
                    video_cache[video_id] = v['url']
                    
                    # Create download button
                    keyboard = [[InlineKeyboardButton("📥 Baixar Vídeo", callback_data=f"download_{video_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    title = v['title'][:100] + "..." if len(v['title']) > 100 else v['title']
                    caption = (
                        f"🔥 *Top #{i}*\n\n"
                        f"📝 {title}\n\n"
                        f"👁️ {format_number(v['play_count'])} views\n"
                        f"❤️ {format_number(v['digg_count'])} curtidas\n"
                        f"💬 {format_number(v['comment_count'])} comentários\n\n"
                        f"🔗 [Ver no TikTok]({v['url']})"
                    )
                    
                    if v.get('cover'):
                        try:
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=v['cover'],
                                caption=caption,
                                parse_mode='Markdown',
                                reply_markup=reply_markup
                            )
                        except Exception:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text=caption,
                                parse_mode='Markdown',
                                reply_markup=reply_markup,
                                disable_web_page_preview=False
                            )
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"Error sending video {i}: {e}")
                    continue
        
    except Exception as e:
        logger.error(f"Error in analisar: {e}")
        await status_msg.edit_text(
            "❌ Ocorreu um erro ao analisar o creator.\n\n"
            "Tente novamente mais tarde.",
            parse_mode='Markdown'
        )


async def musicas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows trending sounds/music on TikTok."""
    from downloader import get_trending_sounds
    
    category = 'all'
    if context.args:
        category = context.args[0].lower()
    
    status_msg = await update.message.reply_text(
        "🎵 Buscando trending sounds...\n\nAguarde! ⏳",
        parse_mode='Markdown'
    )
    
    try:
        # Fetch trending sounds
        loop = asyncio.get_running_loop()
        sounds = await loop.run_in_executor(None, get_trending_sounds, category, 15)
        
        if not sounds:
            await status_msg.edit_text(
                "❌ Não foi possível buscar trending sounds.\n\n"
                "Tente novamente mais tarde.",
                parse_mode='Markdown'
            )
            return
        
        # Build message
        message = "🎵 *Trending Sounds no TikTok*\n\n"
        
        for i, sound in enumerate(sounds[:10], 1):
            # Truncate title if too long
            title = sound['title'][:40] + "..." if len(sound['title']) > 40 else sound['title']
            author = sound['author'][:30] + "..." if len(sound['author']) > 30 else sound['author']
            
            message += (
                f"{i}. *{title}*\n"
                f"   🎤 {author}\n"
                f"   📊 {sound['usage_count']} vídeos\n"
                f"   {sound['status']}\n\n"
            )
        
        message += (
            "\n💡 *Dica:* Sons com status 🔥 VIRAL têm\n"
            "maior chance de impulsionar seu vídeo!"
        )
        
        await status_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in musicas: {e}")
        await status_msg.edit_text(
            "❌ Ocorreu um erro ao buscar trending sounds.\n\n"
            "Tente novamente mais tarde.",
            parse_mode='Markdown'
        )


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
    tendencias_handler = CommandHandler('tendencias', tendencias)
    analisar_handler = CommandHandler('analisar', analisar)
    musicas_handler = CommandHandler('musicas', musicas)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    
    # Callback handlers for buttons
    viral_callback_handler = CallbackQueryHandler(viral_callback, pattern='^viral_')
    download_callback_handler = CallbackQueryHandler(download_callback, pattern='^download_')
    filter_callback_handler = CallbackQueryHandler(viral_filter_callback, pattern='^filter_')

    application.add_handler(start_handler)
    application.add_handler(viral_handler)
    application.add_handler(tendencias_handler)
    application.add_handler(analisar_handler)
    application.add_handler(musicas_handler)
    application.add_handler(viral_callback_handler)
    application.add_handler(filter_callback_handler)
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
