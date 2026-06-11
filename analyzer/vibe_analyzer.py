import re
from collections import Counter

VIBE_LEXICON = {
    "Hype & Energetic": {
        "words": [
            "grind", "beast", "win", "success", "hustle", "power", "workout", "motivation",
            "energy", "strong", "push", "build", "grow", "focus", "dynamic", "champion",
            "conquer", "hard", "goals", "level", "beastmode", "limit", "rise", "achieve",
            "fitness", "gym", "never", "give", "active", "passion"
        ],
        "explanation": "High energy, focused on goals, self-improvement, physical training, and personal motivation."
    },
    "Chill & Relaxed": {
        "words": [
            "chill", "vibe", "relax", "calm", "peace", "nature", "beach", "sunset", "coffee",
            "tea", "weekend", "mood", "aesthetic", "wanderlust", "slow", "simple", "cozy",
            "breeze", "waves", "travel", "scenery", "quiet", "escape", "lazy", "morning",
            "cozy", "satisfying", "peaceful", "flow", "rest"
        ],
        "explanation": "Laidback, appreciative of nature, slow living, aesthetic imagery, and personal peace."
    },
    "Humorous & Witty": {
        "words": [
            "funny", "meme", "joke", "lol", "lmao", "rofl", "comedy", "sarcasm", "haha",
            "laugh", "humor", "crazy", "weird", "epic", "fun", "silly", "prank", "ridiculous",
            "troll", "dumb", "bro", "wtf", "hilarious", "laughing", "relatable", "bruh"
        ],
        "explanation": "Lighthearted, entertaining, sarcastic, and conversational, dominated by memes and comedy."
    },
    "Intellectual & Analytical": {
        "words": [
            "code", "program", "tech", "science", "data", "build", "dev", "github", "study",
            "learn", "book", "reading", "knowledge", "strategy", "analysis", "logic", "smart",
            "developer", "coding", "research", "future", "system", "logic", "engineer",
            "project", "course", "tips", "tutorial", "career", "skills"
        ],
        "explanation": "Analytical, career-oriented, tech-focused, and educational, emphasizing learning and building."
    },
    "Emotional & Empathetic": {
        "words": [
            "love", "heart", "feel", "relationship", "life", "care", "soul", "deep", "sad",
            "happy", "friend", "memory", "miss", "trust", "beauty", "family", "together",
            "heal", "support", "empathy", "hurt", "cry", "broken", "feeling", "blessed",
            "kindness", "people", "forever", "sweet", "smile"
        ],
        "explanation": "Expressive, centered on personal feelings, relationships, friendships, and deep reflection."
    }
}


def analyze_vibe(clean_texts: list[str]) -> dict:
    """
    Analyze the overall vibe and tone of the cleaned texts.
    
    Args:
        clean_texts: List of preprocessed text strings
        
    Returns:
        Dict detailing the dominant vibe, score, description, and raw breakdowns.
    """
    if not clean_texts:
        return {
            "dominant_vibe": "Neutral & Quiet",
            "vibe_score": 0,
            "explanation": "Not enough content to establish a dominant communication vibe.",
            "breakdown": {vibe: 0 for vibe in VIBE_LEXICON}
        }
        
    # Combine texts into a single lowercase bag of words
    full_text = " ".join(clean_texts).lower()
    words = re.findall(r"\b\w+\b", full_text)
    word_counts = Counter(words)
    
    scores = {vibe: 0 for vibe in VIBE_LEXICON}
    total_matches = 0
    
    for vibe, data in VIBE_LEXICON.items():
        vibe_words = data["words"]
        for w in vibe_words:
            count = word_counts.get(w, 0)
            scores[vibe] += count
            total_matches += count
            
    if total_matches == 0:
        # Default fallback if no keywords matched
        return {
            "dominant_vibe": "Chill & Relaxed",
            "vibe_score": 50,
            "explanation": "Communicates in a moderate, everyday conversational style without extreme themes.",
            "breakdown": {vibe: 20 for vibe in VIBE_LEXICON}
        }
        
    # Normalize scores to percentages
    breakdown = {}
    for vibe in scores:
        percentage = round((scores[vibe] / total_matches) * 100)
        breakdown[vibe] = percentage
        
    # Find the dominant vibe
    dominant = max(scores, key=scores.get)
    score = breakdown[dominant]
    explanation = VIBE_LEXICON[dominant]["explanation"]
    
    return {
        "dominant_vibe": dominant,
        "vibe_score": score,
        "explanation": explanation,
        "breakdown": breakdown
    }
