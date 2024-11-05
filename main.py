import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import re
from typing import Optional
import pandas as pd
from datetime import datetime
from langchain import hub
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import pyperclip  # For copy to clipboard functionality

# Optional imports for additional features
from io import StringIO
import base64
import json
import os

# Set page config
st.set_page_config(
    page_title="YouTube Transcript To Article",
    page_icon="🎥",
    layout="wide"
)

# Your existing transcript functions here
def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu.be\/)([\w-]+)',
        r'youtube\.com\/embed\/([\w-]+)',
        r'youtube\.com\/v\/([\w-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_transcript(video_url: str, language: str = 'en') -> tuple[list, str]:
    """
    Fetch and format transcript from a YouTube video.
    Returns both raw transcript list and formatted text.
    """
    try:
        video_id = extract_video_id(video_url) or video_url
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        
        # Format transcript with timestamps
        formatted_lines = []
        for entry in transcript_list:
            timestamp = format_timestamp(entry['start'])
            formatted_lines.append(f"[{timestamp}] {entry['text']}")
        
        formatted_text = '\n'.join(formatted_lines)

        llm = ChatOpenAI(model_name="gpt-3.5-turbo")
        prompt = hub.pull("muhsinbashir/youtube-transcript-to-article")
        chain = prompt | llm

        formatted_text = chain.invoke({"transcript": formatted_text}).content

        return transcript_list, formatted_text
    
    except Exception as e:
        error_msg = str(e)
        if "TranscriptsDisabled" in error_msg:
            raise Exception("Transcripts are disabled for this video.")
        elif "NoTranscriptFound" in error_msg:
            raise Exception(f"No transcript found in language '{language}'.")
        raise Exception(f"Error fetching transcript: {error_msg}")

def get_download_link(text: str, filename: str, button_text: str) -> str:
    """Generate a download link for text content."""
    b64 = base64.b64encode(text.encode()).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}">{button_text}</a>'

# Streamlit UI
def main():
    st.title("📝 YouTube Transcript to Article")
    st.write("Enter a YouTube URL to get an article on its content")

    # Input section
    url = st.text_input("YouTube URL")
    language = st.text_input("Language Code (e.g., 'en' for English)", value="en")
    
    openai_api_key = st.text_input("OpenAI API Key")

    os.environ["OPENAI_API_KEY"] = openai_api_key
    if st.button("Get Article"):
        if url:
            try:
                with st.spinner("Writing Article..."):
                    # Get both raw and formatted transcript
                    raw_transcript, formatted_transcript = get_transcript(url, language)
                    
                    # Display transcript
                    st.subheader("Article")
                    st.text_area("", formatted_transcript, height=400)
                    
                    # Create download options
                    col1, col2 = st.columns(2)
                    
                    # Text format download
                    with col1:
                        st.download_button(
                            label="Download as TXT",
                            data=formatted_transcript,
                            file_name="article.txt",
                            mime="text/plain"
                        )
                    
                    # JSON format download
                    with col2:
                        json_transcript = json.dumps(raw_transcript, indent=2)
                        st.download_button(
                            label="Download as JSON",
                            data=json_transcript,
                            file_name="article.json",
                            mime="application/json"
                        )
                    
                    # Create DataFrame for display
                    df = pd.DataFrame(raw_transcript)
                    df['timestamp'] = df['start'].apply(format_timestamp)
                    st.subheader("Article Data")
                    st.dataframe(df[['timestamp', 'text', 'duration']])
                    
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("Please enter a YouTube URL")

if __name__ == "__main__":
    main()