"""
Matchmaker Compatibility Engine
Computes match scores, vibe alignment, shared keywords, and tailored icebreakers.
"""

import math
from typing import Dict, List, Tuple
from .report_generator import CONVERSATION_TEMPLATES, GENERIC_SUGGESTIONS

COMPATIBILITY_TEMPLATES = [
    "Since you both love {shared_topic}, why not ask: \"{template_q}\"",
    "Ask about their interest in {shared_topic_2}: \"{template_q_2}\"",
    "Bridge their passion for {topic_b} with your interest in {topic_a}: \"If you had to combine {topic_a_short} with {topic_b_short}, what would that look like?\"",
    "Ask a fun hypothetical blending {topic_a} and {topic_b}: \"Would you rather do something related to {topic_a_short} or spend a day doing {topic_b_short}?\""
]

def calculate_cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Calculate the cosine similarity between two numeric frequency dict vectors."""
    all_keys = set(vec1.keys()).union(set(vec2.keys()))
    if not all_keys:
        return 0.0
        
    dot_product = sum(vec1.get(k, 0.0) * vec2.get(k, 0.0) for k in all_keys)
    magnitude1 = math.sqrt(sum(val ** 2 for val in vec1.values()))
    magnitude2 = math.sqrt(sum(val ** 2 for val in vec2.values()))
    
    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return 0.0
        
    return dot_product / (magnitude1 * magnitude2)

def calculate_jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate the Jaccard similarity coefficient between two sets."""
    if not set1 and not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def calculate_compatibility(report_a: dict, report_b: dict) -> dict:
    """
    Evaluate compatibility between two generated reports.
    
    Args:
        report_a: Report dictionary for profile A
        report_b: Report dictionary for profile B
        
    Returns:
        Match report containing overall score, breakdowns, testimonials, and icebreakers
    """
    # 1. Topic Similarity
    topics_a = {t["name"]: float(t["confidence"]) for t in report_a.get("top_topics", [])}
    topics_b = {t["name"]: float(t["confidence"]) for t in report_b.get("top_topics", [])}
    topic_sim = calculate_cosine_similarity(topics_a, topics_b)
    
    # 2. Vibe Similarity
    vibe_breakdown_a = report_a.get("vibe", {}).get("breakdown", {})
    vibe_breakdown_b = report_b.get("vibe", {}).get("breakdown", {})
    # Ensure all values are float
    vibe_a = {k: float(v) for k, v in vibe_breakdown_a.items()}
    vibe_b = {k: float(v) for k, v in vibe_breakdown_b.items()}
    vibe_sim = calculate_cosine_similarity(vibe_a, vibe_b)
    
    # 3. Keyword / Hashtag Jaccard Similarity
    kws_a = set(k["word"].lower() for k in report_a.get("repeated_keywords", []))
    kws_b = set(k["word"].lower() for k in report_b.get("repeated_keywords", []))
    hts_a = set(h["tag"].lower().replace("#", "") for h in report_a.get("repeated_hashtags", []))
    hts_b = set(h["tag"].lower().replace("#", "") for h in report_b.get("repeated_hashtags", []))
    
    kw_sim = calculate_jaccard_similarity(kws_a, kws_b)
    ht_sim = calculate_jaccard_similarity(hts_a, hts_b)
    keyword_sim = (kw_sim * 0.6) + (ht_sim * 0.4)
    
    # 4. Overall score (Weighted)
    # If both inputs are blank or have 0 magnitude, fallback to baseline
    topic_score = round(topic_sim * 100, 1)
    vibe_score = round(vibe_sim * 100, 1)
    kw_score = round(keyword_sim * 100, 1)
    
    overall_score = round((topic_score * 0.5) + (vibe_score * 0.3) + (kw_score * 0.2), 1)
    if overall_score == 0.0 and (topics_a or topics_b):
        # Add slight natural randomness if they just don't overlap but aren't empty
        overall_score = 15.4
        
    # 5. Determine Grade and Tier
    if overall_score >= 90:
        tier = "Destined Soulmates 💖"
        tier_desc = "Your profiles align perfectly. You share deep core interests, speak the same vibe, and are highly likely to hit it off immediately."
    elif overall_score >= 75:
        tier = "High Compatibility ✨"
        tier_desc = "Excellent chemistry! You have major overlapping passions and match each other's emotional tone very well."
    elif overall_score >= 50:
        tier = "Good Friends 👍"
        tier_desc = "Solid alignment. You share a few key interests and could have great conversations, though you also have your own distinct styles."
    elif overall_score >= 30:
        tier = "Challenging Alignment ⚡"
        tier_desc = "Opposites attract! Your profiles are quite different. While it might take some work to find common ground, it keeps things interesting."
    else:
        tier = "Low Alignment 🧊"
        tier_desc = "A bit of a mismatch. Your vibes and core interests diverge significantly. You might need to rely on outside topics to start a conversation."
        
    # 6. Extract Overlapping & Unique Interests
    shared_topics = list(set(topics_a.keys()).intersection(set(topics_b.keys())))
    unique_a = list(set(topics_a.keys()).difference(set(topics_b.keys())))
    unique_b = list(set(topics_b.keys()).difference(set(topics_a.keys())))
    
    # 7. Generate Narrative Report
    dom_vibe_a = report_a.get("vibe", {}).get("dominant_vibe", "Unknown")
    dom_vibe_b = report_b.get("vibe", {}).get("dominant_vibe", "Unknown")
    
    if shared_topics:
        shared_str = ", ".join(shared_topics[:3])
        narrative = f"This match is powered by a strong mutual connection to {shared_str}. "
    else:
        narrative = "You don't share many direct topic tags, but opposites often create dynamic partnerships! "
        
    if dom_vibe_a == dom_vibe_b:
        narrative += f"Both profiles project a very similar '{dom_vibe_a}' tone, meaning you communicate on the exact same wavelength."
    else:
        narrative += f"Your vibes blend '{dom_vibe_a}' (Profile A) and '{dom_vibe_b}' (Profile B), creating a complementary energetic balance."

    # 8. Generate Tailored Icebreakers
    icebreakers = []
    
    # Attempt 1: Shared topic questions
    if len(shared_topics) >= 1:
        top_shared = shared_topics[0]
        templates = CONVERSATION_TEMPLATES.get(top_shared, GENERIC_SUGGESTIONS)
        q = templates[0] if templates else GENERIC_SUGGESTIONS[0]
        icebreakers.append(f"Since you both love {top_shared}: \"{q}\"")
        
    if len(shared_topics) >= 2:
        second_shared = shared_topics[1]
        templates2 = CONVERSATION_TEMPLATES.get(second_shared, GENERIC_SUGGESTIONS)
        q2 = templates2[1] if len(templates2) > 1 else (templates2[0] if templates2 else GENERIC_SUGGESTIONS[1])
        icebreakers.append(f"Ask about your shared interest in {second_shared}: \"{q2}\"")
        
    # Attempt 2: Bridge Topic A with Topic B
    top_a_unique = [t for t in report_a.get("top_topics", []) if t["name"] not in shared_topics]
    top_b_unique = [t for t in report_b.get("top_topics", []) if t["name"] not in shared_topics]
    
    if top_a_unique and top_b_unique:
        ta = top_a_unique[0]["name"]
        tb = top_b_unique[0]["name"]
        
        ta_short = ta.split(" & ")[0].split(" ")[0].lower()
        tb_short = tb.split(" & ")[0].split(" ")[0].lower()
        
        icebreakers.append(
            f"Bridge her interest in {tb} with your interest in {ta}: "
            f"\"If you could create a crossover between {ta_short} and {tb_short}, how would you set that up?\""
        )
        icebreakers.append(
            f"Ask a fun hypothetical: \"Would you rather spend an entire weekend doing activities related to {tb_short}, or deep-dive into {ta_short}?\""
        )
        
    # Fallback if too few icebreakers
    while len(icebreakers) < 3:
        fallback = GENERIC_SUGGESTIONS[len(icebreakers) % len(GENERIC_SUGGESTIONS)]
        icebreakers.append(f"Casual Starter: \"{fallback}\"")
        
    return {
        "overall_compatibility": overall_score,
        "tier": tier,
        "tier_description": tier_desc,
        "narrative": narrative,
        "breakdown": {
            "topics": topic_score,
            "vibes": vibe_score,
            "keywords": kw_score
        },
        "interests": {
            "shared": shared_topics,
            "unique_a": unique_a,
            "unique_b": unique_b
        },
        "icebreakers": icebreakers[:4]
    }
