import os
import json

TAXONOMY_FILE = "taxonomy.json"

DEFAULT_TAXONOMY = {
    "Fitness & Gym": {
        "keywords": [
            "gym", "workout", "fitness", "exercise", "lift", "weight",
            "muscle", "protein", "bulk", "cut", "cardio", "crossfit",
            "bodybuilding", "deadlift", "squat", "bench", "gains",
            "shred", "abs", "bicep", "tricep", "leg day", "chest",
            "shoulder", "back", "transform", "fit", "healthy",
            "strength", "training", "reps", "sets", "pr", "personal record"
        ],
        "hashtags": [
            "gym", "fitness", "workout", "fitfam", "gymmotivation",
            "fitnessmotivation", "bodybuilding", "gymlife", "gains",
            "legday", "chestday", "armday", "personalrecord"
        ]
    },
    "Love & Relationships": {
        "keywords": [
            "love", "heart", "bae", "relationship", "couple", "date",
            "romance", "crush", "soulmate", "partner", "wife", "husband",
            "boyfriend", "girlfriend", "marry", "wedding", "forever",
            "miss", "hug", "kiss", "care", "feeling", "emotion",
            "breakup", "heal", "toxic", "red flag", "trust",
            "loyalty", "commitment"
        ],
        "hashtags": [
            "love", "couplegoals", "relationship", "lovequotes",
            "romance", "bae", "forever", "truelove", "heartbreak",
            "couple", "lovers", "soulmate"
        ]
    },
    "College & Student Life": {
        "keywords": [
            "college", "university", "exam", "study", "student",
            "semester", "lecture", "professor", "campus", "hostel",
            "class", "assignment", "degree", "engineering", "btech",
            "mba", "placement", "intern", "topper", "backlog",
            "attendance", "project", "viva", "lab", "library",
            "canteen", "fest", "fresher"
        ],
        "hashtags": [
            "college", "collegelife", "student", "studentlife",
            "exam", "study", "engineering", "campus", "hostel",
            "placement", "btech", "university"
        ]
    },
    "Humor & Memes": {
        "keywords": [
            "meme", "funny", "lol", "lmao", "rofl", "joke", "humor",
            "comedy", "laugh", "hilarious", "savage", "sarcasm",
            "trolling", "relatable", "dank", "shitpost"
        ],
        "hashtags": [
            "meme", "memes", "funny", "humor", "comedy", "lol",
            "dankmemes", "funnymemes", "memesdaily", "joke",
            "sarcasm", "savage", "relatable"
        ]
    },
    "Cricket & Sports": {
        "keywords": [
            "cricket", "ipl", "t20", "odi", "test match", "world cup",
            "batsman", "bowler", "wicket", "century", "six", "four",
            "innings", "pitch", "stadium", "dhoni", "virat", "kohli",
            "rohit", "sachin", "rcb", "csk", "mi", "kkr",
            "sport", "football", "soccer", "basketball", "tennis",
            "match", "team", "player", "goal", "score", "win",
            "champion", "league", "tournament", "final"
        ],
        "hashtags": [
            "cricket", "ipl", "t20", "worldcup", "dhoni", "virat",
            "kohli", "rcb", "csk", "sports", "football", "basketball",
            "tennis", "fifa", "nba", "match"
        ]
    },
    "Movies & Entertainment": {
        "keywords": [
            "movie", "film", "bollywood", "hollywood", "netflix",
            "series", "show", "actor", "actress", "director", "scene",
            "dialogue", "trailer", "review", "rating", "oscar",
            "award", "release", "theater", "cinema", "ott",
            "amazon prime", "hotstar", "drama", "thriller",
            "action", "horror", "comedy", "anime", "kdrama",
            "webseries", "binge", "watch"
        ],
        "hashtags": [
            "movie", "bollywood", "hollywood", "netflix", "film",
            "cinema", "webseries", "anime", "kdrama", "ott",
            "amazonprime", "hotstar", "bingewatch"
        ]
    },
    "Music": {
        "keywords": [
            "music", "song", "sing", "singer", "rapper", "rap",
            "album", "track", "beat", "melody", "lyric", "concert",
            "spotify", "playlist", "tune", "bass", "guitar", "piano",
            "drum", "vocal", "band", "dj", "edm", "hiphop",
            "pop", "rock", "classical", "indie", "lofi"
        ],
        "hashtags": [
            "music", "song", "singer", "spotify", "hiphop", "rap",
            "edm", "rock", "pop", "indie", "lofi", "playlist",
            "concert", "newmusic", "musiclover"
        ]
    },
    "Food & Cooking": {
        "keywords": [
            "food", "recipe", "cook", "kitchen", "eat", "restaurant",
            "cafe", "dish", "meal", "breakfast", "lunch", "dinner",
            "snack", "dessert", "cake", "pizza", "burger", "biryani",
            "pasta", "sushi", "vegan", "vegetarian", "spicy",
            "delicious", "yummy", "tasty", "chef", "bake",
            "street food", "homemade", "foodie"
        ],
        "hashtags": [
            "food", "foodie", "recipe", "cooking", "chef", "yummy",
            "delicious", "homemade", "streetfood", "biryani",
            "foodporn", "instafood", "foodstagram", "baking"
        ]
    },
    "Travel & Adventure": {
        "keywords": [
            "travel", "trip", "vacation", "holiday", "adventure",
            "explore", "wander", "backpack", "trek", "hike",
            "mountain", "beach", "island", "road trip", "flight",
            "hotel", "resort", "camping", "nature", "sunset",
            "sunrise", "view", "landscape", "destination",
            "passport", "tourist", "solo travel"
        ],
        "hashtags": [
            "travel", "wanderlust", "adventure", "explore",
            "travelgram", "vacation", "trip", "nature", "beach",
            "mountain", "hiking", "backpacking", "solotravel",
            "roadtrip", "sunset", "traveldiaries"
        ]
    },
    "Technology & Coding": {
        "keywords": [
            "tech", "technology", "code", "coding", "programming",
            "developer", "software", "app", "web", "python", "java",
            "javascript", "react", "ai", "artificial intelligence",
            "machine learning", "data science", "startup", "gadget",
            "phone", "laptop", "computer", "hack", "cyber",
            "blockchain", "crypto", "cloud", "devops", "github",
            "linux", "open source"
        ],
        "hashtags": [
            "tech", "coding", "programming", "developer", "python",
            "javascript", "ai", "machinelearning", "datascience",
            "startup", "gadgets", "cyber", "blockchain", "github",
            "webdev", "software", "linux"
        ]
    },
    "Fashion & Style": {
        "keywords": [
            "fashion", "style", "outfit", "wear", "dress", "clothes",
            "brand", "designer", "model", "runway", "trend", "ootd",
            "accessory", "shoe", "sneaker", "watch", "sunglasses",
            "jacket", "hoodie", "jeans", "streetwear", "luxury",
            "aesthetic", "drip", "swag"
        ],
        "hashtags": [
            "fashion", "style", "ootd", "outfit", "streetwear",
            "sneakers", "luxury", "model", "trend", "aesthetic",
            "fashionista", "drip"
        ]
    },
    "Motivation & Self-Improvement": {
        "keywords": [
            "motivation", "inspire", "grind", "hustle", "success",
            "goal", "dream", "mindset", "discipline", "focus",
            "believe", "achieve", "never give up", "hard work",
            "quote", "sigma", "alpha", "stoic", "level up",
            "growth", "potential", "confidence", "self love",
            "mental health", "meditate", "journal", "habit",
            "productivity", "morning routine", "positive"
        ],
        "hashtags": [
            "motivation", "inspiration", "grind", "hustle",
            "success", "mindset", "discipline", "quotes",
            "motivationalquotes", "sigma", "selfimprovement",
            "growthmindset", "nevergiveup", "believe"
        ]
    },
    "Gaming": {
        "keywords": [
            "game", "gaming", "gamer", "play", "stream", "twitch",
            "console", "pc", "ps5", "xbox", "nintendo", "esport",
            "valorant", "fortnite", "minecraft", "gta", "cod",
            "pubg", "bgmi", "freefire", "rpg", "fps", "mmorpg",
            "level", "rank", "clutch", "headshot", "noob", "pro"
        ],
        "hashtags": [
            "gaming", "gamer", "ps5", "xbox", "valorant", "fortnite",
            "minecraft", "gta", "pubg", "bgmi", "esports",
            "pcgaming", "twitch", "streamer"
        ]
    },
    "Photography & Art": {
        "keywords": [
            "photo", "photography", "camera", "portrait", "landscape",
            "shoot", "edit", "lightroom", "photoshop", "lens",
            "dslr", "mirrorless", "art", "artist", "draw", "paint",
            "sketch", "illustration", "design", "creative",
            "digital art", "canvas", "gallery", "exhibition"
        ],
        "hashtags": [
            "photography", "photo", "portrait", "landscape",
            "photographer", "art", "artist", "drawing", "painting",
            "digitalart", "creative", "design", "sketch"
        ]
    },
    "Politics & Current Affairs": {
        "keywords": [
            "politics", "election", "government", "minister",
            "parliament", "democracy", "vote", "policy", "law",
            "protest", "rally", "party", "congress", "bjp",
            "modi", "opposition", "debate", "economy", "budget",
            "tax", "inflation", "corruption", "news", "breaking"
        ],
        "hashtags": [
            "politics", "election", "government", "news",
            "currentaffairs", "breaking", "democracy"
        ]
    },
    "Pets & Animals": {
        "keywords": [
            "dog", "cat", "pet", "puppy", "kitten", "animal",
            "adopt", "rescue", "breed", "walk", "vet", "cute",
            "pawsome", "fur", "tail", "bark", "meow"
        ],
        "hashtags": [
            "dog", "cat", "pet", "puppy", "kitten", "dogsofinstagram",
            "catsofinstagram", "cute", "petlover", "adopt"
        ]
    }
}


def load_taxonomy() -> dict:
    """Load taxonomy from JSON file or fall back to default."""
    if os.path.exists(TAXONOMY_FILE):
        try:
            with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TaxonomyManager] Error reading JSON: {e}. Falling back to default.")
            return DEFAULT_TAXONOMY
    else:
        # Save default to file on first load
        save_taxonomy(DEFAULT_TAXONOMY)
        return DEFAULT_TAXONOMY


def save_taxonomy(taxonomy_data: dict) -> bool:
    """Save taxonomy to JSON file."""
    try:
        with open(TAXONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump(taxonomy_data, f, indent=4)
        return True
    except Exception as e:
        print(f"[TaxonomyManager] Error saving JSON: {e}")
        return False
