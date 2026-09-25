import os
import json
import re
from datetime import datetime


# =========================================================
# COALMIND AUTOMATED REPORT GENERATOR
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


# =========================================================
# GET CURRENT STRUCTURED JSON
# =========================================================

def get_current_json():
    """
    Get the JSON file of the currently processed document.
    """

    if not os.path.exists(CURRENT_FILE):

        print("No current document found.")

        return None

    try:

        with open(
            CURRENT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            json_file = file.read().strip()

    except Exception as error:

        print(
            "Error reading current document:",
            error
        )

        return None

    if not json_file:

        print(
            "No current document is selected."
        )

        return None

    if not os.path.exists(json_file):

        print(
            "Current JSON file not found:"
        )

        print(
            json_file
        )

        return None

    return json_file


# =========================================================
# LOAD STRUCTURED DOCUMENT
# =========================================================

def load_document():
    """
    Load the current structured JSON document.
    """

    json_file = get_current_json()

    if not json_file:

        return None, None

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data, json_file

    except Exception as error:

        print(
            "Error loading JSON:",
            error
        )

        return None, None


# =========================================================
# FIND MATCHING OCR VALIDATION REPORT
# =========================================================

def get_validation_report(json_file):
    """
    Find the OCR validation report corresponding
    to the current processed document.

    Example:

    JSON:
    structured_cleaned_chap9AnnualReport2026en.json

    Validation:
    ocr_validation_report_cleaned_chap9AnnualReport2026en.txt
    """

    document_name = os.path.splitext(
        os.path.basename(json_file)
    )[0]

    # -----------------------------------------------------
    # Remove "structured_" prefix
    # -----------------------------------------------------

    base_name = document_name

    if base_name.startswith("structured_"):

        base_name = base_name[
            len("structured_"):
        ]

    # -----------------------------------------------------
    # Expected validation filename
    # -----------------------------------------------------

    expected_report = os.path.join(
        OUTPUT_FOLDER,
        f"ocr_validation_report_{base_name}.txt"
    )

    # Exact match
    if os.path.exists(expected_report):

        return expected_report

    # -----------------------------------------------------
    # Get all validation reports
    # -----------------------------------------------------

    try:

        validation_files = [
            file
            for file in os.listdir(
                OUTPUT_FOLDER
            )
            if file.lower().startswith(
                "ocr_validation_report_"
            )
            and file.lower().endswith(
                ".txt"
            )
        ]

    except Exception as error:

        print(
            "Error searching validation reports:",
            error
        )

        return None

    if not validation_files:

        return None

    # -----------------------------------------------------
    # Normalize filenames
    # -----------------------------------------------------

    def normalize_name(name):

        name = name.lower()

        name = name.replace(
            "ocr_validation_report_",
            ""
        )

        name = name.replace(
            "structured_",
            ""
        )

        name = name.replace(
            "validated_",
            ""
        )

        name = name.replace(
            "cleaned_",
            ""
        )

        name = os.path.splitext(
            name
        )[0]

        name = re.sub(
            r"[^a-z0-9]+",
            "",
            name
        )

        return name

    current_name = normalize_name(
        document_name
    )

    # -----------------------------------------------------
    # Find matching reports
    # -----------------------------------------------------

    matches = []

    for file in validation_files:

        validation_name = normalize_name(
            file
        )

        if (
            current_name == validation_name
            or current_name in validation_name
            or validation_name in current_name
        ):

            matches.append(
                file
            )

    # -----------------------------------------------------
    # One matching report
    # -----------------------------------------------------

    if len(matches) == 1:

        return os.path.join(
            OUTPUT_FOLDER,
            matches[0]
        )

    # -----------------------------------------------------
    # Multiple matching reports
    # -----------------------------------------------------

    if matches:

        matches.sort(
            key=lambda file:
            os.path.getmtime(
                os.path.join(
                    OUTPUT_FOLDER,
                    file
                )
            ),
            reverse=True
        )

        return os.path.join(
            OUTPUT_FOLDER,
            matches[0]
        )

    # -----------------------------------------------------
    # Do NOT use unrelated report
    # -----------------------------------------------------

    return None


# =========================================================
# READ OCR VALIDATION METRICS
# =========================================================

def load_validation_metrics(json_file):
    """
    Read OCR validation metrics from the matching
    validation report.
    """

    report_file = get_validation_report(
        json_file
    )

    metrics = {

        "report_file": None,

        "table_rows": None,

        "rows_with_issues": None,

        "rows_without_issues": None,

        "total_issues": None,

        "validation_quality": None
    }

    if not report_file:

        return metrics

    metrics["report_file"] = report_file

    try:

        with open(
            report_file,
            "r",
            encoding="utf-8"
        ) as file:

            text = file.read()

    except Exception as error:

        print(
            "Could not read validation report:",
            error
        )

        return metrics

    # -----------------------------------------------------
    # Table-like rows inspected
    # -----------------------------------------------------

    match = re.search(
        r"Table-like rows inspected\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        metrics["table_rows"] = int(
            match.group(1)
        )

    # -----------------------------------------------------
    # Rows requiring review
    # -----------------------------------------------------

    match = re.search(
        r"Rows requiring review\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        metrics["rows_with_issues"] = int(
            match.group(1)
        )

    # -----------------------------------------------------
    # Rows without detected issues
    # -----------------------------------------------------

    match = re.search(
        r"Rows without detected issues\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        metrics["rows_without_issues"] = int(
            match.group(1)
        )

    # -----------------------------------------------------
    # Possible OCR issues
    # -----------------------------------------------------

    match = re.search(
        r"Possible OCR issues\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        metrics["total_issues"] = int(
            match.group(1)
        )

    # -----------------------------------------------------
    # Validation Quality
    # -----------------------------------------------------

    match = re.search(
        r"Validation Quality\s*:\s*([\d.]+)%",
        text,
        re.IGNORECASE
    )

    if match:

        metrics["validation_quality"] = float(
            match.group(1)
        )

    return metrics


# =========================================================
# COLLECT DOCUMENT INFORMATION
# =========================================================

def collect_report_information(data):
    """
    Collect important information from the
    structured JSON document.
    """

    pages = data.get(
        "pages",
        []
    )

    total_pages = len(
        pages
    )

    total_tables = 0

    total_rows = 0

    table_titles = []

    page_text_count = 0

    # -----------------------------------------------------
    # Process pages
    # -----------------------------------------------------

    for page in pages:

        page_text = str(
            page.get(
                "text",
                ""
            )
        ).strip()

        if page_text:

            page_text_count += 1

        tables = page.get(
            "tables",
            []
        )

        if not isinstance(
            tables,
            list
        ):

            continue

        total_tables += len(
            tables
        )

        # -------------------------------------------------
        # Process tables
        # -------------------------------------------------

        for table in tables:

            if not isinstance(
                table,
                dict
            ):

                continue

            title = str(
                table.get(
                    "title",
                    ""
                )
            ).strip()

            rows = table.get(
                "rows",
                []
            )

            if isinstance(
                rows,
                list
            ):

                total_rows += len(
                    rows
                )

            if (
                title
                and title not in table_titles
            ):

                table_titles.append(
                    title
                )

    return {

        "total_pages": total_pages,

        "pages_with_text": page_text_count,

        "total_tables": total_tables,

        "total_rows": total_rows,

        "table_titles": table_titles
    }


# =========================================================
# EXTRACT DOCUMENT TEXT FOR SUMMARY
# =========================================================

def collect_document_text(data):
    """
    Collect text from the structured document
    for a simple document summary.
    """

    pages = data.get(
        "pages",
        []
    )

    text_parts = []

    for page in pages:

        if not isinstance(
            page,
            dict
        ):

            continue

        text = str(
            page.get(
                "text",
                ""
            )
        ).strip()

        if text:

            text_parts.append(
                text
            )

    return "\n".join(
        text_parts
    )


# =========================================================
# CREATE DOCUMENT SUMMARY
# =========================================================

def create_document_summary(data):
    """
    Create a concise summary based only on the
    text available in the structured document.

    This does not use an external LLM and does not
    invent document content.
    """

    document_text = collect_document_text(
        data
    )

    if not document_text:

        return (
            "No page text was available for "
            "document summarization."
        )

    # -----------------------------------------------------
    # Clean whitespace
    # -----------------------------------------------------

    document_text = re.sub(
        r"\s+",
        " ",
        document_text
    ).strip()

    # -----------------------------------------------------
    # Split into sentences
    # -----------------------------------------------------

    sentences = re.split(
        r"(?<=[.!?])\s+",
        document_text
    )

    useful_sentences = []

    # -----------------------------------------------------
    # Select representative sentences
    #
    # This is extractive only. It does not create
    # unsupported information.
    # -----------------------------------------------------

    for sentence in sentences:

        sentence = sentence.strip()

        if len(sentence) < 40:

            continue

        # Ignore obvious page markers
        if re.match(
            r"^PAGE\s+\d+",
            sentence,
            re.IGNORECASE
        ):

            continue

        if sentence not in useful_sentences:

            useful_sentences.append(
                sentence
            )

        if len(useful_sentences) >= 5:

            break

    if not useful_sentences:

        # Fallback to first portion of document
        return (
            document_text[:1000]
            +
            (
                "..."
                if len(document_text) > 1000
                else ""
            )
        )

    return " ".join(
        useful_sentences
    )


# =========================================================
# GENERATE AUTOMATED REPORT
# =========================================================

def generate_report(
    data,
    json_file
):
    """
    Generate the CoalMind automated report.

    Report contains:
        1. Document details
        2. Document summary
        3. Performance metrics
        4. OCR validation metrics
        5. Identified tables / sections

    It does not include:
        - AI system status
        - RAG system status
        - Pipeline status
        - Impact claims
    """

    information = collect_report_information(
        data
    )

    validation = load_validation_metrics(
        json_file
    )

    document_name = os.path.splitext(
        os.path.basename(json_file)
    )[0]

    report_time = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    document_summary = create_document_summary(
        data
    )

    report = []

    # =====================================================
    # HEADER
    # =====================================================

    report.append(
        "=" * 70
    )

    report.append(
        "COALMIND - AUTOMATED REPORT"
    )

    report.append(
        "=" * 70
    )

    # =====================================================
    # DOCUMENT DETAILS
    # =====================================================

    report.append("")

    report.append(
        "-" * 70
    )

    report.append(
        "DOCUMENT DETAILS"
    )

    report.append(
        "-" * 70
    )

    report.append(
        f"Document: {document_name}"
    )

    report.append(
        f"Generated on: {report_time}"
    )

    report.append(
        f"Pages: {information['total_pages']}"
    )

    # =====================================================
    # DOCUMENT SUMMARY
    # =====================================================

    report.append("")

    report.append(
        "-" * 70
    )

    report.append(
        "DOCUMENT SUMMARY"
    )

    report.append(
        "-" * 70
    )

    report.append(
        document_summary
    )

    # =====================================================
    # DOCUMENT CONTENT METRICS
    # =====================================================

    report.append("")

    report.append(
        "-" * 70
    )

    report.append(
        "DOCUMENT PERFORMANCE METRICS"
    )

    report.append(
        "-" * 70
    )

    report.append(
        f"Total pages processed       : "
        f"{information['total_pages']}"
    )

    report.append(
        f"Pages containing text       : "
        f"{information['pages_with_text']}"
    )

    report.append(
        f"Tables detected             : "
        f"{information['total_tables']}"
    )

    report.append(
        f"Rows extracted              : "
        f"{information['total_rows']}"
    )

    # =====================================================
    # OCR VALIDATION METRICS
    # =====================================================

    if validation["report_file"]:

        report.append("")

        report.append(
            "-" * 70
        )

        report.append(
            "OCR PERFORMANCE METRICS"
        )

        report.append(
            "-" * 70
        )

        report.append(
            "Validation report used      : "
            + os.path.basename(
                validation["report_file"]
            )
        )

        if validation["table_rows"] is not None:

            report.append(
                f"Table-like rows inspected   : "
                f"{validation['table_rows']}"
            )

        if validation["rows_with_issues"] is not None:

            report.append(
                f"Rows requiring review       : "
                f"{validation['rows_with_issues']}"
            )

        if validation["rows_without_issues"] is not None:

            report.append(
                f"Rows without detected issues: "
                f"{validation['rows_without_issues']}"
            )

        if validation["total_issues"] is not None:

            report.append(
                f"Possible OCR issues         : "
                f"{validation['total_issues']}"
            )

        if validation["validation_quality"] is not None:

            report.append(
                f"Validation Quality          : "
                f"{validation['validation_quality']:.2f}%"
            )

    else:

        report.append("")

        report.append(
            "-" * 70
        )

        report.append(
            "OCR PERFORMANCE METRICS"
        )

        report.append(
            "-" * 70
        )

        report.append(
            "Matching OCR validation report "
            "was not found."
        )

        report.append(
            "OCR validation metrics are not "
            "available for this document."
        )

    # =====================================================
    # IDENTIFIED TABLES / SECTIONS
    # =====================================================

    report.append("")

    report.append(
        "-" * 70
    )

    report.append(
        "IDENTIFIED TABLES / SECTIONS"
    )

    report.append(
        "-" * 70
    )

    if information["table_titles"]:

        for number, title in enumerate(
            information["table_titles"],
            start=1
        ):

            report.append(
                f"{number}. {title}"
            )

    else:

        report.append(
            "No tables or sections were identified."
        )

    # =====================================================
    # KEY EXTRACTED INFORMATION
    # =====================================================

    report.append("")

    report.append(
        "-" * 70
    )

    report.append(
        "KEY EXTRACTED INFORMATION"
    )

    report.append(
        "-" * 70
    )

    # -----------------------------------------------------
    # Show selected document-level figures / terms
    # -----------------------------------------------------

    document_text = collect_document_text(
        data
    )

    if document_text:

        # Find sentences containing useful
        # report-related numerical information.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            re.sub(
                r"\s+",
                " ",
                document_text
            )
        )

        key_sentences = []

        keywords = [
            "production",
            "coal",
            "lignite",
            "revenue",
            "output",
            "target",
            "growth",
            "achievement",
            "capacity",
            "million",
            "mt",
            "crore",
            "percentage"
        ]

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) < 30:

                continue

            sentence_lower = (
                sentence.lower()
            )

            if any(
                keyword in sentence_lower
                for keyword in keywords
            ):

                if sentence not in key_sentences:

                    key_sentences.append(
                        sentence
                    )

            if len(key_sentences) >= 10:

                break

        if key_sentences:

            for number, sentence in enumerate(
                key_sentences,
                start=1
            ):

                report.append(
                    f"{number}. {sentence}"
                )

        else:

            report.append(
                "No specific key information "
                "was automatically identified."
            )

    else:

        report.append(
            "No extracted text is available."
        )

    # =====================================================
    # FOOTER
    # =====================================================

    report.append("")

    report.append(
        "=" * 70
    )

    report.append(
        "END OF COALMIND REPORT"
    )

    report.append(
        "=" * 70
    )

    return "\n".join(
        report
    )


