# Real-Time Language Translation App

A powerful web-based application that provides real-time language translation with both voice and text input capabilities. Built with Gradio for an intuitive user interface and powered by OpenAI's Whisper for speech recognition, Google Translate for text translation, and Google Text-to-Speech for audio output.

## Features

### Voice Input
- Record audio directly through your microphone
- Automatic speech recognition using Whisper AI
- Support for 13 different input languages

### Text Input
- Type text directly into the interface
- Clean and intuitive text input field
- Copy-paste functionality

### Multi-Language Support
- **13 Supported Languages:**
  - English, Spanish, French, German, Italian
  - Portuguese, Russian, Japanese, Chinese, Korean
  - Arabic, Hindi, Dutch

### Audio Output
- Text-to-speech conversion of translations
- High-quality audio generation using Google TTS
- Playback controls with download option

### Real-Time Progress
- Visual progress indicators
- Step-by-step process feedback
- Error handling with user-friendly messages

### Modern UI
- Beautiful Poppins font integration
- Responsive design with Gradio Soft theme
- Custom CSS styling with gradient progress bars

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection (required for translation and TTS services)

### Required Dependencies

```bash
pip install gradio
pip install openai-whisper
pip install translate
pip install gtts
```

### Additional System Requirements
- FFmpeg (for audio processing with Whisper)
  - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## Usage

### Running the Application

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Real-Time-Language-Translation-App.git
cd Real-Time-Language-Translation-App
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
gradio simple_vtv.py
```

4. Open your web browser and navigate to:
```
http://localhost:7860
```

### How to Use

1. **Select Input Method:**
   - Choose between "Voice Input" or "Text Input"

2. **For Voice Input:**
   - Click the microphone button to start recording
   - Speak clearly in your chosen input language
   - Click stop when finished

3. **For Text Input:**
   - Type or paste your text in the text field

4. **Select Languages:**
   - Choose your input language from the dropdown
   - Select the target language for translation

5. **Translate:**
   - Click the "Translate" button
   - View the progress bar for real-time updates
   - See the results in both text and audio format

## Technical Architecture

### Core Components

- **Speech Recognition:** OpenAI Whisper (base model)
- **Translation:** Google Translate API via `translate` library
- **Text-to-Speech:** Google Text-to-Speech (gTTS)
- **Web Interface:** Gradio framework
- **Audio Processing:** Temporary file handling for audio I/O

### Key Functions

- `translate_content_with_progress()`: Main translation pipeline with progress tracking
- `audio_transcription()`: Converts audio to text using Whisper
- `text_translation()`: Translates text between languages
- `text_to_speech()`: Converts translated text to audio
- `update_interface()`: Manages UI state changes

## Server Configuration
- **Default Port:** 7860
- **Debug Mode:** Enabled
- **Public Sharing:** Disabled (set `share=True` to enable)

## Error Handling

The application includes comprehensive error handling for:
- Empty or invalid audio files
- Network connectivity issues
- Unsupported languages
- File processing errors
- Translation service failures

## Performance Notes

- **First Run:** Initial model loading may take 30-60 seconds
- **Audio Processing:** Depends on file size and duration
- **Translation Speed:** Typically 1-3 seconds per request
- **Memory Usage:** ~1GB for Whisper base model

## Troubleshooting

### Common Issues

1. **Audio not recording:**
   - Check microphone permissions in your browser
   - Ensure microphone is not used by other applications

2. **Translation errors:**
   - Verify internet connection
   - Check if the selected languages are supported

3. **Audio playback issues:**
   - Ensure browser supports MP3 playback
   - Check system audio settings

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Google Translate](https://translate.google.com) for translation services
- [Google Text-to-Speech](https://cloud.google.com/text-to-speech) for audio generation
- [Gradio](https://gradio.app) for the web interface framework
