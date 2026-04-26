from flask import Flask, render_template, request, jsonify
import re
import json

app = Flask(__name__)

# Common complex word replacements
WORD_SIMPLIFICATIONS = {
    "utilize": "use", "utilise": "use",
    "approximately": "about", "sufficient": "enough",
    "numerous": "many", "regarding": "about",
    "demonstrate": "show", "facilitate": "help",
    "implement": "use", "subsequently": "then",
    "consequently": "so", "nevertheless": "still",
    "furthermore": "also", "therefore": "so",
    "however": "but", "additionally": "also",
    "obtain": "get", "require": "need",
    "provide": "give", "purchase": "buy",
    "commence": "start", "terminate": "end",
    "endeavour": "try", "endeavor": "try",
    "initiate": "start", "conclude": "end",
    "comprehend": "understand", "attempt": "try",
    "assist": "help", "construct": "build",
    "encounter": "meet", "observe": "see",
    "indicate": "show", "maintain": "keep",
    "modify": "change", "occur": "happen",
    "perform": "do", "permit": "allow",
    "possess": "have", "present": "show",
    "proceed": "go", "receive": "get",
    "remove": "take out", "request": "ask",
    "require": "need", "resolve": "fix",
    "respond": "answer", "retain": "keep",
    "select": "choose", "submit": "send",
    "sufficient": "enough", "suggest": "say",
    "support": "help", "transform": "change",
    "transmit": "send", "utilize": "use",
    "verify": "check", "frequently": "often",
    "immediately": "now", "particularly": "especially",
    "previously": "before", "currently": "now",
    "approximately": "about", "significantly": "a lot",
    "essentially": "mainly", "generally": "usually",
    "potentially": "possibly", "relatively": "fairly",
    "extremely": "very", "absolutely": "completely",
    "definitely": "surely", "obviously": "clearly",
}

# Transition words that help identify sentence boundaries for chunking
SENTENCE_STARTERS = [
    "However", "Furthermore", "Additionally", "Moreover",
    "Therefore", "Consequently", "Nevertheless", "Subsequently",
    "Meanwhile", "Otherwise", "Although", "Because", "Since",
    "While", "Unless", "Until", "When", "If", "As",
]


def split_into_sentences(text):
    """Split text into sentences using regex."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def simplify_words(text):
    """Replace complex words with simpler alternatives."""
    result = text
    for complex_word, simple_word in WORD_SIMPLIFICATIONS.items():
        pattern = re.compile(r'\b' + re.escape(complex_word) + r'\b', re.IGNORECASE)
        def replace_match(m):
            word = m.group(0)
            if word[0].isupper():
                return simple_word.capitalize()
            return simple_word
        result = pattern.sub(replace_match, result)
    return result


def chunk_long_sentence(sentence, max_words=15):
    """Break long sentences into smaller chunks at natural points."""
    words = sentence.split()
    if len(words) <= max_words:
        return [sentence]

    chunks = []
    current_chunk = []

    # Look for natural break points: commas, semicolons, conjunctions
    conjunctions = {'and', 'but', 'or', 'nor', 'so', 'yet', 'for',
                    'because', 'although', 'since', 'while', 'when',
                    'if', 'unless', 'until', 'after', 'before', 'as'}

    for i, word in enumerate(words):
        current_chunk.append(word)
        clean_word = word.lower().rstrip(',.;:')

        # Break at comma/semicolon after enough words, or at conjunction
        if len(current_chunk) >= 8:
            if word.endswith(',') or word.endswith(';'):
                chunks.append(' '.join(current_chunk))
                current_chunk = []
            elif clean_word in conjunctions and i > 0:
                # Put conjunction at start of next chunk
                current_chunk.pop()
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]

        if len(current_chunk) >= max_words:
            chunks.append(' '.join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks if chunks else [sentence]


def count_syllables(word):
    """Rough syllable counter."""
    word = word.lower().strip(".,!?;:'\"")
    if len(word) <= 3:
        return 1
    count = len(re.findall(r'[aeiou]+', word))
    if word.endswith('e'):
        count -= 1
    return max(1, count)


def get_readability_stats(text):
    """Calculate basic readability statistics."""
    sentences = split_into_sentences(text)
    words = re.findall(r'\b\w+\b', text)

    if not sentences or not words:
        return {}

    avg_sentence_length = len(words) / len(sentences)
    avg_syllables = sum(count_syllables(w) for w in words) / len(words)

    # Flesch Reading Ease approximation
    if len(sentences) > 0:
        fre = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables
        fre = max(0, min(100, fre))
    else:
        fre = 0

    long_sentences = [s for s in sentences if len(s.split()) > 20]

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "readability_score": round(fre, 1),
        "long_sentence_count": len(long_sentences),
        "complex_word_count": sum(1 for w in words if len(w) > 8),
    }


def process_text(text, options):
    """Main text processing pipeline."""
    if not text.strip():
        return {"segments": [], "stats": {}, "simplified_text": ""}

    working_text = text

    # Step 1: Simplify words if enabled
    if options.get("simplify_words"):
        working_text = simplify_words(working_text)

    # Step 2: Split into sentences
    sentences = split_into_sentences(working_text)

    # Step 3: Process each sentence
    segments = []
    for sentence in sentences:
        word_count = len(sentence.split())
        is_long = word_count > 20

        if options.get("chunk_sentences") and is_long:
            chunks = chunk_long_sentence(sentence, max_words=int(options.get("chunk_size", 15)))
            for i, chunk in enumerate(chunks):
                segments.append({
                    "text": chunk,
                    "type": "chunk",
                    "is_long": False,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "word_count": len(chunk.split()),
                })
        else:
            segments.append({
                "text": sentence,
                "type": "sentence",
                "is_long": is_long,
                "word_count": word_count,
            })

    # Compute stats on simplified text
    simplified_text = ' '.join(s["text"] for s in segments)
    stats = get_readability_stats(simplified_text)
    original_stats = get_readability_stats(text)

    return {
        "segments": segments,
        "stats": stats,
        "original_stats": original_stats,
        "simplified_text": simplified_text,
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    data = request.get_json()
    text = data.get('text', '')
    options = data.get('options', {})
    result = process_text(text, options)
    return jsonify(result)


@app.route('/simplify_words', methods=['POST'])
def simplify_words_route():
    data = request.get_json()
    text = data.get('text', '')
    result = simplify_words(text)
    return jsonify({"simplified": result})


if __name__ == '__main__':
    app.run(debug=True, port=5000)