import os
import re

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FOLDER = os.path.join(BASE_FOLDER,"output")
INPUT_FILE = os.path.join(OUTPUT_FOLDER,"cleaned_srn-jan-2025.txt")
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER,"validated_srn-jan-2025_v2.txt")
REPORT_FILE = os.path.join(OUTPUT_FOLDER,"ocr_validation_report_v2.txt")


# ---------------------------------------------------------
# Detect whether a line looks like a table row
# ---------------------------------------------------------
def looks_like_table_row(line):
    if not line.strip():
        return False

    numeric_tokens = re.findall(
        r"\b\d+(?:[.,]\d+)*\b",
        line
    )

    return len(numeric_tokens) >= 3


# ---------------------------------------------------------
# Detect OCR corruption attached to numbers
# ---------------------------------------------------------
def find_attached_ocr_errors(line):
    issues = []

    patterns = [
        r"\b[A-Za-z]+[-_]?\d+(?:\.\d+)?\b",
        r"\b\d+(?:\.\d+)?[A-Za-z]+\b",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, line)

        for match in matches:

            if match.upper() in {
                "FY24",
                "FY25",
                "FY26",
            }:
                continue

            if re.match(
                r"^(TABLE|PAGE)\d*$",
                match.upper()
            ):
                continue

            issues.append(
                f"Attached letters/numbers: '{match}'"
            )

    return issues


# ---------------------------------------------------------
# Detect malformed numeric values
# ---------------------------------------------------------
def find_malformed_numbers(line):
    issues = []

    tokens = line.split()

    for token in tokens:

        cleaned = token.strip(
            ",;:()[]{}"
        )

        if cleaned.count(".") > 1:

            if not re.search(
                r"\d",
                cleaned
            ):
                continue

            issues.append(
                f"Multiple decimal points: '{token}'"
            )

        if cleaned.count(",") > 1:

            if re.fullmatch(
                r"[\d,]+",
                cleaned
            ):
                issues.append(
                    f"Suspicious numeric commas: '{token}'"
                )

    return issues


# ---------------------------------------------------------
# Detect numbers that appear to have been merged together
# ---------------------------------------------------------
def find_possible_merged_numbers(line):
    issues = []

    tokens = line.split()

    for token in tokens:

        cleaned = token.strip(
            ",;:()[]{}"
        )

        match = re.fullmatch(
            r"(\d{5,})\.(\d+)",
            cleaned
        )

        if match:

            issues.append(
                f"Possible merged number: '{token}'"
            )

    return issues


# ---------------------------------------------------------
# Detect suspicious characters inside table rows
# ---------------------------------------------------------
def find_symbol_number_problems(line):
    issues = []

    suspicious = re.findall(
        r"\b(?:[A-Za-z][0-9]+|[0-9]+[A-Za-z])\b",
        line
    )

    for item in suspicious:

        if item.upper() in {
            "FY24",
            "FY25",
            "FY26",
            "MT",
        }:
            continue

        issues.append(
            f"Possible OCR character substitution: '{item}'"
        )

    return issues


# ---------------------------------------------------------
# Validate the complete file
# ---------------------------------------------------------
def validate_text(text):

    lines = text.splitlines()

    validated_lines = []
    report_lines = []

    table_rows = 0
    rows_with_issues = 0
    total_issues = 0

    current_page = "Unknown"
    current_table = "Unknown"

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        stripped = line.strip()

        # Track page
        page_match = re.search(
            r"PAGE\s+(\d+)",
            stripped,
            re.IGNORECASE
        )

        if page_match:
            current_page = page_match.group(1)

        # Track table heading
        if re.search(
            r"\bTABLE\s+\d",
            stripped,
            re.IGNORECASE
        ):
            current_table = stripped

        issues = []

        # Detailed validation for table-like rows
        if looks_like_table_row(stripped):

            table_rows += 1

            issues.extend(
                find_attached_ocr_errors(
                    stripped
                )
            )

            issues.extend(
                find_malformed_numbers(
                    stripped
                )
            )

            issues.extend(
                find_possible_merged_numbers(
                    stripped
                )
            )

            issues.extend(
                find_symbol_number_problems(
                    stripped
                )
            )

        # Remove duplicate issues
        issues = list(
            dict.fromkeys(issues)
        )

        if issues:

            rows_with_issues += 1
            total_issues += len(issues)

            report_lines.append(
                f"Line {line_number} | Page {current_page}"
            )

            report_lines.append(
                f"Table: {current_table}"
            )

            report_lines.append(
                f"Original: {stripped}"
            )

            report_lines.append(
                "Issues:"
            )

            for issue in issues:

                report_lines.append(
                    f"  - {issue}"
                )

            report_lines.append(
                "-" * 70
            )

        # IMPORTANT:
        # Original text is never automatically modified.
        validated_lines.append(line)

    # -----------------------------------------------------
    # CALCULATE VALIDATION QUALITY
    # -----------------------------------------------------

    if table_rows > 0:

        clean_rows = (
            table_rows - rows_with_issues
        )

        validation_quality = (
            clean_rows / table_rows
        ) * 100

    else:

        validation_quality = 100.0

    return (
        "\n".join(validated_lines),
        report_lines,
        table_rows,
        rows_with_issues,
        total_issues,
        validation_quality
    )


