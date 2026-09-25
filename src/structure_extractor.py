import os
import re
import json


OUTPUT_FOLDER = r"C:\coalmind\output"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def is_page_marker(line):
    """
    Detect PAGE markers.

    Examples:
        PAGE 1
        PAGE 25
    """

    return bool(
        re.fullmatch(
            r"\s*PAGE\s+\d+\s*",
            line,
            re.IGNORECASE
        )
    )


def is_source_line(line):
    """
    Detect source lines.

    Examples:
        Source: CIL
        Source: DGCI & S
        Source: ICMW
    """

    return bool(
        re.match(
            r"^\s*Source\s*:",
            line,
            re.IGNORECASE
        )
    )


def is_page_number_only(line):
    """
    Detect standalone page numbers.
    """

    return bool(
        re.fullmatch(
            r"\s*\d+\s*",
            line
        )
    )


# =========================================================
# TABLE TITLE DETECTION
# =========================================================

def is_explicit_table_title(line):
    """
    Detect explicit table titles.

    Examples:
        Table 1.1
        Table 2.1.1 (A)
        Table 8.10:
    """

    line = line.strip()

    return bool(
        re.match(
            r"^Table\s+[\dIVX]+(?:[.\dA-Za-z()_-]*)?",
            line,
            re.IGNORECASE
        )
    )


def is_known_table_title(line):
    """
    Detect common table titles/headings used in
    Coal India / Ministry of Coal reports.

    This function is intentionally conservative.
    """

    line = line.strip()

    if not line:
        return False

    upper = line.upper()

    keywords = [

        # Coal / lignite
        "COAL IMPORT",
        "COAL IMPORTS",
        "COAL AND LIGNITE PRODUCTION",
        "LIGNITE PRODUCTION",
        "LIGNITE DISPATCH",
        "COAL DISPATCH",
        "COAL DESPATCH",
        "COAL OFF-TAKE",
        "COAL OFFTAKE",

        # Sector / company
        "SECTOR-WISE COAL",
        "SECTOR WISE COAL",
        "SECTOR-WISE DEMAND",
        "SECTOR WISE DEMAND",
        "SECTOR-WISE OFFTAKE",
        "SECTOR WISE OFFTAKE",
        "COMPANY WISE COAL DISPATCH",
        "COMPANY-WISE COAL DISPATCH",

        # Production
        "PRODUCTION STATUS",
        "PRODUCTIVITY IN",
        "OUTPUT PER MANSHIFT",
        "OUTPUT PER MAN SHIFT",

        # OBR
        "OBR DURING",
        "OBR UPT O",
        "OBR UPT",
        "TOTAL OBR",
        "DEPARTMENTAL OBR",
        "CONTRACTUAL OBR",

        # Dispatch
        "MODE-WISE DESPATCH",
        "MODE WISE DESPATCH",
        "MODE-WISE DISPATCH",
        "MODE WISE DISPATCH",

        # Finance
        "CAPITAL EXPENDITURE",
        "NAME OF EXPENDITURE",
        "HEAD-WISE CAPITAL EXPENDITURE",
        "HEAD WISE CAPITAL EXPENDITURE",

        # Power
        "POWER SALES",
        "POWER GENERATION",
        "PRODUCTION OF POWER",
        "SOURCE-WISE POWER",

        # Manpower
        "TOTAL MANPOWER",
        "MANPOWER OF CIL",

        # Debtors
        "AGE-WISE DEBTORS",
        "AGE WISE DEBTORS",
        "DEBTORS DUE",
        "DEBTORS DUES",
        "TOTAL DEBTORS",

        # Stock
        "VENDIBLE COAL STOCK",

        # Import
        "PORT-WISE",
        "PORT WISE",
        "COUNTRY-WISE",
        "COUNTRY WISE",
        "GRADE-WISE",
        "GRADE WISE",
        "AVERAGE PRICE OF IMPORTED",
        "SECTOR WISE COAL AND COKE IMPORT",

        # HEMM
        "HEMM UTILISATION",
        "HEMM UTILIZATION"
    ]

    for keyword in keywords:

        if keyword in upper:
            return True

    return False


def is_numbered_section_heading(line):
    """
    Detect ordinary numbered report sections.

    Examples:
        4. Lignite Production
        6. Output per Manshift
        11. Commencement of OBR

    These should NOT automatically become tables.
    """

    line = line.strip()

    return bool(
        re.match(
            r"^\d{1,2}\.\s+[A-Za-z]",
            line
        )
    )


