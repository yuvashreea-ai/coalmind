import os
import json
import re
import numpy as np
import ollama

from sentence_transformers import SentenceTransformer


# ============================================================
# COALMIND AI / HYBRID RAG QUERY RESPONSE
# ============================================================

BASE_FOLDER = r"C:\coalmind"
OUTPUT_FOLDER = os.path.join(BASE_FOLDER, "output")

CURRENT_FILE = os.path.join(
    OUTPUT_FOLDER,
    "current_document.txt"
)

# ------------------------------------------------------------
# Embedding model
# MiniLM is used for semantic retrieval.
# ------------------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ------------------------------------------------------------
# Local LLM
# Llama 3.2 is used for answer generation through Ollama.
# ------------------------------------------------------------

GENERATION_MODEL = "llama3.2:3b"

TOP_K = 5


# ============================================================
# CURRENT DOCUMENT
# ============================================================

def get_current_json():

    if not os.path.exists(CURRENT_FILE):

        print("No current document found.")

        return None

    with open(
        CURRENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        json_file = file.read().strip()

    if not json_file:

        print("No current document is selected.")

        return None

    if not os.path.exists(json_file):

        print("Current JSON file not found:")
        print(json_file)

        return None

    return json_file


# ============================================================
# LOAD JSON
# ============================================================

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
            "Query document:",
            os.path.basename(json_file)
        )

        return data

    except Exception as error:

        print(
            "Error loading JSON:",
            error
        )

        return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.replace(
        "\\n",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT TEXT FROM ANY JSON STRUCTURE
# ============================================================

def extract_text_from_object(obj):

    """
    Recursively extracts useful textual content from
    the JSON produced by structure_extractor.py.
    """

    texts = []

    if isinstance(obj, str):

        text = clean_text(obj)

        if text:
            texts.append(text)

    elif isinstance(obj, list):

        for item in obj:

            texts.extend(
                extract_text_from_object(item)
            )

    elif isinstance(obj, dict):

        # Important textual fields first

        preferred_keys = [
            "title",
            "text",
            "content",
            "page_text",
            "heading",
            "section",
            "source",
            "description"
        ]

        for key in preferred_keys:

            if key in obj:

                value = obj[key]

                if isinstance(value, str):

                    text = clean_text(value)

                    if text:
                        texts.append(text)

        # Rows need special handling

        if "rows" in obj:

            rows = obj["rows"]

            if isinstance(rows, list):

                for row in rows:

                    if isinstance(row, dict):

                        row_values = []

                        for value in row.values():

                            value = clean_text(value)

                            if value:
                                row_values.append(value)

                        if row_values:

                            texts.append(
                                " | ".join(row_values)
                            )

                    elif isinstance(row, list):

                        row_values = []

                        for value in row:

                            value = clean_text(value)

                            if value:
                                row_values.append(value)

                        if row_values:

                            texts.append(
                                " | ".join(row_values)
                            )

                    else:

                        text = clean_text(row)

                        if text:
                            texts.append(text)

        # Recursively inspect remaining fields

        for key, value in obj.items():

            if key in preferred_keys:
                continue

            if key == "rows":
                continue

            if isinstance(
                value,
                (dict, list)
            ):

                texts.extend(
                    extract_text_from_object(value)
                )

    return texts


# ============================================================
# BUILD DOCUMENT CHUNKS
# ============================================================

def build_document_chunks(data):

    """
    Converts the existing structured JSON into
    RAG-friendly chunks.

    Each chunk keeps page + section + content.
    """

    chunks = []

    # --------------------------------------------------------
    # CASE 1: JSON is a list
    # --------------------------------------------------------

    if isinstance(data, list):

        objects = data

    # --------------------------------------------------------
    # CASE 2: JSON is a dictionary
    # --------------------------------------------------------

    elif isinstance(data, dict):

        objects = []

        # Try common page/table containers

        for key in [
            "pages",
            "documents",
            "sections",
            "data",
            "results"
        ]:

            if key in data and isinstance(
                data[key],
                list
            ):

                objects = data[key]

                break

        # If no container exists, process root

        if not objects:
            objects = [data]

    else:

        return []

    # --------------------------------------------------------
    # Process objects
    # --------------------------------------------------------

    for index, obj in enumerate(objects):

        page = None
        title = ""
        content_parts = []

        if isinstance(obj, dict):

            page = obj.get(
                "page",
                obj.get("page_number")
            )

            title = clean_text(
                obj.get(
                    "title",
                    obj.get(
                        "section",
                        ""
                    )
                )
            )

            # Page text

            for key in [
                "text",
                "content",
                "page_text"
            ]:

                value = obj.get(key)

                if isinstance(value, str):

                    value = clean_text(value)

                    if value:
                        content_parts.append(value)

            # Rows

            rows = obj.get(
                "rows",
                []
            )

            if isinstance(rows, list):

                for row in rows:

                    if isinstance(row, dict):

                        values = []

                        for value in row.values():

                            value = clean_text(
                                value
                            )

                            if value:
                                values.append(value)

                        if values:

                            content_parts.append(
                                " | ".join(values)
                            )

                    elif isinstance(row, list):

                        values = []

                        for value in row:

                            value = clean_text(
                                value
                            )

                            if value:
                                values.append(value)

                        if values:

                            content_parts.append(
                                " | ".join(values)
                            )

                    else:

                        value = clean_text(row)

                        if value:

                            content_parts.append(value)

        else:

            content_parts = (
                extract_text_from_object(obj)
            )

        # ----------------------------------------------------
        # Create chunk
        # ----------------------------------------------------

        if content_parts:

            unique_parts = []

            for part in content_parts:

                if (
                    part
                    and part not in unique_parts
                ):

                    unique_parts.append(part)

            content = "\n".join(
                unique_parts
            )

            if content:

                chunks.append(
                    {
                        "id": index,
                        "page": page,
                        "title": title,
                        "text": content
                    }
                )

    # --------------------------------------------------------
    # Fallback:
    # recursively extract entire document
    # --------------------------------------------------------

    if not chunks:

        all_text = extract_text_from_object(
            data
        )

        if all_text:

            combined = "\n".join(
                all_text
            )

            paragraphs = re.split(
                r"\n+",
                combined
            )

            current = []

            for paragraph in paragraphs:

                paragraph = clean_text(
                    paragraph
                )

                if not paragraph:
                    continue

                current.append(
                    paragraph
                )

                if len(" ".join(current)) > 1200:

                    chunks.append(
                        {
                            "id": len(chunks),
                            "page": None,
                            "title": "",
                            "text": "\n".join(
                                current
                            )
                        }
                    )

                    current = []

            if current:

                chunks.append(
                    {
                        "id": len(chunks),
                        "page": None,
                        "title": "",
                        "text": "\n".join(
                            current
                        )
                    }
                )

    # --------------------------------------------------------
    # Split very large chunks
    #
    # This improves retrieval for questions involving:
    # - specific financial years
    # - numerical values
    # - production figures
    # - tables
    # --------------------------------------------------------

    refined_chunks = []

    for chunk in chunks:

        chunk_text = chunk.get(
            "text",
            ""
        )

        # Keep smaller chunks unchanged

        if len(chunk_text) <= 1800:

            refined_chunks.append(
                chunk
            )

            continue

        paragraphs = re.split(
            r"\n+",
            chunk_text
        )

        current = []
        current_length = 0

        for paragraph in paragraphs:

            paragraph = clean_text(
                paragraph
            )

            if not paragraph:
                continue

            if (
                current
                and
                current_length + len(paragraph) > 1800
            ):

                refined_chunks.append(
                    {
                        "id": (
                            f'{chunk.get("id")}_'
                            f'{len(refined_chunks)}'
                        ),
                        "page": chunk.get("page"),
                        "title": chunk.get(
                            "title",
                            ""
                        ),
                        "text": "\n".join(
                            current
                        )
                    }
                )

                current = []
                current_length = 0

            current.append(
                paragraph
            )

            current_length += len(
                paragraph
            )

        if current:

            refined_chunks.append(
                {
                    "id": (
                        f'{chunk.get("id")}_'
                        f'{len(refined_chunks)}'
                    ),
                    "page": chunk.get("page"),
                    "title": chunk.get(
                        "title",
                        ""
                    ),
                    "text": "\n".join(
                        current
                    )
                }
            )

    return refined_chunks


# ============================================================
# NORMALIZE VECTOR
# ============================================================

def normalize_vectors(vectors):

    norms = np.linalg.norm(
        vectors,
        axis=1,
        keepdims=True
    )

    norms[norms == 0] = 1

    return vectors / norms


# ============================================================
# KEYWORD SCORE
# ============================================================

def keyword_score(query, text):

    query_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            query.lower()
        )
    )

    text_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower()
        )
    )

    if not query_words:
        return 0.0

    matches = query_words.intersection(
        text_words
    )

    return len(matches) / len(
        query_words
    )


