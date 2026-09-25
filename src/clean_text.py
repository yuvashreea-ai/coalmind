import os
import re

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FOLDER = os.path.join(BASE_FOLDER,"output")
INPUT_FILE = os.path.join(OUTPUT_FOLDER,"srn-jan-2025.txt")
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER,"cleaned_srn-jan-2025.txt")
REVIEW_FILE = os.path.join(OUTPUT_FOLDER,"cleaning_review.txt")


# ---------------------------------------------------------
# PAGE / HEADING DETECTION
# ---------------------------------------------------------

def is_page_marker(line):
    return bool(re.fullmatch(r"\s*PAGE\s+\d+\s*", line, re.IGNORECASE))


def is_table_heading(line):
    return bool(
        re.search(
            r"\bTable\s+\d+(?:\.\d+)*",
            line,
            re.IGNORECASE
        )
    )


def is_source_or_note(line):
    return bool(
        re.match(
            r"\s*(Source|Note)\s*:",
            line,
            re.IGNORECASE
        )
    )


# ---------------------------------------------------------
# CHART NOISE
# ---------------------------------------------------------

def is_chart_noise(line):

    stripped = line.strip()

    if not stripped:
        return False

    # Never remove important lines
    if is_page_marker(stripped):
        return False

    if is_table_heading(stripped):
        return False

    if is_source_or_note(stripped):
        return False

    if re.match(r"^(Government|Ministry|CIL|SCCL|NLCIL)", stripped):
        return False

    # Only-symbol lines
    if re.fullmatch(r"[\W_]+", stripped):
        return True

    # Very short chart fragments
    if len(stripped) <= 3 and not re.search(r"\d", stripped):
        if stripped.upper() not in {
            "CIL",
            "ECL",
            "BCCL",
            "CCL",
            "NCL",
            "WCL",
            "SECL",
            "MCL",
            "SCCL"
        }:
            return True

    # Lines dominated by symbols
    alphanumeric = len(re.findall(r"[A-Za-z0-9]", stripped))
    total = len(stripped)

    if total > 5 and alphanumeric / total < 0.20:
        return True

    # Obvious chart fragments
    chart_patterns = [
        r"^[Ss]\s+is$",
        r"^é\s*=\s*\d+$",
        r"^sin\s+MT$",
        r"^In\s+MT$",
        r"^No\s+of$",
        r"^[a-zA-Z]\s*[=>]+\s*[-_]+$",
    ]

    for pattern in chart_patterns:
        if re.fullmatch(pattern, stripped, re.IGNORECASE):
            return True

    return False


# ---------------------------------------------------------
# TABLE DETECTION
# ---------------------------------------------------------

def looks_like_table_row(line):

    stripped = line.strip()

    if not stripped:
        return False

    # Multiple numeric values strongly indicate a table row
    numbers = re.findall(
        r"\b\d+(?:[.,]\d+)?\b",
        stripped
    )

    if len(numbers) >= 2:
        return True

    # Common table row keywords
    keywords = [
        "Grand Total",
        "Total",
        "Big Mines",
        "Other Mines",
        "Big Plus Mines",
        "Rest of Mines",
        "Captive/Others",
        "Power Utilities",
        "CPP",
    ]

    for keyword in keywords:
        if keyword.lower() in stripped.lower():
            return True

    return False


# ---------------------------------------------------------
# SAFE OCR CLEANING FOR TABLES
# ---------------------------------------------------------

def clean_table_line(line, review):

    original = line

    # Remove vertical table separators
    line = line.replace("|", " ")

    # Remove currency / copyright-like OCR artifacts
    line = re.sub(r"[¥£€©®™]", "", line)

    # -----------------------------------------------------
    # Fix OCR o/O inside numeric values
    # Example:
    # o.oo -> 0.00
    # 1o.20 -> 10.20
    # -----------------------------------------------------

    def fix_numeric_token(match):

        token = match.group(0)

        fixed = token

        # lowercase/uppercase O between digits
        fixed = re.sub(
            r"(?<=\d)[oO](?=\d)",
            "0",
            fixed
        )

        # O after decimal point
        fixed = re.sub(
            r"(?<=\.)[oO](?=\d)",
            "0",
            fixed
        )

        # O immediately before decimal
        fixed = re.sub(
            r"(?<=\d)[oO](?=\.)",
            "0",
            fixed
        )

        if fixed != token:
            review.append(
                f"OCR numeric correction: {token} -> {fixed}"
            )

        return fixed

    line = re.sub(
        r"\b[\dOo.,-]+\b",
        fix_numeric_token,
        line
    )

    # -----------------------------------------------------
    # Remove isolated OCR symbols around numbers
    #
    #  A 17.67 -> 17.67
    #  V 6.55  -> 6.55
    #  Vv 9.11 -> 9.11
    # -----------------------------------------------------

    line = re.sub(
        r"(?<=\s)[AVW]\s+(?=\d)",
        "",
        line
    )

    line = re.sub(
        r"(?<=\s)V[vV]\s+(?=\d)",
        "",
        line
    )

    # OCR symbols immediately before numbers
    line = re.sub(
        r"(?<![A-Za-z])[_^~]+\s*(?=\d)",
        "",
        line
    )

    # -----------------------------------------------------
    # Remove brackets accidentally attached to numbers
    # -----------------------------------------------------

    line = re.sub(
        r"(?<=\d)[\[\]}]+",
        "",
        line
    )

    line = re.sub(
        r"[\[\{]+(?=\d)",
        "",
        line
    )

    # -----------------------------------------------------
    # Underscores between numeric fields
    # -----------------------------------------------------

    line = re.sub(
        r"(?<=\d)_(?=\d)",
        " ",
        line
    )

    # -----------------------------------------------------
    # Remove isolated OCR junk between numeric fields
    # -----------------------------------------------------

    line = re.sub(
        r"(?<=\d)\s+[&^~]+\s+(?=\d)",
        " ",
        line
    )

    # -----------------------------------------------------
    # Clean repeated whitespace
    # -----------------------------------------------------

    line = re.sub(r"[ \t]+", " ", line)

    line = line.strip()

    # -----------------------------------------------------
    # Record suspicious merged numeric tokens
    #
    # DON'T automatically split them.
    # -----------------------------------------------------

    merged_numbers = re.findall(
        r"\b\d{2,4}\.\d{2,}\b",
        line
    )

    for value in merged_numbers:

        # Values with many digits before decimal are suspicious
        if len(value.split(".")[0]) >= 3:

            review.append(
                f"REVIEW merged/suspicious number: {value} | {line}"
            )

    if line != original:

        review.append(
            f"Cleaned: {original.strip()} -> {line}"
        )

    return line