def is_table_heading(line):
    """
    Main table heading detector.

    Explicit Table titles are always accepted.

    Other headings are accepted only when they contain
    strong table-related terminology.
    """

    line = line.strip()

    if not line:
        return False

    # Explicit Table heading
    if is_explicit_table_title(line):
        return True

    # Strong known table heading
    if is_known_table_title(line):
        return True

    return False


# =========================================================
# NUMERIC DETECTION
# =========================================================

NUMBER_PATTERN = re.compile(
    r"""
    (?:
        # Number with comma separators
        \d{1,3}(?:,\d{2,3})+(?:\.\d+)?

        |

        # Decimal / integer
        \d+(?:\.\d+)?

        |

        # Percentage
        \d+(?:\.\d+)?%

        |

        # Negative number
        -\d+(?:\.\d+)?
    )
    """,
    re.VERBOSE
)


def numeric_tokens(line):
    """
    Return numeric-looking tokens from a line.
    """

    return NUMBER_PATTERN.findall(line)


def count_numbers(line):
    """
    Count numeric-looking values.
    """

    return len(
        numeric_tokens(line)
    )


def contains_year(line):
    """
    Detect report year values.

    Examples:
        2024
        2025
        2024-25
        2025-26
    """

    return bool(
        re.search(
            r"\b20\d{2}(?:[-/]\d{2,4})?\b",
            line
        )
    )


# =========================================================
# TABLE ROW DETECTION
# =========================================================

def looks_like_table_row(line):
    """
    Decide whether an OCR line is likely a data row.

    The rule is intentionally permissive because OCR
    tables are often broken across lines.

    Important:
    A table row can contain only ONE number.

    Example:
        NLC 125.50

    Therefore we do not require two numbers anymore.
    """

    line = line.strip()

    if not line:
        return False

    # Do not classify obvious headings as rows
    if is_table_heading(line):
        return False

    if is_source_line(line):
        return False

    if is_page_number_only(line):
        return False

    # -----------------------------------------------------
    # Avoid normal report sentences
    # -----------------------------------------------------

    lower = line.lower()

    # Long prose is normally not a table row
    words = line.split()

    if len(words) > 35 and count_numbers(line) < 2:
        return False

    # -----------------------------------------------------
    # Strong numeric signal
    # -----------------------------------------------------

    numbers = count_numbers(line)

    if numbers >= 2:
        return True

    # -----------------------------------------------------
    # One numeric value + useful text
    # -----------------------------------------------------

    if numbers == 1:

        # Short line containing text + number
        if len(words) <= 20:
            return True

        # Year-related line
        if contains_year(line):
            return True

        # Percentage-related line
        if "%" in line:
            return True

    # -----------------------------------------------------
    # Year-only combinations
    # -----------------------------------------------------

    if contains_year(line):

        # Avoid very long prose
        if len(words) <= 20:
            return True

    return False


# =========================================================
# TABLE HEADER DETECTION
# =========================================================

def looks_like_table_header(line):
    """
    Detect likely table header lines.

    Headers may contain no numbers.
    """

    line_lower = line.lower().strip()

    if not line_lower:
        return False

    header_keywords = [

        "year",
        "company",
        "sector",
        "subsidiary",
        "actual",
        "target",
        "achievement",
        "total",
        "growth",
        "figure",
        "fig.",
        "quantity",
        "qty",
        "production",
        "dispatch",
        "despatch",
        "expenditure",
        "power",
        "coal",
        "lignite",
        "rate",
        "product",
        "month",
        "upto",
        "upto january",
        "during",
        "jan",
        "january",
        "apr",
        "march",
        "financial year",
        "grade",
        "port",
        "country",
        "price",
        "value",
        "manpower",
        "departmental",
        "contractual",
        "coking",
        "non-coking",
        "stock"
    ]

    matches = 0

    for keyword in header_keywords:

        if keyword in line_lower:
            matches += 1

    # Strong multi-keyword header
    if matches >= 2:
        return True

    # Some short single-keyword headers are valid
    if matches == 1 and len(line_lower.split()) <= 6:
        return True

    return False


# =========================================================
# TABLE CONTINUATION / TITLE LOGIC
# =========================================================