# ---------------------------------------------------------
# FILE PROCESSING
# ---------------------------------------------------------


def process_text_file(input_file):

    if not os.path.exists(input_file):

        print("Input file not found!")
        print(input_file)

        return None, None

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as file:

        text = file.read()

    (
        validated_text,
        report_lines,
        table_rows,
        rows_with_issues,
        total_issues,
        validation_quality
    ) = validate_text(text)

    # Get original filename
    filename = os.path.splitext(
        os.path.basename(input_file)
    )[0]

    # Dynamic output filenames
    output_file = os.path.join(
        OUTPUT_FOLDER,
        f"validated_{filename}.txt"
    )

    report_file = os.path.join(
        OUTPUT_FOLDER,
        f"ocr_validation_report_{filename}.txt"
    )

    # -----------------------------------------------------
    # Save validated copy
    # -----------------------------------------------------

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            validated_text
        )

    # -----------------------------------------------------
    # Create validation report
    # -----------------------------------------------------

    with open(
        report_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "============================================================\n"
        )

        file.write(
            "OCR VALIDATION REPORT - VERSION 2\n"
        )

        file.write(
            "============================================================\n\n"
        )

        file.write(
            "This validation stage does NOT automatically change "
            "questionable numbers.\n"
        )

        file.write(
            "It only identifies OCR patterns that require review.\n\n"
        )

        file.write(
            f"Table-like rows inspected : {table_rows}\n"
        )

        file.write(
            f"Rows requiring review     : {rows_with_issues}\n"
        )

        file.write(
            f"Rows without detected issues : "
            f"{table_rows - rows_with_issues}\n"
        )

        file.write(
            f"Possible OCR issues       : {total_issues}\n"
        )

        file.write(
            f"Validation Quality        : "
            f"{validation_quality:.2f}%\n\n"
        )

        file.write(
            "IMPORTANT:\n"
        )

        file.write(
            "- Validation Quality is based on table-like rows "
            "without detected suspicious patterns.\n"
        )

        file.write(
            "- It is NOT the same as ground-truth OCR accuracy.\n"
        )

        file.write(
            "- Large numbers are NOT automatically treated as errors.\n"
        )

        file.write(
            "- FY24/FY25/FY26 headers are ignored.\n"
        )

        file.write(
            "- Suspicious numbers are NOT automatically corrected.\n"
        )

        file.write(
            "- Corrections should be made only when supported by "
            "the original scanned table.\n\n"
        )

        file.write(
            "============================================================\n\n"
        )

        for report_line in report_lines:

            file.write(
                report_line + "\n"
            )

    print(
        "\nOCR validation v2 completed!"
    )

    print(
        "\nInput file:"
    )

    print(input_file)

    print(
        "\nValidated file:"
    )

    print(output_file)

    print(
        "\nValidation report:"
    )

    print(report_file)

    print(
        "\nSummary:"
    )

    print(
        f"Table-like rows inspected : {table_rows}"
    )

    print(
        f"Rows requiring review     : {rows_with_issues}"
    )

    print(
        f"Rows without detected issues : "
        f"{table_rows - rows_with_issues}"
    )

    print(
        f"Possible OCR issues       : {total_issues}"
    )

    print(
        f"Validation Quality        : "
        f"{validation_quality:.2f}%"
    )

    return output_file, report_file


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # Find cleaned OCR files
    txt_files = [

        file

        for file in os.listdir(
            OUTPUT_FOLDER
        )

        if file.lower().endswith(".txt")

        and file.startswith("cleaned_")

        and not file.startswith("validated_")

    ]

    if not txt_files:

        print(
            "No cleaned OCR TXT file found."
        )

        return

    for txt_file in txt_files:

        input_file = os.path.join(
            OUTPUT_FOLDER,
            txt_file
        )

        process_text_file(
            input_file
        )


if __name__ == "__main__":

    main()