# ============================================================
# SEMANTIC + KEYWORD RETRIEVAL
# ============================================================

def retrieve_relevant_chunks(
    chunks,
    query,
    embedding_model
):

    if not chunks:
        return []

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    # --------------------------------------------------------
    # Create embeddings
    # --------------------------------------------------------

    print(
        f"Creating embeddings for {len(texts)} "
        "document chunks..."
    )

    document_embeddings = (
        embedding_model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
    )

    query_embedding = (
        embedding_model.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False
        )
    )

    document_embeddings = (
        normalize_vectors(
            document_embeddings
        )
    )

    query_embedding = (
        normalize_vectors(
            query_embedding
        )
    )

    semantic_scores = (
        document_embeddings
        @ query_embedding[0]
    )

    # --------------------------------------------------------
    # Hybrid scoring
    # --------------------------------------------------------

    scored_chunks = []

    query_lower = query.lower()

    query_tokens = re.findall(
        r"\b[a-zA-Z0-9]+(?:[-–][a-zA-Z0-9]+)*\b",
        query_lower
    )

    for i, chunk in enumerate(chunks):

        semantic = float(
            semantic_scores[i]
        )

        keyword = keyword_score(
            query,
            chunk["text"]
        )

        text_lower = chunk["text"].lower()

        # ----------------------------------------------------
        # Exact token presence bonus
        #
        # Helps with queries containing:
        # FY 2024-25
        # 2025-26
        # production
        # MT
        # percentages
        # ----------------------------------------------------

        exact_token_matches = sum(
            1
            for token in query_tokens
            if token in text_lower
        )

        token_bonus = (
            exact_token_matches
            / len(query_tokens)
            if query_tokens
            else 0.0
        )

        # ----------------------------------------------------
        # Final hybrid score
        # ----------------------------------------------------

        final_score = (
            0.60 * semantic
            +
            0.25 * keyword
            +
            0.15 * token_bonus
        )

        scored_chunks.append(
            (
                final_score,
                semantic,
                keyword,
                chunk
            )
        )

    scored_chunks.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return scored_chunks[:TOP_K]