def is_probable_table_continuation(line):
    """
    Detect lines that are probably continuation text belonging
    to the current table rather than a new table.

    Examples:
        OBR during Jan OBR during the year
        Coal Despatch during Jan'25 Coal Despatch upto Jan'25
        in Lakh Te
        All Figures in MT
        during Jan'2025
    """

    line = line.strip()

    if not line:
        return False

    lower = line.lower()

    continuation_keywords = [

        "during",
        "upto",
        "up to",
        "all figures",
        "all figur",
        "in mt",
        "in lakh",
        "in mm",
        "in cr",
        "in mu",
        "fig.",
        "fig in",
        "figure",
        "growth",
        "actual",
        "target",
        "achievement",
        "jan'",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december"
    ]

    for keyword in continuation_keywords:

        if keyword in lower:
            return True

    return False


def is_strong_new_section(line):
    """
    Detect a strong non-table section heading.

    This prevents normal report sections from being
    absorbed into an existing table.
    """

    line = line.strip()

    if not line:
        return False

    # Explicitly numbered report section
    if is_numbered_section_heading(line):

        # Explicit table titles are handled separately
        if is_table_heading(line):
            return False

        return True

    return False


def should_start_new_table(line, current_table):
    """
    Decide whether a line starts a new table.

    A table title starts a new table only if it is not
    simply a continuation of the current table.
    """

    if not line.strip():
        return False

    # No current table -> normal title detection
    if current_table is None:
        return is_table_heading(line)

    # If an explicit Table title appears, start a new table
    if is_explicit_table_title(line):

        # But don't split if it is exactly the same title
        if line.strip().lower() == current_table["title"].strip().lower():
            return False

        return True

    # Known headings inside a current table may be
    # continuation lines rather than new tables.
    if is_known_table_title(line):

        lower = line.lower()

        current_title = (
            current_table.get("title", "")
            .lower()
        )

        # Same conceptual table
        if (
            "obr" in lower
            and "obr" in current_title
        ):
            return False

        if (
            "coal dispatch" in lower
            and "coal dispatch" in current_title
        ):
            return False

        if (
            "despatch" in lower
            and "despatch" in current_title
        ):
            return False

        if (
            "production" in lower
            and "production" in current_title
        ):
            return False

        return True

    return False


# =========================================================
# TABLE CLEANUP
# =========================================================

def clean_table(table):
    """
    Clean and normalize a detected table before saving JSON.
    """

    # -----------------------------------------------------
    # Remove duplicate consecutive headers
    # -----------------------------------------------------

    cleaned_header = []

    previous = None

    for line in table.get("header", []):

        line = line.strip()

        if not line:
            continue

        if line == previous:
            continue

        cleaned_header.append(line)

        previous = line

    table["header"] = cleaned_header

    # -----------------------------------------------------
    # Remove duplicate consecutive rows
    # -----------------------------------------------------

    cleaned_rows = []

    previous = None

    for line in table.get("rows", []):

        line = line.strip()

        if not line:
            continue

        if line == previous:
            continue

        cleaned_rows.append(line)

        previous = line

    table["rows"] = cleaned_rows

    # -----------------------------------------------------
    # Clean source
    # -----------------------------------------------------

    if table.get("source"):

        table["source"] = table["source"].strip()

    return table


# =========================================================
# TABLE EXTRACTION
# =========================================================

