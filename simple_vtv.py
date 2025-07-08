import gradio as gr 
import whisper
from translate import Translator

# Load Whisper model (do this once at startup)
model = whisper.load_model("base")

def voice_to_voice(audio_file):
    # Transcribe audio using Whisper
    transcription_text = audio_transcription(audio_file)
    
    # Translate the text
    es_translation = text_translation(transcription_text)
    
    # For now, return the translated text (you can add TTS later)
    return es_translation

def audio_transcription(audio_file):
    # Use Whisper to transcribe audio
    result = model.transcribe(audio_file)
    return result["text"]

def text_translation(text):
    # Translate from English to Spanish
    translator_es = Translator(from_lang="en", to_lang="es")
    es_text = translator_es.translate(text)
    return es_text

def text_to_speech(text):
    # Placeholder - you can add TTS here later
    return text

audio_input = gr.Audio(
    sources=["microphone"],
    type="filepath"
)

demo = gr.Interface(
    fn=voice_to_voice,
    inputs=audio_input,
    outputs=[gr.Textbox(label="Spanish Translation")],  # Changed to text output for now
)

if __name__ == "__main__":
    demo.launch()