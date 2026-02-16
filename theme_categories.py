"""
Theme to Major Theme Category Mapping for Broadway Shows
Uses the same major categories as books for consistency.
"""

# Major theme categories (same as books)
MAJOR_THEMES = [
    "Human Condition & Emotions",
    "Identity & Self",
    "Personal Growth & Resilience",
    "Family & Relationships",
    "Morality & Ethics",
    "Faith & Spirituality",
    "Music & Arts",
    "Philosophy & Ideas",
    "Politics & Power",
    "War & Conflict",
    "Society & Culture",
    "Social Justice & Equality",
    "Business & Leadership",
    "Science & Technology",
    "Psychology & Behavior",
    "Nature & Environment",
    "Sports & Competition",
]

# Mapping of show themes to major categories
THEME_TO_MAJOR = {
    # Human Condition & Emotions
    "acceptance": "Human Condition & Emotions",
    "anxiety": "Human Condition & Emotions",
    "belonging": "Human Condition & Emotions",
    "connection": "Human Condition & Emotions",
    "death": "Human Condition & Emotions",
    "dreams": "Human Condition & Emotions",
    "empathy": "Human Condition & Emotions",
    "existential fear": "Human Condition & Emotions",
    "fate": "Human Condition & Emotions",
    "forgiveness": "Human Condition & Emotions",
    "isolation": "Human Condition & Emotions",
    "joy": "Human Condition & Emotions",
    "loss": "Human Condition & Emotions",
    "love": "Human Condition & Emotions",
    "madness": "Human Condition & Emotions",
    "personal struggle": "Human Condition & Emotions",
    "reality vs. illusion": "Human Condition & Emotions",
    "romance": "Human Condition & Emotions",
    "sacrifice": "Human Condition & Emotions",
    "trauma": "Human Condition & Emotions",
    "circle of life": "Human Condition & Emotions",
    "magic": "Human Condition & Emotions",
    
    # Identity & Self
    "adolescence": "Identity & Self",
    "ambition": "Identity & Self",
    "cultural identity": "Identity & Self",
    "identity": "Identity & Self",
    "identity and responsibility": "Identity & Self",
    "self-discovery": "Identity & Self",
    "self-identity": "Identity & Self",
    "autism": "Identity & Self",
    "jewish experience": "Identity & Self",
    
    # Personal Growth & Resilience
    "change": "Personal Growth & Resilience",
    "empowerment": "Personal Growth & Resilience",
    "moral growth": "Personal Growth & Resilience",
    "perseverance": "Personal Growth & Resilience",
    "redemption": "Personal Growth & Resilience",
    "resilience": "Personal Growth & Resilience",
    "survival": "Personal Growth & Resilience",
    
    # Family & Relationships
    "betrayal": "Family & Relationships",
    "community": "Family & Relationships",
    "family": "Family & Relationships",
    "family legacy": "Family & Relationships",
    "fatherhood": "Family & Relationships",
    "friendship": "Family & Relationships",
    "legacy": "Family & Relationships",
    
    # Morality & Ethics
    "corruption": "Morality & Ethics",
    "crime": "Morality & Ethics",
    "ethics": "Morality & Ethics",
    "justice": "Morality & Ethics",
    "murder": "Morality & Ethics",
    "revenge": "Morality & Ethics",
    "truth and lies": "Morality & Ethics",
    
    # Faith & Spirituality
    "faith": "Faith & Spirituality",
    "religion": "Faith & Spirituality",
    
    # Music & Arts
    "celebrity": "Music & Arts",
    "fame": "Music & Arts",
    "music industry": "Music & Arts",
    "theater": "Music & Arts",
    "1950s television": "Music & Arts",
    
    # Politics & Power
    "capitalism": "Politics & Power",
    "cold war": "Politics & Power",
    "political history": "Politics & Power",
    "politics": "Politics & Power",
    "power": "Politics & Power",
    "revolution": "Politics & Power",
    "war": "War & Conflict",
    
    # Society & Culture
    "american dream": "Society & Culture",
    "the american dream": "Society & Culture",
    "class struggle": "Society & Culture",
    "cultural clashes": "Society & Culture",
    "cultural conflict": "Society & Culture",
    "history": "Society & Culture",
    "immigration": "Society & Culture",
    "social class": "Society & Culture",
    "societal norms": "Society & Culture",
    "socioeconomic struggles": "Society & Culture",
    "popularity": "Society & Culture",
    "mystery": "Society & Culture",
    
    # Social Justice & Equality
    "hiv/aids": "Social Justice & Equality",
    "prejudice": "Social Justice & Equality",
    "racial injustice": "Social Justice & Equality",
    
    # Business & Leadership
    "competition": "Business & Leadership",
    "success": "Business & Leadership",
    
    # Science & Technology
    "technology": "Science & Technology",
    "media": "Science & Technology",
    "journalism": "Science & Technology",
    
    # Psychology & Behavior
    "mental health": "Psychology & Behavior",
    "education": "Psychology & Behavior",
    
    # Nature & Environment
    "nature": "Nature & Environment",
}


def get_major_theme(themes_list):
    """
    Given a list of themes, determine the most appropriate major theme.
    Returns the major theme that appears most frequently among the show's themes.
    """
    if not themes_list:
        return None
    
    # Count occurrences of each major theme
    major_counts = {}
    for theme in themes_list:
        theme_lower = theme.lower().strip()
        if theme_lower in THEME_TO_MAJOR:
            major = THEME_TO_MAJOR[theme_lower]
            major_counts[major] = major_counts.get(major, 0) + 1
    
    if not major_counts:
        return None
    
    # Return the major theme with the highest count
    return max(major_counts, key=major_counts.get)


def get_all_major_themes(themes_list):
    """
    Given a list of themes, return all unique major themes.
    """
    if not themes_list:
        return []
    
    majors = set()
    for theme in themes_list:
        theme_lower = theme.lower().strip()
        if theme_lower in THEME_TO_MAJOR:
            majors.add(THEME_TO_MAJOR[theme_lower])
    
    return sorted(majors)