def extract_tables_from_lines(lines):
    """
    Extract tables while preserving page text.

    Important design:

    - Table title starts a table.
    - Multi-line headers stay with the same table.
    - Numeric rows are retained.
    - One-number rows are allowed.
    - OCR continuation lines are retained.
    - Normal numbered sections terminate the table.
    - Source lines terminate the table.
    """

    tables = []
    page_text = []

    current_table = None
    table_content_started = False

    for index, raw_line in enumerate(lines):

        line = raw_line.strip()

        if not line:
            continue

        # =================================================
        # PAGE NUMBER
        # =================================================

        if is_page_number_only(line):

            # Page numbers are not useful table content
            continue

        # =================================================
        # SOURCE
        # =================================================

        if is_source_line(line):

            page_text.append(line)

            if current_table is not None:

                current_table["source"] = line

                current_table = clean_table(
                    current_table
                )

                if (
                    current_table["header"]
                    or current_table["rows"]
                ):

                    tables.append(
                        current_table
                    )

                current_table = None
                table_content_started = False

            continue

        # =================================================
        # NEW TABLE TITLE
        # =================================================

        if should_start_new_table(
            line,
            current_table
        ):

            # -------------------------------------------------
            # Close previous table
            # -------------------------------------------------

            if current_table is not None:

                current_table = clean_table(
                    current_table
                )

                if (
                    current_table["header"]
                    or current_table["rows"]
                ):

                    tables.append(
                        current_table
                    )

            # -------------------------------------------------
            # Start new table
            # -------------------------------------------------

            current_table = {

                "title": line,

                "header": [],

                "rows": [],

                "source": None

            }

            page_text.append(line)

            table_content_started = False

            continue

        # =================================================
        # CURRENT TABLE EXISTS
        # =================================================

        if current_table is not None:

            # -------------------------------------------------
            # Strong section heading
            # -------------------------------------------------

            if is_strong_new_section(line):

                # Close table
                current_table = clean_table(
                    current_table
                )

                if (
                    current_table["header"]
                    or current_table["rows"]
                ):

                    tables.append(
                        current_table
                    )

                current_table = None
                table_content_started = False

                # Preserve section text
                page_text.append(line)

                continue

            # -------------------------------------------------
            # Header before data starts
            # -------------------------------------------------

            if not table_content_started:

                # Header
                if looks_like_table_header(line):

                    current_table[
                        "header"
                    ].append(line)

                    page_text.append(line)

                    continue

                # Numeric data begins
                if looks_like_table_row(line):

                    current_table[
                        "rows"
                    ].append(line)

                    page_text.append(line)

                    table_content_started = True

                    continue

                # -------------------------------------------------
                # Possible continuation/title/header text
                # -------------------------------------------------

                if is_probable_table_continuation(line):

                    current_table[
                        "header"
                    ].append(line)

                    page_text.append(line)

                    continue

                # -------------------------------------------------
                # Short non-numeric line immediately after
                # title is probably another header line.
                # -------------------------------------------------

                if len(line.split()) <= 15:

                    current_table[
                        "header"
                    ].append(line)

                    page_text.append(line)

                    continue

                # -------------------------------------------------
                # Long prose means table has not really started.
                # Preserve as page text but don't force into table.
                # -------------------------------------------------

                page_text.append(line)

                continue

            # =================================================
            # TABLE DATA HAS STARTED
            # =================================================

            # -------------------------------------------------
            # New explicit table title
            # -------------------------------------------------

            if is_explicit_table_title(line):

                current_table = clean_table(
                    current_table
                )

                if (
                    current_table["header"]
                    or current_table["rows"]
                ):

                    tables.append(
                        current_table
                    )

                current_table = {

                    "title": line,

                    "header": [],

                    "rows": [],

                    "source": None

                }

                page_text.append(line)

                table_content_started = False

                continue

            # -------------------------------------------------
            # Data row
            # -------------------------------------------------

            if looks_like_table_row(line):

                current_table[
                    "rows"
                ].append(line)

                page_text.append(line)

                continue

            # -------------------------------------------------
            # Continuation line
            #
            # OCR can split table rows.
            # -------------------------------------------------

            if is_probable_table_continuation(line):

                current_table[
                    "rows"
                ].append(line)

                page_text.append(line)

                continue

            # -------------------------------------------------
            # Short text after data can be part of OCR row.
            # -------------------------------------------------

            if len(line.split()) <= 8:

                current_table[
                    "rows"
                ].append(line)

                page_text.append(line)

                continue

            # -------------------------------------------------
            # Otherwise this is normal page text.
            #
            # Do NOT automatically append long prose to table.
            # -------------------------------------------------

            page_text.append(line)

            continue

        # =================================================
        # NORMAL PAGE TEXT
        # =================================================

        page_text.append(line)

    # =====================================================
    # CLOSE LAST TABLE
    # =====================================================

    if current_table is not None:

        current_table = clean_table(
            current_table
        )

        if (
            current_table["header"]
            or current_table["rows"]
        ):

            tables.append(
                current_table
            )

    return tables, page_text


# =========================================================
# PAGE EXTRACTION
# =========================================================

