import os
import logging
import uuid
import yt_dlp
from typing import Optional

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class DownloadError(Exception):
    """Custom exception for download errors"""
    pass

def download_video(url: str) -> str:
    """
    Downloads a video from Instagram or TikTok using yt-dlp.
    Returns the path to the downloaded file.
    Raises DownloadError if download fails.
    
    Args:
        url: URL of the video to download
        
    Returns:
        str: Path to the downloaded video file
    """
    
    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    output_template = f"downloads/{unique_id}.%(ext)s"
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'best',  # Download best quality
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.instagram.com/',
    }
    
    # Platform-specific configurations
    if "instagram.com" in url:
        logger.info(f"Detected Instagram URL: {url}")
        ydl_opts.update({
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.instagram.com/',
            }
        })
    elif "tiktok.com" in url:
        logger.info(f"Detected TikTok URL: {url}")
        ydl_opts.update({
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
            }
        })
    else:
        raise DownloadError("URL não suportada. Apenas Instagram e TikTok são suportados.")
    
    try:
        logger.info(f"Starting download from: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to check if video is available
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise DownloadError("Não foi possível extrair informações do vídeo. Verifique se o link é válido e público.")
            
            logger.info(f"Video info extracted: {info.get('title', 'Unknown')}")
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file
            expected_filename = f"downloads/{unique_id}.mp4"
            
            # Check for various possible extensions
            possible_extensions = ['.mp4', '.webm', '.mkv', '.mov']
            downloaded_file = None
            
            for ext in possible_extensions:
                test_file = f"downloads/{unique_id}{ext}"
                if os.path.exists(test_file):
                    downloaded_file = test_file
                    break
            
            if not downloaded_file:
                # Try to find any file with the unique_id
                for file in os.listdir("downloads"):
                    if unique_id in file:
                        downloaded_file = os.path.join("downloads", file)
                        break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise DownloadError("O arquivo não foi encontrado após o download.")
            
            file_size = os.path.getsize(downloaded_file)
            logger.info(f"Video downloaded successfully: {downloaded_file} ({file_size} bytes)")
            
            if file_size < 1000:  # Less than 1KB, probably an error
                os.remove(downloaded_file)
                raise DownloadError("Arquivo baixado é muito pequeno, provavelmente inválido.")
            
            return downloaded_file
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"yt-dlp download error: {error_msg}")
        
        # Provide more specific error messages
        if "Private video" in error_msg or "private" in error_msg.lower():
            raise DownloadError("Este vídeo é privado e não pode ser baixado.")
        elif "not available" in error_msg.lower():
            raise DownloadError("Este vídeo não está disponível. Pode ter sido removido ou está privado.")
        elif "login" in error_msg.lower() or "sign in" in error_msg.lower():
            raise DownloadError("Este vídeo requer login. Apenas vídeos públicos podem ser baixados.")
        else:
            raise DownloadError(f"Erro ao baixar o vídeo: {error_msg}")
            
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        raise DownloadError(f"Erro inesperado: {str(e)}")