# ============================================================
# LOAD AI MODEL
# ============================================================

def load_generation_model():

    print()

    print(
        "Loading local LLM through Ollama..."
    )

    print(
        "Model:",
        GENERATION_MODEL
    )

    try:

        # Check that the model exists in Ollama

        ollama.show(
            GENERATION_MODEL
        )

        print(
            "LLM is available."
        )

        # IMPORTANT:
        # Return only the model name.
        # Do NOT return tokenizer/model like FLAN-T5.

        return GENERATION_MODEL

    except Exception as error:

        print(
            "Ollama LLM is not available:",
            error
        )

        print()

        print(
            f"Make sure Ollama is running and "
            f"run: ollama pull {GENERATION_MODEL}"
        )

        return None


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_ai_answer(
    query,
    retrieved_chunks,
    llm_model
):

    if not retrieved_chunks:

        return (
            "I could not find relevant "
            "information in the uploaded document."
        )

    if not llm_model:

        return (
            "The LLM is not available. "
            "Please start Ollama and make sure "
            "the model is installed."
        )

    # --------------------------------------------------------
    # Build structured context
    # --------------------------------------------------------

    context_parts = []

    for rank, (
        score,
        semantic,
        keyword,
        chunk
    ) in enumerate(
        retrieved_chunks,
        start=1
    ):

        page = chunk.get(
            "page"
        )

        title = clean_text(
            chunk.get(
                "title",
                ""
            )
        )

        chunk_text = clean_text(
            chunk.get(
                "text",
                ""
            )
        )

        source_label = ""

        if page is not None:

            source_label = (
                f"Page {page}"
            )

        if title:

            if source_label:

                source_label += " — "

            source_label += title

        if not source_label:

            source_label = "Document"

        context_parts.append(
            f"--- Retrieved Source {rank} ---\n"
            f"Source: {source_label}\n"
            f"Content:\n{chunk_text}"
        )

    context = "\n\n".join(
        context_parts
    )

    # --------------------------------------------------------
    # Context limit
    # --------------------------------------------------------

    context = context[:12000]

    # --------------------------------------------------------
    # Grounded RAG prompt
    # --------------------------------------------------------

    prompt = f"""
You are COALMIND, an AI assistant for official
coal and mining reports.

Answer the user's question ONLY using the
retrieved document context below.

IMPORTANT RULES:

1. Use only the supplied document context.

2. Do not use outside knowledge.

3. Do not invent, estimate, or assume numbers.

4. Carefully match the financial year requested
   by the user.

5. For questions involving production, revenue,
   targets, percentages, quantities, or other
   numerical information, carefully inspect the
   retrieved context for the exact value.

6. If the requested information is present
   anywhere in the retrieved context, answer
   using that information.

7. Information may appear inside a table,
   row, paragraph, or report section.

8. If the requested information is genuinely
   absent from the retrieved context, say:

   "The information was not found in the
   provided document."

9. Keep the answer concise and factual.

10. When useful, mention the relevant source page.

USER QUESTION:
{query}

RETRIEVED DOCUMENT CONTEXT:
{context}

FINAL ANSWER:
"""

    # --------------------------------------------------------
    # Generate using Llama through Ollama
    # --------------------------------------------------------

    try:

        response = ollama.chat(
            model=llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded document "
                        "question-answering assistant. "
                        "Use only the supplied document "
                        "context and do not invent facts."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.0
            }
        )

        answer = (
            response[
                "message"
            ][
                "content"
            ]
        )

    except Exception as error:

        print(
            "LLM generation error:",
            error
        )

        return (
            "The LLM could not generate a response. "
            "Please check that Ollama is running."
        )

    answer = clean_text(
        answer
    )

    if not answer:

        answer = (
            "The LLM could not generate "
            "a reliable answer from the "
            "retrieved document information."
        )

    return answer