def extract_structure(text):

    pages = []

    # -----------------------------------------------------
    # PAGE marker pattern
    # -----------------------------------------------------

    page_pattern = re.compile(
        r"^\s*PAGE\s+(\d+)\s*$",
        re.IGNORECASE | re.MULTILINE
    )

    matches = list(
        page_pattern.finditer(text)
    )

    print(
        f"Page markers found: {len(matches)}"
    )

    # -----------------------------------------------------
    # No PAGE markers
    # -----------------------------------------------------

    if not matches:

        print(
            "Warning: No PAGE markers found."
        )

        return pages

    # -----------------------------------------------------
    # Process pages
    # -----------------------------------------------------

    for index, match in enumerate(matches):

        page_number = int(
            match.group(1)
        )

        start = match.end()

        if index + 1 < len(matches):

            end = matches[
                index + 1
            ].start()

        else:

            end = len(text)

        page_content = text[
            start:end
        ].strip()

        # -------------------------------------------------
        # Clean lines
        # -------------------------------------------------

        lines = []

        for raw_line in page_content.splitlines():

            line = raw_line.strip()

            if line:

                lines.append(line)

        # -------------------------------------------------
        # Extract tables
        # -------------------------------------------------

        tables, page_text = extract_tables_from_lines(
            lines
        )

        # -------------------------------------------------
        # Remove duplicate consecutive page text
        # -------------------------------------------------

        cleaned_page_text = []

        previous_line = None

        for line in page_text:

            if line == previous_line:
                continue

            cleaned_page_text.append(line)

            previous_line = line

        # -------------------------------------------------
        # Add page
        # -------------------------------------------------

        pages.append({

            "page": page_number,

            "text": "\n".join(
                cleaned_page_text
            ),

            "tables": tables

        })

    return pages


# =========================================================
# PROCESS ONE VALIDATED FILE
# =========================================================

def process_validated_file(input_file):

    if not os.path.exists(
        input_file
    ):

        print(
            "\nInput file not found!"
        )

        print(
            input_file
        )

        return None

    # -----------------------------------------------------
    # Read validated OCR text
    # -----------------------------------------------------

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    # -----------------------------------------------------
    # Extract structure
    # -----------------------------------------------------

    pages = extract_structure(
        text
    )

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    total_tables = 0
    total_rows = 0

    for page in pages:

        total_tables += len(
            page["tables"]
        )

        for table in page["tables"]:

            total_rows += len(
                table["rows"]
            )

    # -----------------------------------------------------
    # Output filename
    # -----------------------------------------------------

    filename = os.path.splitext(
        os.path.basename(
            input_file
        )
    )[0]

    if filename.startswith(
        "validated_"
    ):

        filename = filename[
            len("validated_"):
        ]

    output_file = os.path.join(

        OUTPUT_FOLDER,

        f"structured_{filename}.json"

    )

    # -----------------------------------------------------
    # JSON result
    # -----------------------------------------------------

    result = {

        "document": {

            "file": os.path.basename(
                input_file
            ),

            "pages_processed": len(
                pages
            ),

            "tables_detected": total_tables,

            "rows_extracted": total_rows

        },

        "pages": pages

    }

    # -----------------------------------------------------
    # Save JSON
    # -----------------------------------------------------

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(

            result,

            file,

            indent=4,

            ensure_ascii=False

        )

    # -----------------------------------------------------
    # Display result
    # -----------------------------------------------------

    print(
        "\nDocument structure extraction completed!"
    )

    print(
        f"Input file    : {input_file}"
    )

    print(
        f"Pages detected : {len(pages)}"
    )

    print(
        f"Tables detected: {total_tables}"
    )

    print(
        f"Rows extracted : {total_rows}"
    )

    print(
        "\nOutput saved to:"
    )

    print(
        output_file
    )

    # -----------------------------------------------------
    # Display table details
    # -----------------------------------------------------

    print(
        "\nDetected table details:"
    )

    if not total_tables:

        print(
            "No tables detected."
        )

    else:

        for page in pages:

            for table in page["tables"]:

                print(
                    f"\nPage {page['page']}: "
                    f"{table['title']}"
                )

                print(
                    f"Header lines: "
                    f"{len(table['header'])}"
                )

                print(
                    f"Rows: "
                    f"{len(table['rows'])}"
                )

                if table.get("source"):

                    print(
                        f"Source: "
                        f"{table['source']}"
                    )

    return output_file


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # Ensure output folder exists
    # -----------------------------------------------------

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Find validated TXT files
    # -----------------------------------------------------

    txt_files = [

        file

        for file in os.listdir(
            OUTPUT_FOLDER
        )

        if file.lower().endswith(
            ".txt"
        )

        and file.startswith(
            "validated_"
        )

    ]

    # -----------------------------------------------------
    # No validated files
    # -----------------------------------------------------

    if not txt_files:

        print(
            "No validated OCR TXT file found."
        )

        return

    # -----------------------------------------------------
    # Process all validated files
    # -----------------------------------------------------

    for txt_file in sorted(txt_files):

        input_file = os.path.join(

            OUTPUT_FOLDER,

            txt_file

        )

        print(
            "\n"
            + "=" * 60
        )

        print(
            f"Processing: {txt_file}"
        )

        print(
            "=" * 60
        )

        process_validated_file(
            input_file
        )


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()