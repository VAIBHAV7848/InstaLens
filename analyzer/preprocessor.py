"""
Text preprocessor for Instagram caption/repost content.

Handles:
- Hashtag extraction and CamelCase splitting
- Mention extraction
- URL/emoji removal
- Stopword removal and lemmatization via spaCy
"""

import re
import unicodedata
import spacy

# Load spaCy English model (small, fast)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("[InstaLens] spaCy English model not found. Downloading 'en_core_web_sm'...")
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Custom stopwords common in Instagram/social media
SOCIAL_STOPWORDS = {
    "repost", "share", "follow", "like", "comment", "tag",
    "dm", "link", "bio", "post", "story", "reel", "reels",
    "via", "credit", "source", "original", "pic", "photo",
    "video", "click", "tap", "swipe", "check", "account",
    "page", "trending", "viral", "fyp", "foryou", "foryoupage",
    "explore", "instagood", "instagram", "insta", "instadaily",
    "photooftheday", "picoftheday", "love", "like4like",
    "followme", "follow4follow", "likeforlike", "followforfollow",
    "f4f", "l4l", "instalike", "instaphoto",
}


def extract_hashtags(text: str) -> list[str]:
    """Extract all hashtags from text and return as cleaned list."""
    raw_tags = re.findall(r"#(\w+)", text)
    return [tag.lower() for tag in raw_tags]


def split_camelcase(word: str) -> str:
    """
    Split CamelCase or PascalCase into separate words.
    e.g., 'GymLife' -> 'Gym Life', 'IPLFinal' -> 'IPL Final'
    """
    # Insert space before uppercase letters that follow lowercase
    result = re.sub(r"([a-z])([A-Z])", r"\1 \2", word)
    # Insert space before uppercase letters followed by lowercase (for acronyms)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", result)
    return result


def expand_hashtags(hashtags: list[str]) -> list[str]:
    """Split CamelCase hashtags into readable words."""
    expanded = []
    for tag in hashtags:
        split = split_camelcase(tag)
        expanded.append(split.lower())
    return expanded


def remove_urls(text: str) -> str:
    """Remove URLs from text."""
    return re.sub(r"https?://\S+|www\.\S+", "", text)


def remove_mentions(text: str) -> str:
    """Remove @mentions from text but return them separately."""
    return re.sub(r"@\w+", "", text)


def extract_mentions(text: str) -> list[str]:
    """Extract @mentions from text."""
    return re.findall(r"@(\w+)", text)


def remove_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    return "".join(
        char for char in text
        if unicodedata.category(char) not in ("So", "Sk", "Sc")
        or char in ("$", "€", "£", "¥")
    )


def remove_special_chars(text: str) -> str:
    """Remove special characters, keeping alphanumeric and spaces."""
    return re.sub(r"[^a-zA-Z0-9\s]", " ", text)


def lemmatize_and_clean(text: str) -> list[str]:
    """
    Process text through spaCy: tokenize, lemmatize, remove stopwords.
    Returns list of clean lemmatized tokens.
    """
    doc = nlp(text.lower())
    tokens = []
    for token in doc:
        # Skip stopwords, punctuation, spaces, and very short tokens
        if (
            token.is_stop
            or token.is_punct
            or token.is_space
            or len(token.lemma_) < 2
            or token.lemma_ in SOCIAL_STOPWORDS
        ):
            continue
        tokens.append(token.lemma_)
    return tokens


def extract_entities(text: str) -> list[dict]:
    """
    Extract named entities from text using spaCy NER.
    Returns list of dicts with 'text' and 'label' keys.
    """
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "WORK_OF_ART", "PRODUCT", "NORP"):
            entities.append({"text": ent.text, "label": ent.label_})
    return entities


def preprocess(raw_text: str) -> dict:
    """
    Full preprocessing pipeline for Instagram text content.

    Args:
        raw_text: Raw caption/repost text (can include hashtags, mentions, URLs)

    Returns:
        dict with keys:
            - clean_text: Cleaned, readable text
            - tokens: List of lemmatized tokens
            - hashtags: List of raw hashtags (lowercase)
            - expanded_hashtags: Hashtags split from CamelCase
            - mentions: List of @mentions
            - entities: Named entities found
    """
    # Step 1: Extract structured elements before cleaning
    hashtags = extract_hashtags(raw_text)
    expanded_hashtags = expand_hashtags(hashtags)
    mentions = extract_mentions(raw_text)
    entities = extract_entities(raw_text)

    # Step 2: Clean the text
    text = remove_urls(raw_text)
    text = remove_mentions(text)
    text = re.sub(r"#\w+", "", text)  # Remove hashtag symbols
    text = remove_emojis(text)
    text = remove_special_chars(text)
    text = re.sub(r"\s+", " ", text).strip()  # Collapse whitespace

    # Step 3: Lemmatize and tokenize
    tokens = lemmatize_and_clean(text)

    # Step 4: Also tokenize the expanded hashtags and add to tokens
    hashtag_text = " ".join(expanded_hashtags)
    hashtag_tokens = lemmatize_and_clean(hashtag_text)
    all_tokens = tokens + hashtag_tokens

    return {
        "clean_text": text,
        "tokens": all_tokens,
        "hashtags": hashtags,
        "expanded_hashtags": expanded_hashtags,
        "mentions": mentions,
        "entities": entities,
    }


def preprocess_multiple(texts: list[str]) -> dict:
    """
    Preprocess multiple text chunks and aggregate results.

    Args:
        texts: List of caption/repost text strings

    Returns:
        Aggregated preprocessing results
    """
    all_tokens = []
    all_hashtags = []
    all_expanded = []
    all_mentions = []
    all_entities = []
    all_clean = []

    for text in texts:
        if not text or not text.strip():
            continue
        result = preprocess(text)
        all_tokens.extend(result["tokens"])
        all_hashtags.extend(result["hashtags"])
        all_expanded.extend(result["expanded_hashtags"])
        all_mentions.extend(result["mentions"])
        all_entities.extend(result["entities"])
        all_clean.append(result["clean_text"])

    return {
        "clean_texts": all_clean,
        "all_tokens": all_tokens,
        "all_hashtags": all_hashtags,
        "expanded_hashtags": all_expanded,
        "all_mentions": all_mentions,
        "all_entities": all_entities,
    }
