import json
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer


# =========================================================
# PATHS
# =========================================================

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_FOLDER = os.path.join(
    BASE_FOLDER,
    "output"
)

CURRENT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "current_document.txt"
)


# =========================================================
# STOP WORDS
# =========================================================

STOP_WORDS = {
    # General English
    "the", "and", "for", "that", "this", "with",
    "from", "were", "was", "are", "been", "being",
    "have", "has", "had", "will", "would", "could",
    "should", "shall", "may", "might", "can",
    "not", "but", "than", "then", "into", "onto",
    "over", "under", "between", "among",
    "during", "through", "about", "after", "before",
    "above", "below", "within", "without",
    "also", "such", "their", "there", "these",
    "those", "they", "them", "which", "where",
    "when", "what", "whose", "while",
    "each", "both", "other", "more", "most",
    "some", "any", "all", "only", "same",
    "very", "per", "etc",

    # Document/report noise
    "report", "reports", "page", "pages",
    "table", "tables", "source", "sources",
    "note", "notes", "figure", "fig",
    "figures", "chart", "charts",
    "section", "chapter", "appendix",
    "data", "details", "information",
    "statement", "statements",
    "total", "value", "values",
    "year", "years", "month", "months",
    "date", "dates",
    "january", "february", "march", "april",
    "may", "june", "july", "august",
    "september", "october", "november", "december",

    # OCR/table noise
    "mtd", "ytd", "upto", "upto",
    "nos", "no", "nil", "na",
    "figs", "mt", "fy",
    "crore", "crores",
    "lakh", "lakhs",
    "rs", "inr",

    # Common administrative words
    "government", "ministry",
    "department", "office",
    "authority", "official",
    "regarding", "following",
    "provided", "given",
    "based", "including",
    "according", "respectively"
}


# =========================================================
# LOAD CURRENT DOCUMENT
# =========================================================

def get_current_json():

    if not os.path.exists(CURRENT_FILE):
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
        return None

    return json_file


# =========================================================
# LOAD DOCUMENT TEXT
# =========================================================

def load_document_text():

    json_file = get_current_json()

    if not json_file:
        return []

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except Exception as error:

        print(
            "JSON loading error:",
            error
        )

        return []

    documents = []

    for page in data.get("pages", []):

        page_text = str(
            page.get("text", "")
        ).strip()

        if page_text:
            documents.append(page_text)

        # Include table information because
        # important subjects may occur mainly
        # inside tables.

        for table in page.get("tables", []):

            title = str(
                table.get("title", "")
            ).strip()

            rows = table.get(
                "rows",
                []
            )

            table_text = []

            if title:
                table_text.append(title)

            for row in rows:

                row_text = str(row).strip()

                if row_text:
                    table_text.append(
                        row_text
                    )

            if table_text:

                documents.append(
                    " ".join(table_text)
                )

    return documents


# =========================================================
# CLEAN TEXT FOR TOPIC EXTRACTION
# =========================================================

def clean_text(text):

    text = text.lower()

    # Remove page markers
    text = re.sub(
        r"---\s*page\s*\d+\s*---",
        " ",
        text
    )

    # Remove URLs
    text = re.sub(
        r"https?://\S+|www\.\S+",
        " ",
        text
    )

    # Remove email addresses
    text = re.sub(
        r"\S+@\S+",
        " ",
        text
    )

    # Remove numbers
    text = re.sub(
        r"\b\d+(?:\.\d+)?\b",
        " ",
        text
    )

    # Remove special characters
    text = re.sub(
        r"[^a-zA-Z\s]",
        " ",
        text
    )

    # Normalize spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# =========================================================
# CHECK WHETHER A TERM IS MEANINGFUL
# =========================================================

def is_meaningful_topic(term):

    term = term.strip().lower()

    if not term:
        return False

    words = term.split()

    # Avoid extremely short terms
    if any(
        len(word) < 3
        for word in words
    ):
        return False

    # Avoid stop-word-only terms
    meaningful_words = [
        word
        for word in words
        if word not in STOP_WORDS
    ]

    if not meaningful_words:
        return False

    # A phrase should contain at least
    # one meaningful word.
    #
    # For multi-word phrases, require
    # at least two meaningful words.

    if len(words) >= 2:

        if len(meaningful_words) < 2:
            return False

    # Reject terms consisting mainly of
    # repeated/common words.

    if len(set(words)) != len(words):
        return False

    # Reject very generic terms
    generic_terms = {
        "information",
        "details",
        "statement",
        "document",
        "reporting",
        "analysis",
        "result",
        "results",
        "description",
        "general",
        "particular",
        "provided",
        "available"
    }

    if term in generic_terms:
        return False

    return True


