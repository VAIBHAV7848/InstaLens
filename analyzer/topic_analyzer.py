"""
Core topic analysis engine.

Uses TF-IDF vectorization, keyword frequency analysis, and a predefined
topic taxonomy to identify what an Instagram profile is about.
"""

from collections import Counter
import math

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# -----------------------------------------------------------------
#  Predefined Topic Taxonomy (loaded dynamically from JSON)
# -----------------------------------------------------------------
from .taxonomy_manager import load_taxonomy


def compute_tfidf_keywords(texts: list[str], top_n: int = 30) -> list[tuple[str, float]]:
    """
    Extract top keywords from texts using TF-IDF.

    Args:
        texts: List of cleaned text strings
        top_n: Number of top keywords to return

    Returns:
        List of (keyword, tfidf_score) tuples sorted by score
    """
    if not texts or all(not t.strip() for t in texts):
        return []

    # Filter empty texts
    valid_texts = [t for t in texts if t.strip()]
    if not valid_texts:
        return []

    vectorizer = TfidfVectorizer(
        max_features=200,
        ngram_range=(1, 2),       # Unigrams and bigrams
        min_df=1,
        max_df=0.95,
        stop_words="english",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(valid_texts)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()

    # Average TF-IDF scores across all documents
    avg_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()

    # Get top N
    top_indices = avg_scores.argsort()[::-1][:top_n]
    keywords = [(feature_names[i], float(avg_scores[i])) for i in top_indices if avg_scores[i] > 0]

    return keywords


def analyze_hashtag_frequency(hashtags: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    """
    Count and rank hashtags by frequency.

    Args:
        hashtags: List of hashtag strings (without #)
        top_n: Number of top hashtags to return

    Returns:
        List of (hashtag, count) tuples sorted by frequency
    """
    counter = Counter(hashtags)
    return counter.most_common(top_n)


def classify_topics(
    tokens: list[str],
    hashtags: list[str],
    tfidf_keywords: list[tuple[str, float]],
) -> list[dict]:
    """
    Classify content into topics using the predefined taxonomy.

    Scoring algorithm:
    1. Token match: each token matching a topic keyword adds 1 point
    2. Hashtag match: each hashtag matching a topic hashtag adds 2 points (stronger signal)
    3. TF-IDF keyword match: each TF-IDF keyword matching a topic keyword adds its TF-IDF score
    4. Normalize to percentage

    Args:
        tokens: Lemmatized text tokens
        hashtags: List of hashtags
        tfidf_keywords: TF-IDF extracted keywords with scores

    Returns:
        List of topic dicts sorted by score, each with:
            - name: topic name
            - score: raw score
            - confidence: 0-100 percentage
            - matched_keywords: list of matching keywords
            - matched_hashtags: list of matching hashtags
    """
    token_set = set(tokens)
    hashtag_set = set(hashtags)
    tfidf_dict = {kw: score for kw, score in tfidf_keywords}

    results = []

    taxonomy = load_taxonomy()
    for topic_name, topic_data in taxonomy.items():
        topic_keywords = set(topic_data["keywords"])
        topic_hashtags = set(topic_data["hashtags"])

        # Score from token matches
        matched_kw = token_set & topic_keywords
        token_score = len(matched_kw)

        # Score from hashtag matches (weighted 2x)
        matched_ht = hashtag_set & topic_hashtags
        hashtag_score = len(matched_ht) * 2

        # Score from TF-IDF keyword matches
        tfidf_score = 0
        for kw in tfidf_dict:
            if kw in topic_keywords:
                tfidf_score += tfidf_dict[kw] * 5  # Amplify TF-IDF signal

            # Also check bigram overlap
            kw_parts = kw.split()
            for part in kw_parts:
                if part in topic_keywords:
                    tfidf_score += tfidf_dict[kw] * 2

        total_score = token_score + hashtag_score + tfidf_score

        if total_score > 0:
            results.append({
                "name": topic_name,
                "score": round(total_score, 2),
                "matched_keywords": sorted(matched_kw),
                "matched_hashtags": sorted(matched_ht),
            })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Calculate confidence as percentage of top score
    if results:
        max_score = results[0]["score"]
        # Confidence is based on the absolute strength of the signal
        # More matched keywords = higher confidence
        for r in results:
            # Confidence formula: logistic scaling of raw score
            # This maps scores to a 0-100 range with diminishing returns
            raw_confidence = (1 - math.exp(-r["score"] / 5)) * 100
            r["confidence"] = round(min(raw_confidence, 99), 1)

    return results


def extract_keyword_frequency(tokens: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    """
    Get most frequent meaningful tokens.

    Args:
        tokens: List of lemmatized tokens
        top_n: Number of top keywords to return

    Returns:
        List of (keyword, count) tuples
    """
    counter = Counter(tokens)
    return counter.most_common(top_n)


def analyze(
    tokens: list[str],
    hashtags: list[str],
    clean_texts: list[str],
    entities: list[dict],
) -> dict:
    """
    Run the full analysis pipeline.

    Args:
        tokens: All lemmatized tokens
        hashtags: All extracted hashtags
        clean_texts: All cleaned text strings
        entities: Named entities from NER

    Returns:
        Complete analysis results dict
    """
    # TF-IDF keywords
    tfidf_keywords = compute_tfidf_keywords(clean_texts)

    # Hashtag frequency
    hashtag_freq = analyze_hashtag_frequency(hashtags)

    # Keyword frequency
    keyword_freq = extract_keyword_frequency(tokens)

    # Topic classification
    topics = classify_topics(tokens, hashtags, tfidf_keywords)

    # Entity frequency
    entity_counter = Counter(e["text"] for e in entities)
    top_entities = entity_counter.most_common(10)

    return {
        "topics": topics,
        "tfidf_keywords": tfidf_keywords[:15],
        "keyword_frequency": keyword_freq,
        "hashtag_frequency": hashtag_freq,
        "top_entities": top_entities,
        "clean_texts": clean_texts,
    }
