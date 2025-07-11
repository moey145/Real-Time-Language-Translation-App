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

def translate_content_with_progress(audio_file, text_input, input_method, input_language, target_language, progress=gr.Progress()):
    try:
        progress(0.1, desc="Starting translation...")
        time.sleep(0.1)  # Small delay to show progress
        
        # Determine input text based on selected method
        progress(0.2, desc="Processing input...")
        if input_method == "Voice Input":
            if not audio_file:
                return "Error: Please record audio for voice input.", None
            progress(0.3, desc="Transcribing audio...")
            transcription_text = audio_transcription(audio_file, input_language)
            input_source = "Voice Input"
        elif input_method == "Text Input":
            if not text_input or not text_input.strip():
                return "Error: Please enter text for text input.", None
            transcription_text = text_input.strip()
            input_source = "Text Input"
        else:
            return "Error: Please select an input method.", None

        progress(0.5, desc="Preparing translation...")
        # Get language codes
        input_lang_code = LANGUAGE_OPTIONS[input_language]
        target_lang_code = LANGUAGE_OPTIONS[target_language]

        # Skip translation if input and target languages are the same
        if input_language == target_language:
            progress(0.7, desc="Languages are the same, skipping translation...")
            translation = transcription_text
        else:
            progress(0.6, desc="Translating text...")
            # Translate text
            translation = text_translation(transcription_text, input_lang_code, target_lang_code)

        progress(0.8, desc="Generating audio...")
        # Generate audio for translation
        audio_output = text_to_speech(translation, target_lang_code)

        progress(0.95, desc="Finalizing results...")
        result_text = f"Original ({input_language}) [{input_source}]: {transcription_text}\n\nTranslation ({target_language}): {translation}"
        
        progress(1.0, desc="Complete!")
        return result_text, audio_output

    except Exception as e:
        print(f"Error in translate_content_with_progress: {e}")
        return f"Error: {str(e)}", None

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

        # Generate audio for translation
        audio_output = text_to_speech(translation, target_lang_code)

        result_text = f"Original ({input_language}) [{input_source}]: {transcription_text}\n\nTranslation ({target_language}): {translation}"
        
        return result_text, audio_output

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

/* Progress bar styling */
.progress-bar {
    background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
    border-radius: 4px !important;
}

/* Footer styling */
.footer {
    text-align: center;
    color: black;
    position: fixed;
    bottom: 55px;
    left: 0;
    width: 100%;
}

.footer h3 {
    margin-bottom: 10px;
    color: black !important;
}

.footer p {
    margin-bottom: 15px;
    color: black !important;
    opacity: 0.8;
}

.footer p a {
    color: black !important;
    text-decoration: none;
    transition: all 0.3s ease;
}

.footer p a:hover {
    text-decoration: underline;
    opacity: 1;
}

.footer-buttons {
    display: flex;
    justify-content: center;
    gap: 15px;
    flex-wrap: wrap;
}

.footer-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: transparent;
    border: 2px solid #ccc;
    border-radius: 50%;
    color: black !important;
    text-decoration: none;
    transition: all 0.3s ease;
}

.footer-btn:hover {
    background: #f0f0f0;
    border-color: #999;
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
    
    # Footer
    gr.HTML("""
    <div class="footer">
        <h3>© 2025 Mohamad Eldhaibi</h3>
        <p><a href="mailto:mohamad.eldhaibi@gmail.com">mohamad.eldhaibi@gmail.com</a></p>
        <div class="footer-buttons">
            <a href="https://github.com/moey145" class="footer-btn" target="_blank" title="GitHub">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.30.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
            </a>
            <a href="https://www.linkedin.com/in/mohamad-eldhaibi-8ba8a42b7" class="footer-btn" target="_blank" title="LinkedIn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
            </a>
            <a href="https://www.mohamadeldhaibi.com" class="footer-btn" target="_blank" title="Website">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                </svg>
            </a>
        </div>
    </div>
    """)
    
    # Event handlers
    input_method.change(
        fn=update_interface,
        inputs=[input_method],
        outputs=[audio_input, text_input]
    )
    
    # Updated function call with progress bar
    translate_btn.click(
        fn=translate_content_with_progress,
        inputs=[audio_input, text_input, input_method, input_language_dropdown, target_language_dropdown],
        outputs=[text_output, audio_output],
        show_progress=True
    )

if __name__ == "__main__":
    demo.launch()