import os
import json


def load_structured_data(json_file):
    """
    Load structured data generated from the uploaded PDF.
    """

    if not json_file:
        print("No structured JSON file provided.")
        return None

    if not os.path.exists(json_file):
        print("Structured JSON not found!")
        print(json_file)
        return None

    try:
        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as error:
        print("Error loading structured JSON:")
        print(error)
        return None


def search_document(data, query):
    """
    Search the uploaded document.

    Searches:
    - Normal page text
    - Table titles
    - Table rows
    """

    if not data:
        return []

    query = query.lower().strip()

    if not query:
        return []

    results = []

    for page in data.get("pages", []):

        page_number = page.get("page")

        # =================================================
        # SEARCH NORMAL PAGE TEXT
        # =================================================

        page_text = str(
            page.get("text", "")
        )

        matching_text_lines = []

        for line in page_text.splitlines():

            line = line.strip()

            if line and query in line.lower():

                matching_text_lines.append(line)

        # =================================================
        # SEARCH TABLES
        # =================================================

        table_results = []

        for table in page.get("tables", []):

            title = str(
                table.get("title", "")
            )

            rows = table.get(
                "rows",
                []
            )

            # ---------------------------------------------
            # CHECK TABLE TITLE
            # ---------------------------------------------

            title_match = (
                query in title.lower()
            )

            # ---------------------------------------------
            # CHECK TABLE ROWS
            # ---------------------------------------------

            matching_rows = []

            for row in rows:

                row_text = str(row)

                if query in row_text.lower():

                    matching_rows.append(
                        row_text
                    )

            # ---------------------------------------------
            # STORE TABLE RESULT
            # ---------------------------------------------

            if title_match or matching_rows:

                table_results.append({

                    "page": page_number,

                    "title": title,

                    "rows": matching_rows,

                    "title_match": title_match

                })

        # =================================================
        # ADD PAGE TEXT RESULT
        # =================================================

        if matching_text_lines:

            results.append({

                "page": page_number,

                "title": "Page Text",

                "rows": matching_text_lines,

                "title_match": False

            })

        # =================================================
        # ADD TABLE RESULTS
        # =================================================

        results.extend(
            table_results
        )

    return results


def search_json_file(json_file, query):
    """
    Load a structured JSON file and search it.
    """

    data = load_structured_data(
        json_file
    )

    if data is None:

        return []

    return search_document(
        data,
        query
    )


def main():

    print("\n========================================")
    print("             COALMIND SEARCH")
    print("========================================")

    # For testing from terminal only

    json_file = input(
        "\nEnter structured JSON file path: "
    ).strip()

    query = input(
        "Enter search term: "
    ).strip()

    if not query:

        print(
            "Please enter a search term."
        )

        return

    results = search_json_file(
        json_file,
        query
    )

    print(
        f"\nResults found: {len(results)}"
    )

    if not results:

        print(
            "No matching information found."
        )

        return

    for result in results:

        print(
            "\n----------------------------------------"
        )

        print(
            f"Page : {result['page']}"
        )

        print(
            f"Section: {result['title']}"
        )

        if result["title_match"]:

            print(
                "Title matched."
            )

        if result["rows"]:

            print(
                "Matching information:"
            )

            for row in result["rows"]:

                print(
                    f"  {row}"
                )


if __name__ == "__main__":

    main()