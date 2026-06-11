"""
Report generator — builds the final structured output from analysis results.

Produces:
- Top topics with confidence scores
- Common interests
- Repeated keywords and hashtags
- Conversation suggestions
- Human-readable summary sentence
"""

import random
from .vibe_analyzer import analyze_vibe


# -----------------------------------------------------------------
#  Conversation suggestion templates per topic
# -----------------------------------------------------------------

CONVERSATION_TEMPLATES = {
    "Fitness & Gym": [
        "What's your current workout split looking like?",
        "Have you tried any new pre-workout supplements lately?",
        "Do you prefer strength training or cardio?",
        "What's your current PR on bench/squat/deadlift?",
        "Are you on a bulk or cut phase right now?",
    ],
    "Love & Relationships": [
        "Do you believe in love at first sight or does it grow over time?",
        "What's your idea of a perfect date?",
        "What's the most romantic gesture you've seen?",
        "Do you think long-distance relationships can work?",
    ],
    "College & Student Life": [
        "What are you studying, and how's the semester going?",
        "Any college fest coming up that you're excited about?",
        "How do you balance academics and fun in college?",
        "What's the best thing about your campus life?",
    ],
    "Humor & Memes": [
        "What's the funniest meme you've seen recently?",
        "Do you have a favorite meme page you follow?",
        "What kind of humor do you vibe with the most — sarcastic, absurd, or relatable?",
        "Have you ever made a meme that went viral?",
    ],
    "Cricket & Sports": [
        "Who are you supporting in the IPL this season?",
        "Who's your all-time favorite cricketer?",
        "Did you catch the last match? That ending was insane!",
        "Do you play any sports yourself, or just follow?",
    ],
    "Movies & Entertainment": [
        "What's the last movie or series you binge-watched?",
        "Are you more of a Bollywood or Hollywood person?",
        "Any hidden gem shows you'd recommend?",
        "What genre of movies do you enjoy the most?",
    ],
    "Music": [
        "What are you listening to these days?",
        "Do you play any musical instruments?",
        "What's your go-to playlist vibe — chill, hype, or sad?",
        "Have you been to any live concerts recently?",
    ],
    "Food & Cooking": [
        "What's your favorite cuisine to eat or cook?",
        "Do you know any hidden gem restaurants nearby?",
        "Are you a street food person or a fine dining person?",
        "What's the best dish you've ever cooked?",
    ],
    "Travel & Adventure": [
        "What's the most beautiful place you've ever visited?",
        "Are you more of a mountains or beaches person?",
        "Do you have a travel bucket list? What's on top?",
        "Solo travel or group trips — what do you prefer?",
    ],
    "Technology & Coding": [
        "What programming languages are you into?",
        "Are you working on any cool side projects?",
        "What's your take on the latest AI developments?",
        "Do you prefer frontend, backend, or full-stack?",
    ],
    "Fashion & Style": [
        "Where do you usually get your outfit inspiration from?",
        "What's your go-to everyday style?",
        "Are you into streetwear or more of a classic dresser?",
        "Any fashion brands you're obsessed with right now?",
    ],
    "Motivation & Self-Improvement": [
        "What motivates you to keep going on tough days?",
        "Do you follow any specific morning routine?",
        "What's the best self-improvement advice you've received?",
        "Are you into journaling or meditation?",
    ],
    "Gaming": [
        "What games are you currently playing?",
        "PC, console, or mobile — what's your preferred platform?",
        "Have you played any game that genuinely blew your mind?",
        "Do you watch any gaming streamers or esports?",
    ],
    "Photography & Art": [
        "What kind of photography do you enjoy — portraits, street, or landscapes?",
        "Do you use any particular editing style or preset?",
        "What inspires your creative work?",
        "Have you ever exhibited or sold your art?",
    ],
    "Politics & Current Affairs": [
        "What current event are you following closely right now?",
        "Do you think social media is good or bad for political discourse?",
        "What change would you like to see in your community?",
    ],
    "Pets & Animals": [
        "Do you have any pets? What are they like?",
        "Are you a dog person or a cat person?",
        "What's the funniest thing your pet has ever done?",
        "Have you ever thought about adopting a rescue animal?",
    ],
}