# ============================================================
# EXTRACT SOURCE INFORMATION
# ============================================================

def get_sources(
    retrieved_chunks
):

    sources = []

    for (
        score,
        semantic,
        keyword,
        chunk
    ) in retrieved_chunks:

        page = chunk.get(
            "page"
        )

        title = clean_text(
            chunk.get(
                "title",
                ""
            )
        )

        if page is not None:

            if title:

                source = (
                    f"Page {page} — {title}"
                )

            else:

                source = (
                    f"Page {page}"
                )

        else:

            source = (
                title
                or
                "Document"
            )

        if source not in sources:

            sources.append(
                source
            )

    return sources


# ============================================================
# MAIN RAG PIPELINE
# ============================================================

def generate_response(
    data,
    query
):

    if not data:

        return (
            "No processed document is available."
        )

    if not query.strip():

        return (
            "Please enter a question."
        )

    # --------------------------------------------------------
    # STEP 1
    # Build chunks
    # --------------------------------------------------------

    print()

    print(
        "Preparing document for AI retrieval..."
    )

    chunks = build_document_chunks(
        data
    )

    print(
        "Document chunks available:",
        len(chunks)
    )

    if not chunks:

        return (
            "No usable content was found "
            "in the structured document."
        )

    # --------------------------------------------------------
    # STEP 2
    # Load embedding model
    # --------------------------------------------------------

    print()

    print(
        "Searching using hybrid retrieval..."
    )

    print()

    print(
        "Loading embedding model..."
    )

    print(
        "Model:",
        EMBEDDING_MODEL
    )

    embedding_model = (
        SentenceTransformer(
            EMBEDDING_MODEL
        )
    )

    print(
        "Embedding model loaded."
    )

    # --------------------------------------------------------
    # STEP 3
    # Retrieve relevant chunks
    # --------------------------------------------------------

    retrieved_chunks = (
        retrieve_relevant_chunks(
            chunks,
            query,
            embedding_model
        )
    )

    print()

    print(
        "Relevant sources retrieved:",
        len(retrieved_chunks)
    )

    if not retrieved_chunks:

        return (
            "No relevant information was "
            "retrieved from the document."
        )

    # --------------------------------------------------------
    # STEP 4
    # Load LLM
    # --------------------------------------------------------

    print()

    print(
        "Generating AI response..."
    )

    # IMPORTANT:
    # Only ONE value is returned here.
    # This fixes the previous:
    #
    # ValueError: too many values to unpack
    #
    llm_model = (
        load_generation_model()
    )

    # --------------------------------------------------------
    # STEP 5
    # Generate answer
    # --------------------------------------------------------

    answer = generate_ai_answer(
        query,
        retrieved_chunks,
        llm_model
    )

    # --------------------------------------------------------
    # STEP 6
    # Sources
    # --------------------------------------------------------

    sources = get_sources(
        retrieved_chunks
    )

    response = []

    response.append(
        answer
    )

    response.append("")

    response.append(
        "Sources:"
    )

    for source in sources:

        response.append(
            f"• {source}"
        )

    return "\n".join(
        response
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 60
    )

    print(
        "COALMIND AI / HYBRID RAG QUERY → RESPONSE"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # Load document
    # --------------------------------------------------------

    data = load_document()

    if data is None:

        return

    # --------------------------------------------------------
    # Ask question
    # --------------------------------------------------------

    query = input(
        "\nAsk a question or enter a query: "
    ).strip()

    if not query:

        print(
            "Please enter a query."
        )

        return

    # --------------------------------------------------------
    # Generate response
    # --------------------------------------------------------

    response = generate_response(
        data,
        query
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print()

    print(
        "-" * 60
    )

    print(
        "COALMIND AI GENERATED RESPONSE"
    )

    print(
        "-" * 60
    )

    print(
        response
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()