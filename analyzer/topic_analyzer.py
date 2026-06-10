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
#  Predefined Topic Taxonomy
#  Each topic has a name and a set of keywords/phrases that signal it.
# -----------------------------------------------------------------

TOPIC_TAXONOMY = {
    "Fitness & Gym": {
        "keywords": [
            "gym", "workout", "fitness", "exercise", "lift", "weight",
            "muscle", "protein", "bulk", "cut", "cardio", "crossfit",
            "bodybuilding", "deadlift", "squat", "bench", "gains",
            "shred", "abs", "bicep", "tricep", "leg day", "chest",
            "shoulder", "back", "transform", "fit", "healthy",
            "strength", "training", "reps", "sets", "pr", "personal record",
        ],
        "hashtags": [
            "gym", "fitness", "workout", "fitfam", "gymmotivation",
            "fitnessmotivation", "bodybuilding", "gymlife", "gains",
            "legday", "chestday", "armday", "personalrecord",
        ],
    },
    "Love & Relationships": {
        "keywords": [
            "love", "heart", "bae", "relationship", "couple", "date",
            "romance", "crush", "soulmate", "partner", "wife", "husband",
            "boyfriend", "girlfriend", "marry", "wedding", "forever",
            "miss", "hug", "kiss", "care", "feeling", "emotion",
            "breakup", "heal", "toxic", "red flag", "trust",
            "loyalty", "commitment",
        ],
        "hashtags": [
            "love", "couplegoals", "relationship", "lovequotes",
            "romance", "bae", "forever", "truelove", "heartbreak",
            "couple", "lovers", "soulmate",
        ],
    },
    "College & Student Life": {
        "keywords": [
            "college", "university", "exam", "study", "student",
            "semester", "lecture", "professor", "campus", "hostel",
            "class", "assignment", "degree", "engineering", "btech",
            "mba", "placement", "intern", "topper", "backlog",
            "attendance", "project", "viva", "lab", "library",
            "canteen", "fest", "fresher",
        ],
        "hashtags": [
            "college", "collegelife", "student", "studentlife",
            "exam", "study", "engineering", "campus", "hostel",
            "placement", "btech", "university",
        ],
    },
    "Humor & Memes": {
        "keywords": [
            "meme", "funny", "lol", "lmao", "rofl", "joke", "humor",
            "comedy", "laugh", "hilarious", "savage", "sarcasm",
            "trolling", "relatable", "dank", "shitpost",
        ],
        "hashtags": [
            "meme", "memes", "funny", "humor", "comedy", "lol",
            "dankmemes", "funnymemes", "memesdaily", "joke",
            "sarcasm", "savage", "relatable",
        ],
    },
    "Cricket & Sports": {
        "keywords": [
            "cricket", "ipl", "t20", "odi", "test match", "world cup",
            "batsman", "bowler", "wicket", "century", "six", "four",
            "innings", "pitch", "stadium", "dhoni", "virat", "kohli",
            "rohit", "sachin", "rcb", "csk", "mi", "kkr",
            "sport", "football", "soccer", "basketball", "tennis",
            "match", "team", "player", "goal", "score", "win",
            "champion", "league", "tournament", "final",
        ],
        "hashtags": [
            "cricket", "ipl", "t20", "worldcup", "dhoni", "virat",
            "kohli", "rcb", "csk", "sports", "football", "basketball",
            "tennis", "fifa", "nba", "match",
        ],
    },
    "Movies & Entertainment": {
        "keywords": [
            "movie", "film", "bollywood", "hollywood", "netflix",
            "series", "show", "actor", "actress", "director", "scene",
            "dialogue", "trailer", "review", "rating", "oscar",
            "award", "release", "theater", "cinema", "ott",
            "amazon prime", "hotstar", "drama", "thriller",
            "action", "horror", "comedy", "anime", "kdrama",
            "webseries", "binge", "watch",
        ],
        "hashtags": [
            "movie", "bollywood", "hollywood", "netflix", "film",
            "cinema", "webseries", "anime", "kdrama", "ott",
            "amazonprime", "hotstar", "bingewatch",
        ],
    },
    "Music": {
        "keywords": [
            "music", "song", "sing", "singer", "rapper", "rap",
            "album", "track", "beat", "melody", "lyric", "concert",
            "spotify", "playlist", "tune", "bass", "guitar", "piano",
            "drum", "vocal", "band", "dj", "edm", "hiphop",
            "pop", "rock", "classical", "indie", "lofi",
        ],
        "hashtags": [
            "music", "song", "singer", "spotify", "hiphop", "rap",
            "edm", "rock", "pop", "indie", "lofi", "playlist",
            "concert", "newmusic", "musiclover",
        ],
    },
    "Food & Cooking": {
        "keywords": [
            "food", "recipe", "cook", "kitchen", "eat", "restaurant",
            "cafe", "dish", "meal", "breakfast", "lunch", "dinner",
            "snack", "dessert", "cake", "pizza", "burger", "biryani",
            "pasta", "sushi", "vegan", "vegetarian", "spicy",
            "delicious", "yummy", "tasty", "chef", "bake",
            "street food", "homemade", "foodie",
        ],
        "hashtags": [
            "food", "foodie", "recipe", "cooking", "chef", "yummy",
            "delicious", "homemade", "streetfood", "biryani",
            "foodporn", "instafood", "foodstagram", "baking",
        ],
    },
    "Travel & Adventure": {
        "keywords": [
            "travel", "trip", "vacation", "holiday", "adventure",
            "explore", "wander", "backpack", "trek", "hike",
            "mountain", "beach", "island", "road trip", "flight",
            "hotel", "resort", "camping", "nature", "sunset",
            "sunrise", "view", "landscape", "destination",
            "passport", "tourist", "solo travel",
        ],
        "hashtags": [
            "travel", "wanderlust", "adventure", "explore",
            "travelgram", "vacation", "trip", "nature", "beach",
            "mountain", "hiking", "backpacking", "solotravel",
            "roadtrip", "sunset", "traveldiaries",
        ],
    },
    "Technology & Coding": {
        "keywords": [
            "tech", "technology", "code", "coding", "programming",
            "developer", "software", "app", "web", "python", "java",
            "javascript", "react", "ai", "artificial intelligence",
            "machine learning", "data science", "startup", "gadget",
            "phone", "laptop", "computer", "hack", "cyber",
            "blockchain", "crypto", "cloud", "devops", "github",
            "linux", "open source",
        ],
        "hashtags": [
            "tech", "coding", "programming", "developer", "python",
            "javascript", "ai", "machinelearning", "datascience",
            "startup", "gadgets", "cyber", "blockchain", "github",
            "webdev", "software", "linux",
        ],
    },
    "Fashion & Style": {
        "keywords": [
            "fashion", "style", "outfit", "wear", "dress", "clothes",
            "brand", "designer", "model", "runway", "trend", "ootd",
            "accessory", "shoe", "sneaker", "watch", "sunglasses",
            "jacket", "hoodie", "jeans", "streetwear", "luxury",
            "aesthetic", "drip", "swag",
        ],
        "hashtags": [
            "fashion", "style", "ootd", "outfit", "streetwear",
            "sneakers", "luxury", "model", "trend", "aesthetic",
            "fashionista", "drip",
        ],
    },
    "Motivation & Self-Improvement": {
        "keywords": [
            "motivation", "inspire", "grind", "hustle", "success",
            "goal", "dream", "mindset", "discipline", "focus",
            "believe", "achieve", "never give up", "hard work",
            "quote", "sigma", "alpha", "stoic", "level up",
            "growth", "potential", "confidence", "self love",
            "mental health", "meditate", "journal", "habit",
            "productivity", "morning routine", "positive",
        ],
        "hashtags": [
            "motivation", "inspiration", "grind", "hustle",
            "success", "mindset", "discipline", "quotes",
            "motivationalquotes", "sigma", "selfimprovement",
            "growthmindset", "nevergiveup", "believe",
        ],
    },
    "Gaming": {
        "keywords": [
            "game", "gaming", "gamer", "play", "stream", "twitch",
            "console", "pc", "ps5", "xbox", "nintendo", "esport",
            "valorant", "fortnite", "minecraft", "gta", "cod",
            "pubg", "bgmi", "freefire", "rpg", "fps", "mmorpg",
            "level", "rank", "clutch", "headshot", "noob", "pro",
        ],
        "hashtags": [
            "gaming", "gamer", "ps5", "xbox", "valorant", "fortnite",
            "minecraft", "gta", "pubg", "bgmi", "esports",
            "pcgaming", "twitch", "streamer",
        ],
    },
    "Photography & Art": {
        "keywords": [
            "photo", "photography", "camera", "portrait", "landscape",
            "shoot", "edit", "lightroom", "photoshop", "lens",
            "dslr", "mirrorless", "art", "artist", "draw", "paint",
            "sketch", "illustration", "design", "creative",
            "digital art", "canvas", "gallery", "exhibition",
        ],
        "hashtags": [
            "photography", "photo", "portrait", "landscape",
            "photographer", "art", "artist", "drawing", "painting",
            "digitalart", "creative", "design", "sketch",
        ],
    },
    "Politics & Current Affairs": {
        "keywords": [
            "politics", "election", "government", "minister",
            "parliament", "democracy", "vote", "policy", "law",
            "protest", "rally", "party", "congress", "bjp",
            "modi", "opposition", "debate", "economy", "budget",
            "tax", "inflation", "corruption", "news", "breaking",
        ],
        "hashtags": [
            "politics", "election", "government", "news",
            "currentaffairs", "breaking", "democracy",
        ],
    },
    "Pets & Animals": {
        "keywords": [
            "dog", "cat", "pet", "puppy", "kitten", "animal",
            "adopt", "rescue", "breed", "walk", "vet", "cute",
            "pawsome", "fur", "tail", "bark", "meow",
        ],
        "hashtags": [
            "dog", "cat", "pet", "puppy", "kitten", "dogsofinstagram",
            "catsofinstagram", "cute", "petlover", "adopt",
        ],
    },
}


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

    for topic_name, topic_data in TOPIC_TAXONOMY.items():
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
    }