# =========================================================
# REMOVE DUPLICATE / OVERLAPPING TOPICS
# =========================================================

def remove_redundant_topics(
    ranked_topics
):

    selected = []

    for topic, score in ranked_topics:

        topic_words = set(
            topic.split()
        )

        redundant = False

        for existing_topic, existing_score in selected:

            existing_words = set(
                existing_topic.split()
            )

            # Exact duplicate
            if topic == existing_topic:

                redundant = True
                break

            # If one phrase is completely contained
            # inside another, keep the stronger phrase.

            if (
                topic_words <= existing_words
                or
                existing_words <= topic_words
            ):

                # Prefer the longer meaningful phrase
                # when scores are reasonably close.

                if len(existing_words) >= len(topic_words):

                    if existing_score >= score * 0.80:

                        redundant = True
                        break

        if not redundant:

            selected.append(
                (topic, score)
            )

    return selected


# =========================================================
# IDENTIFY IMPORTANT TOPICS
# =========================================================

def identify_topics():

    documents = load_document_text()

    if not documents:

        print(
            "No current document found."
        )

        return []

    cleaned_documents = []

    for document in documents:

        cleaned = clean_text(
            document
        )

        if cleaned:

            cleaned_documents.append(
                cleaned
            )

    if not cleaned_documents:

        print(
            "No usable document text found."
        )

        return []

    # =====================================================
    # TF-IDF
    # =====================================================

    try:

        vectorizer = TfidfVectorizer(

            stop_words=list(
                STOP_WORDS
            ),

            ngram_range=(
                1,
                3
            ),

            min_df=2,

            max_features=1000,

            sublinear_tf=True
        )

        matrix = vectorizer.fit_transform(
            cleaned_documents
        )

    except ValueError as error:

        print(
            "Topic extraction error:",
            error
        )

        return []

    terms = vectorizer.get_feature_names_out()

    # =====================================================
    # CALCULATE IMPORTANCE
    # =====================================================

    scores = matrix.mean(
        axis=0
    ).A1

    ranked_topics = []

    for term, score in zip(
        terms,
        scores
    ):

        if not is_meaningful_topic(
            term
        ):
            continue

        ranked_topics.append(
            (
                term,
                float(score)
            )
        )

    if not ranked_topics:

        print(
            "No meaningful topics identified."
        )

        return []

    # Highest importance first
    ranked_topics.sort(
        key=lambda item: item[1],
        reverse=True
    )

    # =====================================================
    # IMPORTANCE THRESHOLD
    # =====================================================

    highest_score = ranked_topics[0][1]

    # Only retain terms that have a meaningful
    # relationship to the strongest topics.
    #
    # This is NOT a fixed number of topics.

    importance_threshold = (
        highest_score * 0.20
    )

    important_topics = [

        item

        for item in ranked_topics

        if item[1] >= importance_threshold

    ]

    # =====================================================
    # REMOVE REDUNDANCY
    # =====================================================

    important_topics = remove_redundant_topics(
        important_topics
    )

    # =====================================================
    # FINAL SORT
    # =====================================================

    important_topics.sort(
        key=lambda item: item[1],
        reverse=True
    )

    # Return only the topic names.
    #
    # NO [:10]
    # NO [:15]
    # NO artificial maximum.

    topics = [
        topic
        for topic, score
        in important_topics
    ]

    return topics


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    topics = identify_topics()

    print("\n")
    print("=" * 60)
    print("IMPORTANT TOPICS IDENTIFIED")
    print("=" * 60)

    if not topics:

        print(
            "No important topics identified."
        )

    else:

        for index, topic in enumerate(
            topics,
            start=1
        ):

            print(
                f"{index}. {topic}"
            )

    print("\n")
    print(
        "Total important topics identified:",
        len(topics)
    )