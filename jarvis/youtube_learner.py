import re
import os
import json
import logging
import tempfile
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    YTDL_AVAILABLE = True
except ImportError:
    YTDL_AVAILABLE = False
    logger.warning("yt-dlp not available. YouTube learning will be limited.")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class VideoInfo:
    video_id: str
    title: str
    description: str
    duration: int
    author: str
    url: str
    thumbnail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoNotes:
    video_id: str
    title: str
    summary: str
    key_points: List[str]
    topics: List[str]
    code_examples: List[Dict[str, str]]
    timestamps: List[Dict[str, Any]]
    full_transcript: str
    learned_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class YouTubeLearner:
    def __init__(self, memory=None, router_client=None):
        self.memory = memory
        self.router_client = router_client
        self.temp_dir = tempfile.gettempdir()
        logger.info("YouTubeLearner initialized")

    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
            r'youtube\.com/shorts/([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_info(self, url: str) -> Optional[VideoInfo]:
        if not YTDL_AVAILABLE:
            logger.error("yt-dlp not available")
            return None
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                logger.error(f"Could not extract video ID from: {url}")
                return None
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return VideoInfo(
                    video_id=video_id,
                    title=info.get('title', 'Unknown'),
                    description=info.get('description', ''),
                    duration=info.get('duration', 0),
                    author=info.get('uploader', 'Unknown'),
                    url=url,
                    thumbnail=info.get('thumbnail'),
                )
        except Exception as e:
            logger.exception(f"Failed to get video info: {e}")
            return None

    def download_audio(self, url: str, output_path: Optional[str] = None) -> Optional[str]:
        if not YTDL_AVAILABLE:
            logger.error("yt-dlp not available")
            return None
        try:
            video_id = self.extract_video_id(url)
            if not output_path:
                output_path = os.path.join(self.temp_dir, f"{video_id}.mp3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': output_path.replace('.mp3', ''),
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if os.path.exists(output_path):
                logger.info(f"Audio downloaded: {output_path}")
                return output_path
            alt_path = output_path.replace('.mp3', '.m4a')
            if os.path.exists(alt_path):
                return alt_path
            return None
        except Exception as e:
            logger.exception(f"Failed to download audio: {e}")
            return None

    def transcribe_audio(self, audio_path: str) -> str:
        try:
            try:
                import whisper
                model = whisper.load_model("base")
                result = model.transcribe(audio_path)
                return result["text"]
            except ImportError:
                logger.error("No transcription service available")
                return "[Transcription not available - local whisper required]"
        except Exception as e:
            logger.exception(f"Transcription failed: {e}")
            return f"[Transcription error: {str(e)}]"

    async def summarize_transcript(self, transcript: str, video_info: VideoInfo) -> VideoNotes:
        if not self.router_client:
            return VideoNotes(
                video_id=video_info.video_id,
                title=video_info.title,
                summary=transcript[:500] + "..." if len(transcript) > 500 else transcript,
                key_points=["Transcription available. AI summarization available."],
                topics=[],
                code_examples=[],
                timestamps=[],
                full_transcript=transcript,
                learned_at=str(asyncio.get_event_loop().time()),
            )

        try:
            system_prompt = """You are an expert at creating structured notes from video transcripts.
Analyze the transcript and create:
1. A concise summary (2-3 sentences)
2. Key points (5-10 bullet points)
3. Topics covered (list of topics)
4. Any code examples found (with language and description)
5. Important timestamps with descriptions

Respond in JSON format:
{
    "summary": "...",
    "key_points": ["...", "..."],
    "topics": ["...", "..."],
    "code_examples": [{"language": "python", "code": "...", "description": "..."}],
    "timestamps": [{"time": "MM:SS", "description": "..."}]
}"""

            response = self.router_client.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Video: {video_info.title}\n\nTranscript:\n{transcript[:15000]}"}
                ],
                response_format={"type": "json_object"}
            )

            result = json.loads(response)

            return VideoNotes(
                video_id=video_info.video_id,
                title=video_info.title,
                summary=result.get("summary", "No summary available"),
                key_points=result.get("key_points", []),
                topics=result.get("topics", []),
                code_examples=result.get("code_examples", []),
                timestamps=result.get("timestamps", []),
                full_transcript=transcript,
                learned_at=str(asyncio.get_event_loop().time()),
            )

        except Exception as e:
            logger.exception(f"Summarization failed: {e}")
            return VideoNotes(
                video_id=video_info.video_id,
                title=video_info.title,
                summary="Error during summarization",
                key_points=[f"Error: {str(e)}"],
                topics=[],
                code_examples=[],
                timestamps=[],
                full_transcript=transcript,
                learned_at=str(asyncio.get_event_loop().time()),
            )

    async def learn_from_video(self, url: str, save_to_memory: bool = True) -> Dict[str, Any]:
        logger.info(f"Starting learning from: {url}")
        video_info = self.get_video_info(url)
        if not video_info:
            return {"success": False, "error": "Could not get video info"}

        logger.info(f"Video: {video_info.title} ({video_info.duration}s)")
        audio_path = self.download_audio(url)
        if not audio_path:
            transcript = await self._get_youtube_transcript(url)
        else:
            transcript = self.transcribe_audio(audio_path)
            try:
                os.remove(audio_path)
            except:
                pass

        if not transcript or transcript.startswith("["):
            return {
                "success": False,
                "error": "Could not get transcript",
                "video_info": video_info.to_dict()
            }

        notes = await self.summarize_transcript(transcript, video_info)

        if save_to_memory and self.memory:
            self._save_to_memory(notes)

        return {
            "success": True,
            "video_info": video_info.to_dict(),
            "notes": notes.to_dict(),
        }

    async def _get_youtube_transcript(self, url: str) -> str:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            video_id = self.extract_video_id(url)
            if video_id:
                ytt_api = YouTubeTranscriptApi()
                try:
                    transcript = ytt_api.fetch(video_id)
                    return " ".join([snippet.text for snippet in transcript])
                except NoTranscriptFound:
                    try:
                        transcript_list = ytt_api.list(video_id)
                        available = transcript_list._manually_created_transcripts or transcript_list._generated_transcripts
                        if available:
                            first_lang = list(available.keys())[0]
                            transcript = ytt_api.fetch(video_id, languages=[first_lang])
                            return " ".join([snippet.text for snippet in transcript])
                    except:
                        pass
        except:
            pass
        return ""

    def _save_to_memory(self, notes: VideoNotes):
        if not self.memory:
            return
        try:
            note_title = f"YouTube: {notes.title}"
            note_content = f"""Video: {notes.title}
Video ID: {notes.video_id}

Summary:
{notes.summary}

Key Points:
{chr(10).join([f"• {point}" for point in notes.key_points])}

Topics: {', '.join(notes.topics)}

Transcript Preview:
{notes.full_transcript[:1000]}...
"""
            self.memory.add_note(note_title, note_content, category="youtube_learning", tags=notes.topics)
            summary = f"Learned from YouTube video: {notes.title}"
            self.memory.save_conversation(summary, topics=notes.topics + ["youtube", "learning"], importance=3)
            logger.info(f"Video notes saved to memory: {notes.title}")
        except Exception as e:
            logger.exception(f"Failed to save to memory: {e}")

    def format_notes_for_display(self, notes: VideoNotes) -> str:
        lines = [
            f"**{notes.title}**",
            "",
            "**Summary:**",
            notes.summary,
            "",
            "**Key Points:**",
        ]
        for point in notes.key_points:
            lines.append(f"  \u2022 {point}")
        if notes.topics:
            lines.extend(["", f"**Topics:** {', '.join(notes.topics)}"])
        if notes.code_examples:
            lines.extend(["", "**Code Examples:**"])
            for example in notes.code_examples:
                lines.append(f"  [{example.get('language', 'code')}] {example.get('description', '')}")
                lines.append(f"  ```{example.get('language', '')}")
                lines.append(f"  {example.get('code', '')}")
                lines.append("  ```")
        if notes.timestamps:
            lines.extend(["", "**Timestamps:**"])
            for ts in notes.timestamps:
                lines.append(f"  {ts.get('time', '')} - {ts.get('description', '')}")
        lines.extend(["", "Notes saved to memory. You can reference this video anytime!"])
        return "\n".join(lines)


youtube_learner: Optional[YouTubeLearner] = None


def init_youtube_learner(memory=None, router_client=None):
    global youtube_learner
    youtube_learner = YouTubeLearner(memory, router_client)
    return youtube_learner


async def learn_from_youtube(url: str, save_to_memory: bool = True) -> Dict[str, Any]:
    if not youtube_learner:
        return {"success": False, "error": "YouTube learner not initialized"}
    return await youtube_learner.learn_from_video(url, save_to_memory)


def tool_youtube_learn(url: str) -> str:
    if not youtube_learner:
        return "YouTube learner not initialized"
    import asyncio
    try:
        result = asyncio.run(learn_from_youtube(url))
        if result["success"]:
            notes = VideoNotes(**result["notes"])
            return youtube_learner.format_notes_for_display(notes)
        return f"Error: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error: {str(e)}"


YOUTUBE_REGISTRY = {
    "youtube_learn": tool_youtube_learn,
}
