import spacy
import whisper
from moviepy import VideoFileClip

# -----------------------------
# Load models
# -----------------------------
nlp = spacy.load("en_core_web_sm")
speech_model = whisper.load_model("base")

# =====================================================
# 1. GRAMMAR-BASED ISL PIPELINE (ROBUST VERSION)
# =====================================================

def process_clause(tokens):
    time_tokens = []
    object_tokens = []
    subject_tokens = []
    verb_tokens = []
    negation_tokens = []
    modifiers = []

    for token in tokens:

        # Time expressions
        if token.ent_type_ in ("DATE", "TIME"):
            time_tokens.append(token.text.upper())

        # Temporal modifiers
        elif token.pos_ in ("ADV", "ADP") and token.text.lower() in (
            "before", "after", "immediately", "now", "later"
        ):
            modifiers.append(token.text.upper())

        # Location / context adverbs (outside, inside, here)
        elif token.pos_ == "ADV":
            object_tokens.append(token.text.upper())

        # Subject (drop dummy 'it')
        elif token.dep_ in ("nsubj", "nsubjpass"):
            if token.text.lower() != "it":
                subject_tokens.append(token.text.upper())

        # Main verb
        elif token.pos_ == "VERB":
            verb_tokens.append(token.lemma_.upper())

        # Object / attribute / adjective
        elif token.dep_ in ("dobj", "pobj", "attr", "acomp"):
            object_tokens.append(token.text.upper())

        # Negation
        elif token.dep_ == "neg":
            negation_tokens.append("NOT")

    # ISL ordering
    return (
        time_tokens +
        modifiers +
        object_tokens +
        subject_tokens +
        verb_tokens +
        negation_tokens
    )


def split_clauses(doc):
    condition_tokens = set()
    main_tokens = set(doc)

    for token in doc:
        # Conditional clause
        if token.dep_ == "advcl":
            for sub in token.subtree:
                condition_tokens.add(sub)
                main_tokens.discard(sub)

        # Explicit "if"
        if token.text.lower() == "if":
            for sub in token.head.subtree:
                condition_tokens.add(sub)
                main_tokens.discard(sub)

    return list(condition_tokens), list(main_tokens)


def english_to_isl(sentence):
    doc = nlp(sentence)

    condition_tokens, main_tokens = split_clauses(doc)

    condition_isl = process_clause(condition_tokens)
    main_isl = process_clause(main_tokens)

    return condition_isl + [","] + main_isl if condition_isl else main_isl

# =====================================================
# 2. VIDEO → AUDIO → TEXT
# =====================================================

def extract_audio_from_video(video_path, audio_path="temp_audio.wav"):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path


def speech_to_text(audio_path):
    result = speech_model.transcribe(audio_path)
    return result["text"]


def video_to_isl(video_path):
    print("\nProcessing video:", video_path)

    audio_path = extract_audio_from_video(video_path)
    print("Audio extracted.")

    text = speech_to_text(audio_path)
    print("Recognized English Text:", text)

    # ✅ Sentence splitting
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]

    all_isl = []

    for s in sentences:
        isl = english_to_isl(s)
        print("\nEnglish Sentence:", s)
        print("ISL Output:", isl)
        all_isl.append(isl)

    return all_isl

# =====================================================
# 3. DEMO
# =====================================================

if __name__ == "__main__":
    video_file = "sample1.mp4"
    video_to_isl(video_file)
