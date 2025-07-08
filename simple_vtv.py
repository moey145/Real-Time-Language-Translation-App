import gradio as gr
import whisper
from translate import Translator
from gtts import gTTS
import tempfile
import os
import time

# Load Whisper model (do this once at startup)
model = whisper.load_model("base")

# Language options for translation
LANGUAGE_OPTIONS = {
    "English": "en",
    "Spanish": "es",
    "French": "fr", 
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl"
}

# Whisper language codes (for transcription)
WHISPER_LANG_MAP = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl"
}

def translate_content(audio_file, text_input, input_method, input_language, target_language):
    try:
        # Determine input text based on selected method
        if input_method == "Voice Input":
            if not audio_file:
                return "Error: Please record audio for voice input.", None
            transcription_text = audio_transcription(audio_file, input_language)
            input_source = "Voice Input"
        elif input_method == "Text Input":
            if not text_input or not text_input.strip():
                return "Error: Please enter text for text input.", None
            transcription_text = text_input.strip()
            input_source = "Text Input"
        else:
            return "Error: Please select an input method.", None

        # Get language codes
        input_lang_code = LANGUAGE_OPTIONS[input_language]
        target_lang_code = LANGUAGE_OPTIONS[target_language]

        # Skip translation if input and target languages are the same
        if input_language == target_language:
            translation = transcription_text
        else:
            # Translate text
            translation = text_translation(transcription_text, input_lang_code, target_lang_code)

        # Generate audio for translation (for both voice and text input)
        audio_output = text_to_speech(translation, target_lang_code)

        return f"Original ({input_language}) [{input_source}]: {transcription_text}\n\nTranslation ({target_language}): {translation}", audio_output

    except Exception as e:
        print(f"Error in translate_content: {e}")
        return f"Error: {str(e)}", None

def audio_transcription(audio_file, input_language):
    print(f"Audio file received: {audio_file}")
    if not audio_file or not os.path.exists(audio_file):
        raise ValueError("No valid audio file received. Please check the input.")
    
    # Check if file is not empty
    if os.path.getsize(audio_file) == 0:
        raise ValueError("Audio file is empty.")
    
    # Get Whisper language code
    whisper_lang = WHISPER_LANG_MAP.get(input_language, "en")
    
    # Transcribe with specified language
    result = model.transcribe(audio_file, language=whisper_lang)
    return result["text"]

def text_translation(text, from_lang, to_lang):
    # Skip translation if languages are the same
    if from_lang == to_lang:
        return text
    
    translator = Translator(from_lang=from_lang, to_lang=to_lang)
    translated_text = translator.translate(text)
    return translated_text

def text_to_speech(text, language_code):
    try:
        # Map language codes for gTTS
        gtts_lang_map = {
            "en": "en", "es": "es", "fr": "fr", "de": "de", "it": "it",
            "pt": "pt", "ru": "ru", "ja": "ja", "zh": "zh",
            "ko": "ko", "ar": "ar", "hi": "hi", "nl": "nl"
        }
        
        lang = gtts_lang_map.get(language_code, "en")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()
        
        # Generate speech with gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(temp_file.name)
        
        # Validate the audio file
        if os.path.getsize(temp_file.name) == 0:
            raise ValueError("Generated audio file is empty.")
            
        print(f"gTTS audio generated: {temp_file.name} (size: {os.path.getsize(temp_file.name)} bytes)")
        return temp_file.name
        
    except Exception as e:
        print(f"gTTS Error: {e}")
        return None

def update_interface(input_method):
    """Update interface based on selected input method"""
    if input_method == "Voice Input":
        return gr.update(visible=True), gr.update(visible=False)
    else:  # Text Input
        return gr.update(visible=False), gr.update(visible=True)

# Custom CSS for Poppins font and fixing scroll issues
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

* {
    font-family: 'Poppins', sans-serif !important;
}

.gradio-container {
    font-family: 'Poppins', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
}

label, span {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 600 !important;
}

button {
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
}

input, textarea, select {
    font-family: 'Poppins', sans-serif !important;
}

.markdown {
    font-family: 'Poppins', sans-serif !important;
}

.prose {
    font-family: 'Poppins', sans-serif !important;
}

.block.padded {
    font-family: 'Poppins', sans-serif !important;
}

"""

# Create the Gradio interface with custom theme and CSS
with gr.Blocks(
    theme=gr.themes.Soft(),
    title="Multi-Language Translation App",
    css=custom_css
) as demo:
    gr.Markdown("<h1 style='text-align: center; padding-bottom: 30px; margin-bottom: 20px;'>Multi-Language Translation App</h1>")
    
    with gr.Row():
        with gr.Column():
            # Input method selection
            input_method = gr.Radio(
                choices=["Voice Input", "Text Input"],
                value="Voice Input",
                label="Select Input Method"
            )
            
            # Audio input (visible by default)
            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="Record Your Voice",
                visible=True
            )
            
            # Text input (hidden by default)
            text_input = gr.Textbox(
                placeholder="Type your text here...",
                lines=3,
                label="Enter Text to Translate",
                visible=False
            )
            
            # Language selection
            with gr.Row():
                input_language_dropdown = gr.Dropdown(
                    choices=list(LANGUAGE_OPTIONS.keys()),
                    value="English",
                    label="Input Language"
                )
                target_language_dropdown = gr.Dropdown(
                    choices=list(LANGUAGE_OPTIONS.keys()),
                    value="Spanish",
                    label="Target Language"
                )
            
            translate_btn = gr.Button("Translate", variant="primary", size="lg")
        
        with gr.Column():
            text_output = gr.Textbox(
                label="Translation Result",
                lines=8,
                show_copy_button=True
            )
            
            audio_output = gr.Audio(
                label="Translation Audio",
                type="filepath",
                autoplay=False,
                visible=True
            )
    
    # Event handlers
    input_method.change(
        fn=update_interface,
        inputs=[input_method],
        outputs=[audio_input, text_input]
    )
    
    translate_btn.click(
        fn=translate_content,
        inputs=[audio_input, text_input, input_method, input_language_dropdown, target_language_dropdown],
        outputs=[text_output, audio_output]
    )

if __name__ == "__main__":
    demo.launch(
        share=False,
        debug=True,
        server_port=7860
    )