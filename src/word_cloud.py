import os
import json
import re

from wordcloud import WordCloud
import matplotlib.pyplot as plt


# =========================================================
# FOLDERS
# =========================================================

BASE_FOLDER = r"C:\coalmind"

OUTPUT_FOLDER = os.path.join(
    BASE_FOLDER,
    "output"
)

CURRENT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "current_document.txt"
)

WORDCLOUD_FILE = os.path.join(
    OUTPUT_FOLDER,
    "wordcloud.png"
)


# =========================================================
# STOP WORDS
# =========================================================

STOP_WORDS = {
    "the",
    "and",
    "of",
    "to",
    "in",
    "for",
    "on",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "by",
    "with",
    "from",
    "as",
    "at",
    "or",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "has",
    "have",
    "had",
    "not",
    "but",
    "than",
    "into",
    "during",
    "through",
    "over",
    "under",
    "about",
    "which",
    "their",
    "there",
    "been",
    "being",
    "also",
    "such",
    "may",
    "can",
    "will",
    "would",
    "should",
    "per",
    "no",
    "yes"
}


# =========================================================
# GET CURRENT JSON FILE
# =========================================================

def get_current_json():

    if not os.path.exists(CURRENT_FILE):

        print(
            "No current document found."
        )

        return None

    with open(
        CURRENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        json_file = file.read().strip()

    if not json_file:

        return None

    if not os.path.exists(json_file):

        print(
            "Current JSON file not found:"
        )

        print(json_file)

        return None

    return json_file


# =========================================================
# LOAD JSON
# =========================================================

def load_document():

    json_file = get_current_json()

    if not json_file:

        return None

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        print(
            "Word Cloud document:",
            os.path.basename(json_file)
        )

        return data

    except Exception as error:

        print(
            "Error loading JSON:",
            error
        )

        return None


# =========================================================
# EXTRACT TEXT
# =========================================================

def extract_text(data):

    if not data:

        return ""

    all_text = []

    for page in data.get(
        "pages",
        []
    ):

        page_text = page.get(
            "text",
            ""
        )

        if page_text:

            all_text.append(
                page_text
            )

    return "\n".join(
        all_text
    )


# =========================================================
# CLEAN WORD CLOUD TEXT
# =========================================================

def clean_text(text):

    text = text.lower()

    # Keep only alphabetic words
    words = re.findall(
        r"[a-zA-Z]+",
        text
    )

    useful_words = []

    for word in words:

        if len(word) < 3:
            continue

        if word in STOP_WORDS:
            continue

        useful_words.append(
            word
        )

    return " ".join(
        useful_words
    )


# =========================================================
# GENERATE WORD CLOUD
# =========================================================

def generate_word_cloud():

    data = load_document()

    if data is None:

        return None

    text = extract_text(
        data
    )

    if not text.strip():

        print(
            "No text found in document."
        )

        return None

    cleaned_text = clean_text(
        text
    )

    if not cleaned_text.strip():

        print(
            "No usable words found."
        )

        return None

    wordcloud = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        max_words=100
    ).generate(
        cleaned_text
    )

    plt.figure(
        figsize=(14, 7)
    )

    plt.imshow(
        wordcloud,
        interpolation="bilinear"
    )

    plt.axis(
        "off"
    )

    plt.tight_layout()

    wordcloud.to_file(
        WORDCLOUD_FILE
    )

    plt.close()

    print(
        "\nWord Cloud generated successfully!"
    )

    print(
        "Saved to:"
    )

    print(
        WORDCLOUD_FILE
    )

    return WORDCLOUD_FILE


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    generate_word_cloud()