# Fallback generic suggestions
GENERIC_SUGGESTIONS = [
    "What do you usually do on weekends?",
    "What's something you're passionate about that most people don't know?",
    "If you could learn any new skill overnight, what would it be?",
    "What's the best advice someone ever gave you?",
]


def generate_conversation_suggestions(
    topics: list[dict], max_suggestions: int = 5
) -> list[str]:
    """
    Generate conversation starter suggestions based on detected topics.

    Picks suggestions from top topics, with more suggestions from
    higher-confidence topics.

    Args:
        topics: List of topic dicts from the analyzer (sorted by score)
        max_suggestions: Maximum number of suggestions to generate

    Returns:
        List of conversation suggestion strings
    """
    suggestions = []

    if not topics:
        return random.sample(GENERIC_SUGGESTIONS, min(max_suggestions, len(GENERIC_SUGGESTIONS)))

    # Pick from top topics
    for topic in topics[:4]:
        name = topic["name"]
        if name in CONVERSATION_TEMPLATES:
            templates = CONVERSATION_TEMPLATES[name]
            # Pick 1-2 suggestions per topic
            count = 2 if topic == topics[0] else 1
            picked = random.sample(templates, min(count, len(templates)))
            suggestions.extend(picked)

        if len(suggestions) >= max_suggestions:
            break

    # Fill remaining with generic if needed
    while len(suggestions) < max_suggestions:
        remaining = [s for s in GENERIC_SUGGESTIONS if s not in suggestions]
        if not remaining:
            break
        suggestions.append(random.choice(remaining))

    return suggestions[:max_suggestions]


def generate_summary_sentence(topics: list[dict], source: str = "posts") -> str:
    """
    Generate a human-readable summary sentence.

    e.g., "This profile mostly reposts content about gym, love quotes,
    college life, Marathi memes, movies, and cricket."

    Args:
        topics: Sorted list of topic dicts
        source: Source of content (posts/reposts/following)

    Returns:
        Summary sentence string
    """
    if not topics:
        return "Not enough data to determine the profile's interests. Try adding more captions or text."

    # Take top topics with meaningful confidence
    significant = [t for t in topics if t["confidence"] > 15]
    if not significant:
        significant = topics[:3]

    topic_names = [t["name"].lower() for t in significant[:6]]

    if len(topic_names) == 1:
        topics_str = topic_names[0]
    elif len(topic_names) == 2:
        topics_str = f"{topic_names[0]} and {topic_names[1]}"
    else:
        topics_str = ", ".join(topic_names[:-1]) + f", and {topic_names[-1]}"

    if source == "following":
        return f"This profile follows accounts related to {topics_str}."
    return f"This profile mostly engages with content about {topics_str}."