# =========================================================
# SAVE REPORT
# =========================================================

def save_report(
    report,
    json_file
):
    """
    Save the generated automated report.
    """

    document_name = os.path.splitext(
        os.path.basename(json_file)
    )[0]

    report_filename = (
        document_name
        + "_automated_report.txt"
    )

    report_path = os.path.join(
        OUTPUT_FOLDER,
        report_filename
    )

    try:

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                report
            )

    except Exception as error:

        print(
            "Error saving report:",
            error
        )

        return None

    return report_path


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 70
    )

    print(
        "COALMIND AUTOMATED REPORT GENERATION"
    )

    print(
        "=" * 70
    )

    # -----------------------------------------------------
    # Load document
    # -----------------------------------------------------

    data, json_file = load_document()

    if data is None:

        print(
            "\nUnable to load processed document."
        )

        return

    print()

    print(
        "Generating report for:"
    )

    print(
        os.path.basename(
            json_file
        )
    )

    # -----------------------------------------------------
    # Check matching OCR validation report
    # -----------------------------------------------------

    validation_report = get_validation_report(
        json_file
    )

    if validation_report:

        print()

        print(
            "Matching OCR validation report:"
        )

        print(
            os.path.basename(
                validation_report
            )
        )

    else:

        print()

        print(
            "No matching OCR validation report found."
        )

        print(
            "The report will not use metrics "
            "from another document."
        )

    # -----------------------------------------------------
    # Generate report
    # -----------------------------------------------------

    report = generate_report(
        data,
        json_file
    )

    # -----------------------------------------------------
    # Save report
    # -----------------------------------------------------

    report_path = save_report(
        report,
        json_file
    )

    if not report_path:

        return

    # -----------------------------------------------------
    # Display report
    # -----------------------------------------------------

    print()

    print(
        "-" * 70
    )

    print(
        "GENERATED REPORT"
    )

    print(
        "-" * 70
    )

    print()

    print(
        report
    )

    # -----------------------------------------------------
    # Final status
    # -----------------------------------------------------

    print()

    print(
        "Report generated successfully!"
    )

    print()

    print(
        "Saved to:"
    )

    print(
        report_path
    )


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()