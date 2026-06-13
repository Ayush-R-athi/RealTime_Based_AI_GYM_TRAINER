import re
from io import BytesIO
from gtts import gTTS


class TextToSpeech:
    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            return None

        # remove markdown/quotes
        cleaned = re.sub(r'["*_`]', '', cleaned)
        # replace commas with a short pause word so gTTS doesn't cut off
        cleaned = re.sub(r',\s*', '. ', cleaned)
        # collapse multiple spaces
        cleaned = re.sub(r' +', ' ', cleaned).strip()

        buffer = BytesIO()
        gTTS(text=cleaned, lang=lang, slow=False).write_to_fp(buffer)
        buffer.seek(0)

        return buffer.read()
    