def download_instagram_alternative(url: str) -> str:
    """
    Alternative method to download Instagram videos using API fallbacks.
    This is a backup method if yt-dlp fails.
    
    Args:
        url: Instagram video URL
        
    Returns:
        str: Path to the downloaded video file
    """
    import requests
    import re
    
    logger.info(f"Trying alternative Instagram download method for: {url}")
    
    # Method 1: Try SnapInsta API
    try:
        api_url = "https://snapinsta.app/api/ajaxSearch"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        data = {
            'q': url,
            'lang': 'en'
        }
        
        response = requests.post(api_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'ok':
                html = result.get('data', '')
                
                # Look for video download link
                patterns = [
                    r'href="([^"]+)"[^>]*class="[^"]*download[^"]*"',
                    r'<a[^>]+href="([^"]+)"[^>]*>\s*Download',
                    r'href="(https://[^"]+\.cdninstagram\.com[^"]+)"',
                    r'href="(https://scontent[^"]+)"'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        video_url = match.group(1)
                        if 'cdninstagram' in video_url or 'scontent' in video_url:
                            return _download_from_direct_url(video_url, "instagram")
    except Exception as e:
        logger.warning(f"SnapInsta API failed: {e}")
    
    raise DownloadError("Método alternativo de download também falhou.")


def download_tiktok_alternative(url: str) -> str:
    """
    Alternative method to download TikTok videos using API fallbacks.
    This is a backup method if yt-dlp fails.
    
    Args:
        url: TikTok video URL
        
    Returns:
        str: Path to the downloaded video file
    """
    import requests
    import re
    
    logger.info(f"Trying alternative TikTok download method for: {url}")
    
    # Method 1: Try TikWM API
    try:
        api_url = "https://www.tikwm.com/api/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        params = {
            'url': url,
            'hd': '1'
        }
        
        response = requests.post(api_url, headers=headers, data=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                
                # Try HD video first, then fall back to regular
                video_url = data.get('hdplay') or data.get('play')
                
                if video_url:
                    logger.info(f"Found TikTok video URL via TikWM API")
                    return _download_from_direct_url(video_url, "tiktok")
    except Exception as e:
        logger.warning(f"TikWM API failed: {e}")
    
    # Method 2: Try SnapTik API
    try:
        api_url = "https://snaptik.app/abc2.php"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        data = {
            'url': url,
            'lang': 'en'
        }
        
        response = requests.post(api_url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            html = response.text
            
            # Look for video download link
            patterns = [
                r'href="([^"]+)"[^>]*class="[^"]*download[^"]*"',
                r'<a[^>]+href="([^"]+)"[^>]*>\s*Download',
                r'href="(https://[^"]+\.tiktokcdn\.com[^"]+)"',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    video_url = match.group(1)
                    if 'tiktokcdn' in video_url or 'tiktok' in video_url:
                        logger.info(f"Found TikTok video URL via SnapTik API")
                        return _download_from_direct_url(video_url, "tiktok")
    except Exception as e:
        logger.warning(f"SnapTik API failed: {e}")
    
    raise DownloadError("Método alternativo de download também falhou.")


def _download_from_direct_url(video_url: str, platform: str) -> str:
    """
    Download video from a direct URL.
    
    Args:
        video_url: Direct URL to the video file
        platform: Platform name (for filename)
        
    Returns:
        str: Path to the downloaded video file
    """
    import requests
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.instagram.com/' if platform == 'instagram' else 'https://www.tiktok.com/'
        }
        
        logger.info(f"Downloading video from direct URL: {video_url[:100]}...")
        
        video_response = requests.get(video_url, headers=headers, timeout=120, stream=True)
        video_response.raise_for_status()
        
        # Save to file
        os.makedirs("downloads", exist_ok=True)
        filename = f"downloads/{uuid.uuid4()}_{platform}.mp4"
        
        with open(filename, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(filename)
        logger.info(f"Video downloaded successfully: {filename} ({file_size} bytes)")
        
        if file_size < 1000:  # Less than 1KB, probably an error
            os.remove(filename)
            raise DownloadError("Arquivo baixado é muito pequeno, provavelmente inválido.")
        
        return filename
        
    except Exception as e:
        logger.error(f"Error downloading from direct URL: {e}")
        raise DownloadError(f"Erro ao baixar do URL direto: {str(e)}")




def search_tiktok_by_hashtag(hashtag: str, limit: int = 15, region: str = 'US', sort_by: str = 'likes') -> list:
    """
    Searches TikTok videos by hashtag.
    
    Args:
        hashtag: Hashtag to search for (with or without #)
        limit: Number of videos to return
        region: Region code (e.g. 'BR', 'US'). Defaults to 'US' (Global/International).
        sort_by: Sort criteria - 'likes', 'views', or 'date'
        
    Returns:
        list: List of dictionaries with video info
    """
    import requests
    from datetime import datetime
    
    # Clean hashtag (remove # if present)
    hashtag = hashtag.strip().lstrip('#')
    
    logger.info(f"Searching TikTok for #{hashtag} (limit={limit}, region={region}, sort={sort_by})")
    
    try:
        # TikWM Search API
        api_url = "https://www.tikwm.com/api/feed/search"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        # Request more videos to allow for filtering
        params = {
            'keywords': f'#{hashtag}',
            'count': 100,  # Request more to ensure we have enough after filtering
            'region': region
        }
        
        response = requests.post(api_url, headers=headers, data=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"TikWM API error: {response.status_code}")
            return []
            
        result = response.json()
        if result.get('code') != 0:
            logger.error(f"TikWM API returned error code: {result.get('msg')}")
            return []
            
        videos = result.get('data', {}).get('videos', [])
        
        if not videos:
            logger.warning(f"No videos found for #{hashtag}")
            return []
        
        # Process video data
        processed_videos = []
        for v in videos:
            video_data = {
                'title': v.get('title', 'Sem título'),
                'play_count': v.get('play_count', 0),
                'digg_count': v.get('digg_count', 0),
                'author': v.get('author', {}).get('nickname', 'Desconhecido'),
                'url': f"https://www.tiktok.com/@{v.get('author', {}).get('unique_id', 'user')}/video/{v.get('video_id')}",
                'cover': v.get('cover', ''),
                'create_time': v.get('create_time', 0)
            }
            processed_videos.append(video_data)
        
        # Sort based on criteria
        if sort_by == 'likes':
            processed_videos.sort(key=lambda x: x['digg_count'], reverse=True)
        elif sort_by == 'views':
            processed_videos.sort(key=lambda x: x['play_count'], reverse=True)
        elif sort_by == 'date':
            processed_videos.sort(key=lambda x: x['create_time'], reverse=True)
        else:
            # Default to likes
            processed_videos.sort(key=lambda x: x['digg_count'], reverse=True)
        
        logger.info(f"Found {len(processed_videos)} videos for #{hashtag}")
        return processed_videos[:limit]
        
    except Exception as e:
        logger.error(f"Error searching for #{hashtag}: {e}")
        return []


def get_tiktok_trending(limit: int = 15, days: int = 5, region: str = 'US') -> list:

    """
    Fetches trending TikTok videos.
    Filters by last N days and returns top N videos.
    
    Args:
        limit: Number of videos to return
        days: How many days back to look
        region: Region code (e.g. 'BR', 'US'). Defaults to 'US' (Global/International).
        
    Returns:
        list: List of dictionaries with video info
    """
    import requests
    import time
    from datetime import datetime, timedelta
    
    logger.info(f"Fetching trending TikTok videos (limit={limit}, days={days}, region={region})")
    
    try:
        # TikWM Feed API
        api_url = "https://www.tikwm.com/api/feed/list"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        # Request more videos to allow for filtering
        params = {
            'region': region,
            'count': 200  # Increased to ensure we get enough videos
        }
        
        response = requests.post(api_url, headers=headers, data=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"TikWM API error: {response.status_code}")
            return []
            
        result = response.json()
        if result.get('code') != 0:
            logger.error(f"TikWM API returned error code: {result.get('msg')}")
            return []
            
        videos = result.get('data', [])
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        filtered_videos = []
        all_videos = []  # Fallback without date filter
        
        for v in videos:
            video_data = {
                'title': v.get('title', 'Sem título'),
                'play_count': v.get('play_count', 0),
                'digg_count': v.get('digg_count', 0),
                'author': v.get('author', {}).get('nickname', 'Desconhecido'),
                'url': f"https://www.tiktok.com/@{v.get('author', {}).get('unique_id', 'user')}/video/{v.get('video_id')}",
                'cover': v.get('cover', '')
            }
            all_videos.append(video_data)
            
            # create_time is unix timestamp
            create_time = v.get('create_time', 0)
            if create_time >= cutoff_timestamp:
                filtered_videos.append(video_data)
        
        # Sort by digg_count (likes) descending
        filtered_videos.sort(key=lambda x: x['digg_count'], reverse=True)
        all_videos.sort(key=lambda x: x['digg_count'], reverse=True)
        
        # If we don't have enough filtered videos, use all videos
        if len(filtered_videos) < limit:
            logger.warning(f"Only {len(filtered_videos)} videos in last {days} days, using all trending videos")
            return all_videos[:limit]
        
        return filtered_videos[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching trending videos: {e}")
        return []