# ---------------------------------------------------------
# NORMAL TEXT CLEANING
# ---------------------------------------------------------

def clean_normal_line(line):

    line = line.rstrip()

    # Remove excessive spaces
    line = re.sub(
        r"[ \t]{2,}",
        " ",
        line
    )

    # Known obvious OCR typo
    line = line.replace(
        "Inpt",
        "Input"
    )

    return line.strip()


# ---------------------------------------------------------
# MAIN CLEANING
# ---------------------------------------------------------

def clean_text(text):

    lines = text.splitlines()

    cleaned_lines = []

    removed_lines = []

    review_lines = []

    in_table = False
    table_gap = 0

    for line in lines:

        stripped = line.strip()

        # Blank line
        if not stripped:

            cleaned_lines.append("")

            if in_table:
                table_gap += 1

                # Leave table mode after several blank lines
                if table_gap >= 3:
                    in_table = False

            continue

        table_gap = 0

        # -------------------------------------------------
        # PAGE
        # -------------------------------------------------

        if is_page_marker(stripped):

            cleaned_lines.append(
                re.sub(
                    r"\s+",
                    " ",
                    stripped
                )
            )

            in_table = False
            continue

        # -------------------------------------------------
        # TABLE HEADING
        # -------------------------------------------------

        if is_table_heading(stripped):

            cleaned_lines.append(stripped)

            in_table = True
            continue

        # -------------------------------------------------
        # SOURCE / NOTE
        # -------------------------------------------------

        if is_source_or_note(stripped):

            cleaned_lines.append(
                clean_normal_line(stripped)
            )

            continue

        # -------------------------------------------------
        # CHART NOISE
        # -------------------------------------------------

        if not in_table and is_chart_noise(stripped):

            removed_lines.append(stripped)

            continue

        # -------------------------------------------------
        # TABLE ROW
        # -------------------------------------------------

        if in_table or looks_like_table_row(stripped):

            cleaned = clean_table_line(
                stripped,
                review_lines
            )

            if cleaned:

                cleaned_lines.append(cleaned)

            continue

        # -------------------------------------------------
        # NORMAL TEXT
        # -------------------------------------------------

        cleaned = clean_normal_line(stripped)

        if cleaned:

            cleaned_lines.append(cleaned)

    # Remove excessive blank lines
    result = "\n".join(cleaned_lines)

    result = re.sub(
        r"\n{3,}",
        "\n\n",
        result
    )

    return result.strip(), removed_lines, review_lines


# ---------------------------------------------------------
# FILE PROCESSING
# ---------------------------------------------------------

def process_text_file(input_file):
    """
    Clean one OCR-generated TXT file.

    Returns:
        Path of the cleaned TXT file
        Path of the cleaning review file
    """

    if not os.path.exists(input_file):

        print("Input TXT file not found!")
        print(input_file)

        return None, None

    # Read OCR text
    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    # Perform cleaning
    cleaned, removed, review = clean_text(text)

    # Get original filename
    filename = os.path.splitext(
        os.path.basename(input_file)
    )[0]

    # Create output filenames dynamically
    output_file = os.path.join(
        OUTPUT_FOLDER,
        f"cleaned_{filename}.txt"
    )

    review_file = os.path.join(
        OUTPUT_FOLDER,
        f"cleaning_review_{filename}.txt"
    )

    # Save cleaned text
    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(cleaned)

    # Save review information
    with open(
        review_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "OCR CLEANING REVIEW\n"
        )

        file.write(
            "=" * 60 + "\n\n"
        )

        file.write(
            "LINES REMOVED AS CHART / OCR NOISE\n"
        )

        file.write(
            "-" * 60 + "\n"
        )

        for item in removed:
            file.write(item + "\n")

        file.write(
            "\n\nOCR CORRECTIONS AND SUSPICIOUS VALUES\n"
        )

        file.write(
            "-" * 60 + "\n"
        )

        for item in review:
            file.write(item + "\n")

    print("\nText cleaning completed!")

    print(f"Input  : {input_file}")
    print(f"Output : {output_file}")
    print(f"Review : {review_file}")

    print(f"\nRemoved lines  : {len(removed)}")
    print(f"Review entries : {len(review)}")

    return output_file, review_file


def main():

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # Find OCR-generated TXT files
    txt_files = [
        file
        for file in os.listdir(OUTPUT_FOLDER)
        if file.lower().endswith(".txt")
        and not file.startswith("cleaned_")
        and not file.startswith("cleaning_review")
        and not file.startswith("validated_")
        and not file.startswith("ocr_validation")
    ]

    if not txt_files:

        print("No OCR TXT file found.")

        return

    for txt_file in txt_files:

        input_file = os.path.join(
            OUTPUT_FOLDER,
            txt_file
        )

        process_text_file(input_file)


if __name__ == "__main__":
    main()