def generate_report(analysis_results: dict, source: str = "posts", profile_info: dict = None) -> dict:
    """
    Generate the final structured report from analysis results.

    Args:
        analysis_results: Output from topic_analyzer.analyze()
        source: Source of content (posts/reposts/following)
        profile_info: Scraped profile data including posts_detail

    Returns:
        Complete report dict with all output fields
    """
    topics = analysis_results["topics"]

    # Top topics (max 8)
    top_topics = []
    for t in topics[:8]:
        top_topics.append({
            "name": t["name"],
            "confidence": t["confidence"],
            "matched_keywords": t["matched_keywords"][:5],
            "matched_hashtags": t["matched_hashtags"][:5],
        })

    # Common interests — derived from top topics
    common_interests = [t["name"] for t in topics[:5]]

    # Repeated keywords
    repeated_keywords = [
        {"word": kw, "count": count}
        for kw, count in analysis_results["keyword_frequency"][:15]
    ]

    # Repeated hashtags
    repeated_hashtags = [
        {"tag": f"#{tag}", "count": count}
        for tag, count in analysis_results["hashtag_frequency"][:15]
    ]

    # TF-IDF important keywords
    important_keywords = [
        {"word": kw, "score": round(score, 3)}
        for kw, score in analysis_results["tfidf_keywords"]
    ]

    # Named entities
    notable_entities = [
        {"name": name, "count": count}
        for name, count in analysis_results["top_entities"]
    ]

    # Conversation suggestions
    suggestions = generate_conversation_suggestions(topics)

    # Summary sentence
    summary = generate_summary_sentence(topics, source=source)

    # Vibe & Style analysis
    vibe = analyze_vibe(analysis_results.get("clean_texts", []))

    # Overall confidence score (average of top 3 topics)
    if top_topics:
        top_confidences = [t["confidence"] for t in top_topics[:3]]
        overall_confidence = round(sum(top_confidences) / len(top_confidences), 1)
    else:
        overall_confidence = 0

    # Engagement & Format Analytics
    engagement_analytics = {
        "total_likes": 0,
        "total_comments": 0,
        "avg_likes": 0.0,
        "avg_comments": 0.0,
        "engagement_rate": 0.0,
        "format_distribution": {"Reel": 0.0, "Carousel": 0.0, "Image": 0.0},
        "weekday_distribution": {
            "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0,
            "Friday": 0, "Saturday": 0, "Sunday": 0
        }
    }

    if profile_info and "posts_detail" in profile_info and profile_info["posts_detail"]:
        details = profile_info["posts_detail"]
        total_posts = len(details)
        
        total_likes = sum(d.get("likes", 0) for d in details)
        total_comments = sum(d.get("comments", 0) for d in details)
        
        avg_likes = round(total_likes / total_posts, 1) if total_posts > 0 else 0.0
        avg_comments = round(total_comments / total_posts, 1) if total_posts > 0 else 0.0
        
        followers = profile_info.get("followers", 0)
        if followers > 0 and total_posts > 0:
            # Average interaction rate per post: ((Interactions / Posts) / Followers) * 100
            er = round((((total_likes + total_comments) / total_posts) / followers) * 100, 2)
        else:
            # Fallback to post-based ER approximation if follower count is missing
            er = round(((avg_likes + avg_comments) / 1000) * 100, 2)
            
        engagement_analytics["total_likes"] = total_likes
        engagement_analytics["total_comments"] = total_comments
        engagement_analytics["avg_likes"] = avg_likes
        engagement_analytics["avg_comments"] = avg_comments
        engagement_analytics["engagement_rate"] = er
        
        # Format distribution
        formats = [d.get("format", "Image") for d in details]
        if formats:
            for fmt_name in ["Reel", "Carousel", "Image"]:
                count = formats.count(fmt_name)
                engagement_analytics["format_distribution"][fmt_name] = round((count / len(formats)) * 100, 1)
                
        # Weekday distribution
        from datetime import datetime
        for d in details:
            date_str = d.get("date", "")
            if date_str:
                for fmt in ("%B %d, %Y", "%b %d, %Y"):
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt)
                        day_name = dt.strftime("%A")
                        if day_name in engagement_analytics["weekday_distribution"]:
                            engagement_analytics["weekday_distribution"][day_name] += 1
                        break
                    except ValueError:
                        continue

    return {
        "summary": summary,
        "overall_confidence": overall_confidence,
        "top_topics": top_topics,
        "common_interests": common_interests,
        "repeated_keywords": repeated_keywords,
        "repeated_hashtags": repeated_hashtags,
        "important_keywords": important_keywords,
        "notable_entities": notable_entities,
        "conversation_suggestions": suggestions,
        "vibe": vibe,
        "engagement_analytics": engagement_analytics
    }
