# =========================================================
# COALMIND - app.py
# =========================================================

from flask import Flask, render_template, request, send_file

import json
import os
import subprocess
import sys
import re
import time


# =========================================================
# IMPORTS
# =========================================================

from src.search import search_document

# RAG / LLM query response
from src.query_response import generate_response


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# FOLDERS
# =========================================================

BASE_FOLDER = r"C:\coalmind"

INPUT_FOLDER = os.path.join(
    BASE_FOLDER,
    "input"
)

OUTPUT_FOLDER = os.path.join(
    BASE_FOLDER,
    "output"
)

SRC_FOLDER = os.path.join(
    BASE_FOLDER,
    "src"
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
# CREATE FOLDERS
# =========================================================

os.makedirs(
    INPUT_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# =========================================================
# REPORT LANGUAGE
# =========================================================

DEFAULT_REPORT_LANGUAGE = "english"

SUPPORTED_REPORT_LANGUAGES = [
    "english",
    "hindi"
]


# =========================================================
# REPORT LANGUAGE FILE
# =========================================================

REPORT_LANGUAGE_FILE = os.path.join(
    OUTPUT_FOLDER,
    "report_language.txt"
)


# =========================================================
# SAVE REPORT LANGUAGE
# =========================================================

def save_report_language(language):

    language = str(
        language
    ).strip().lower()

    if language not in SUPPORTED_REPORT_LANGUAGES:

        language = DEFAULT_REPORT_LANGUAGE

    try:

        with open(
            REPORT_LANGUAGE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                language
            )

        print(
            "Report language saved:",
            language
        )

    except Exception as error:

        print(
            "Could not save report language:",
            error
        )


# =========================================================
# GET REPORT LANGUAGE
# =========================================================

def get_report_language():

    if not os.path.exists(
        REPORT_LANGUAGE_FILE
    ):

        return DEFAULT_REPORT_LANGUAGE

    try:

        with open(
            REPORT_LANGUAGE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            language = (
                file.read()
                .strip()
                .lower()
            )

        if language in SUPPORTED_REPORT_LANGUAGES:

            return language

    except Exception as error:

        print(
            "Could not read report language:",
            error
        )

    return DEFAULT_REPORT_LANGUAGE


# =========================================================
# SAVE CURRENT JSON PATH
# =========================================================

def save_current_json(json_file):

    try:

        with open(
            CURRENT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                json_file
            )

    except Exception as error:

        print(
            "Could not save current JSON:",
            error
        )


# =========================================================
# GET CURRENT JSON PATH
# =========================================================

def get_current_json():

    if not os.path.exists(
        CURRENT_FILE
    ):

        return None

    try:

        with open(
            CURRENT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            json_file = (
                file.read()
                .strip()
            )

    except Exception as error:

        print(
            "Could not read current document:",
            error
        )

        return None

    if not json_file:

        return None

    if not os.path.exists(
        json_file
    ):

        print(
            "Current JSON file does not exist:",
            json_file
        )

        return None

    return json_file


# =========================================================
# LOAD CURRENT DOCUMENT
# =========================================================

def load_current_data():

    json_file = get_current_json()

    if not json_file:

        print(
            "No current processed document found."
        )

        return None

    try:

        with open(
            json_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        print(
            "Current document:",
            os.path.basename(
                json_file
            )
        )

        return data

    except Exception as error:

        print(
            "JSON loading error:",
            error
        )

        return None


# =========================================================
# GET DOCUMENT INFORMATION
# =========================================================

def get_document_info(data):

    if not data:

        return {}

    document = data.get(
        "document",
        {}
    )

    pages = data.get(
        "pages",
        []
    )

    total_pages = len(
        pages
    )

    pages_with_text = 0

    total_tables = 0

    total_rows = 0

    for page in pages:

        page_text = str(
            page.get(
                "text",
                ""
            )
        ).strip()

        if page_text:

            pages_with_text += 1

        tables = page.get(
            "tables",
            []
        )

        total_tables += len(
            tables
        )

        for table in tables:

            rows = table.get(
                "rows",
                []
            )

            total_rows += len(
                rows
            )

    current_json = get_current_json()

    default_name = (

        os.path.basename(
            current_json
        )

        if current_json

        else "Current Report"

    )

    return {

        "name":
            document.get(
                "name",
                document.get(
                    "filename",
                    default_name
                )
            ),

        "pages":
            total_pages,

        "pages_with_text":
            pages_with_text,

        "tables":
            total_tables,

        "rows":
            total_rows

    }


# =========================================================
# GET OCR VALIDATION METRICS
# =========================================================

def get_validation_metrics():

    metrics = {

        "table_rows": 0,

        "rows_with_issues": 0,

        "rows_without_issues": 0,

        "total_issues": 0,

        "validation_quality": 0.0

    }

    current_json = get_current_json()

    if not current_json:

        return metrics

    document_name = os.path.splitext(
        os.path.basename(
            current_json
        )
    )[0]

    validation_file = os.path.join(
        OUTPUT_FOLDER,
        f"ocr_validation_report_{document_name}.txt"
    )

    if not os.path.exists(
        validation_file
    ):

        validation_files = [

            file

            for file in os.listdir(
                OUTPUT_FOLDER
            )

            if file.startswith(
                "ocr_validation_report_"
            )

            and file.lower().endswith(
                ".txt"
            )

        ]

        if validation_files:

            validation_files.sort(

                key=lambda file:
                os.path.getmtime(
                    os.path.join(
                        OUTPUT_FOLDER,
                        file
                    )
                ),

                reverse=True

            )

            validation_file = os.path.join(
                OUTPUT_FOLDER,
                validation_files[0]
            )

        else:

            return metrics

    try:

        with open(
            validation_file,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            text = file.read()

        match = re.search(
            r"Table-like rows inspected\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:

            metrics["table_rows"] = int(
                match.group(1)
            )

        match = re.search(
            r"Rows requiring review\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:

            metrics["rows_with_issues"] = int(
                match.group(1)
            )

        match = re.search(
            r"Rows without detected issues\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:

            metrics["rows_without_issues"] = int(
                match.group(1)
            )

        elif metrics["table_rows"] > 0:

            metrics["rows_without_issues"] = (

                metrics["table_rows"]
                -
                metrics["rows_with_issues"]

            )

        match = re.search(
            r"Possible OCR issues\s*:\s*(\d+)",
            text,
            re.IGNORECASE
        )

        if match:

            metrics["total_issues"] = int(
                match.group(1)
            )

        match = re.search(
            r"Validation Quality\s*:\s*([\d.]+)%",
            text,
            re.IGNORECASE
        )

        if match:

            metrics["validation_quality"] = float(
                match.group(1)
            )

        elif metrics["table_rows"] > 0:

            metrics["validation_quality"] = (

                metrics["rows_without_issues"]
                /
                metrics["table_rows"]

            ) * 100

    except Exception as error:

        print(
            "Validation metrics error:",
            error
        )

    return metrics


# =========================================================
# RUN PYTHON MODULE
# =========================================================

def run_module(
    module_name,
    environment=None
):

    module_path = os.path.join(
        SRC_FOLDER,
        module_name
    )

    if not os.path.exists(
        module_path
    ):

        print(
            "Module not found:",
            module_path
        )

        return ""

    try:

        process_environment = os.environ.copy()

        if environment:

            process_environment.update(
                environment
            )

        print()
        print(
            "Running module:",
            module_name
        )

        result = subprocess.run(

            [
                sys.executable,
                module_path
            ],

            cwd=BASE_FOLDER,

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="ignore",

            env=process_environment

        )

        if result.stdout:

            print(
                result.stdout
            )

        if result.stderr:

            print(
                result.stderr
            )

        return result.stdout

    except Exception as error:

        print(
            "Module execution error:",
            error
        )

        return ""


# =========================================================
# GENERATE WORD CLOUD
# =========================================================

def generate_wordcloud():

    print("\n")
    print("=" * 60)
    print("GENERATING WORD CLOUD")
    print("=" * 60)

    run_module(
        "word_cloud.py"
    )

    if os.path.exists(
        WORDCLOUD_FILE
    ):

        print(
            "Word Cloud generated successfully."
        )

        return True

    print(
        "Word Cloud was not generated."
    )

    return False


# =========================================================
# GENERATE IMPORTANT TOPICS
# =========================================================

def generate_topics():

    print("\n")
    print("=" * 60)
    print("IDENTIFYING IMPORTANT TOPICS")
    print("=" * 60)

    output = run_module(
        "topic_identifier.py"
    )

    topics = []

    if not output:

        return topics

    lines = output.splitlines()

    for line in lines:

        line = line.strip()

        if not line:

            continue

        if "." not in line:

            continue

        parts = line.split(
            ".",
            1
        )

        number = parts[0].strip()

        topic = parts[1].strip()

        if (
            number.isdigit()
            and
            topic
        ):

            if topic not in topics:

                topics.append(
                    topic
                )

    print(
        "Important topics identified:",
        topics
    )

    print(
        "Total important topics:",
        len(topics)
    )

    return topics


# =========================================================
# GET AUTOMATED REPORT FILE
# =========================================================

def get_report_file(
    language=None
):

    json_file = get_current_json()

    if not json_file:

        return None

    if language is None:

        language = get_report_language()

    language = str(
        language
    ).strip().lower()

    if language not in SUPPORTED_REPORT_LANGUAGES:

        language = DEFAULT_REPORT_LANGUAGE

    document_name = os.path.splitext(
        os.path.basename(
            json_file
        )
    )[0]

    # -----------------------------------------------------
    # English
    # -----------------------------------------------------

    if language == "english":

        report_filename = (

            document_name
            +
            "_automated_report_english.txt"

        )

    # -----------------------------------------------------
    # Hindi
    # -----------------------------------------------------

    elif language == "hindi":

        report_filename = (

            document_name
            +
            "_automated_report_hindi.txt"

        )

    else:

        report_filename = (

            document_name
            +
            "_automated_report_english.txt"

        )

    return os.path.join(
        OUTPUT_FOLDER,
        report_filename
    )


# =========================================================
# DELETE OLD REPORT FOR SELECTED LANGUAGE
# =========================================================

def remove_existing_language_report(
    language
):

    report_file = get_report_file(
        language
    )

    if not report_file:

        return

    if os.path.exists(
        report_file
    ):

        try:

            os.remove(
                report_file
            )

            print(
                "Removed previous report:",
                report_file
            )

        except Exception as error:

            print(
                "Could not remove old report:",
                error
            )


# =========================================================
# GENERATE AUTOMATED REPORT
# =========================================================

def generate_automated_report(
    language="english"
):

    language = str(
        language
    ).strip().lower()

    if language not in SUPPORTED_REPORT_LANGUAGES:

        language = DEFAULT_REPORT_LANGUAGE

    print("\n")
    print("=" * 60)
    print("GENERATING AUTOMATED REPORT")
    print("=" * 60)

    print(
        "Selected language:",
        language
    )

    # -----------------------------------------------------
    # Check current document
    # -----------------------------------------------------

    current_json = get_current_json()

    if not current_json:

        print(
            "No current document available."
        )

        return None

    # -----------------------------------------------------
    # Save selected language
    # -----------------------------------------------------

    save_report_language(
        language
    )

    # -----------------------------------------------------
    # Remove old report for this language
    #
    # This prevents stale reports from being displayed.
    # -----------------------------------------------------

    remove_existing_language_report(
        language
    )

    # -----------------------------------------------------
    # Pass language to automated_report.py
    # -----------------------------------------------------

    print()
    print(
        "Starting automated_report.py..."
    )

    print(
        "COALMIND_REPORT_LANGUAGE =",
        language
    )

    output = run_module(

        "automated_report.py",

        environment={

            "COALMIND_REPORT_LANGUAGE":
                language

        }

    )

    # -----------------------------------------------------
    # Expected report
    # -----------------------------------------------------

    report_file = get_report_file(
        language
    )

    # -----------------------------------------------------
    # Check expected report
    # -----------------------------------------------------

    if (
        report_file
        and
        os.path.exists(
            report_file
        )
    ):

        print()
        print(
            "Automated report generated successfully:"
        )

        print(
            report_file
        )

        return report_file

    # -----------------------------------------------------
    # Compatibility fallback
    #
    # Some versions of automated_report.py may create:
    #
    # document_automated_report.txt
    #
    # If that happens, copy it to the correct
    # language-specific filename.
    # -----------------------------------------------------

    document_name = os.path.splitext(
        os.path.basename(
            current_json
        )
    )[0]

    old_report_file = os.path.join(

        OUTPUT_FOLDER,

        document_name
        +
        "_automated_report.txt"

    )

    if os.path.exists(
        old_report_file
    ):

        try:

            with open(
                old_report_file,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as source_file:

                report_text = source_file.read()

            if report_text.strip():

                with open(
                    report_file,
                    "w",
                    encoding="utf-8"
                ) as target_file:

                    target_file.write(
                        report_text
                    )

                print()
                print(
                    "Compatibility report created:"
                )

                print(
                    report_file
                )

                return report_file

        except Exception as error:

            print(
                "Compatibility report error:",
                error
            )

    # -----------------------------------------------------
    # Nothing was generated
    # -----------------------------------------------------

    print()
    print(
        "Automated report was not generated."
    )

    if output:

        print(
            "automated_report.py output was:"
        )

        print(
            output
        )

    return None


# =========================================================
# READ AUTOMATED REPORT
# =========================================================

def read_automated_report(
    language=None
):

    if language is None:

        language = get_report_language()

    report_file = get_report_file(
        language
    )

    if not report_file:

        return ""

    if not os.path.exists(
        report_file
    ):

        return ""

    try:

        with open(
            report_file,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            return file.read()

    except Exception as error:

        print(
            "Report reading error:",
            error
        )

        return ""


# =========================================================
# AI RESPONSE
# =========================================================

def create_ai_response(
    question,
    data
):

    if not question:

        return (
            "Ask a question about the current report."
        )

    if not data:

        return (
            "Please upload and process a report first."
        )

    try:

        print("\n")
        print("=" * 60)
        print("COALMIND AI QUERY")
        print("=" * 60)

        print(
            "Question:",
            question
        )

        response = generate_response(
            data,
            question
        )

        print(
            "\nAI RESPONSE:"
        )

        print(
            response
        )

        return response

    except Exception as error:

        print("\n")
        print("=" * 60)
        print("AI RESPONSE ERROR")
        print("=" * 60)

        print(
            error
        )

        return (
            "Unable to generate an AI response "
            "from the current report."
        )


# =========================================================
# DASHBOARD DATA
# =========================================================

def dashboard_data():

    data = load_current_data()

    info = get_document_info(
        data
    )

    topics = []

    if data:

        topics = generate_topics()

    report_language = get_report_language()

    report = read_automated_report(
        report_language
    )

    current_json = get_current_json()

    current_document = (

        os.path.basename(
            current_json
        )

        if current_json

        else None

    )

    validation = get_validation_metrics()

    return {

        "data":
            data,

        "document":
            info,

        "current_document":
            current_document,

        "pages":
            info.get(
                "pages",
                0
            ),

        "tables":
            info.get(
                "tables",
                0
            ),

        "rows":
            info.get(
                "rows",
                0
            ),

        "topics":
            topics,

        "automated_report":
            report,

        "report_language":
            report_language,

        "wordcloud_exists":
            os.path.exists(
                WORDCLOUD_FILE
            ),

        "table_rows":
            validation.get(
                "table_rows",
                0
            ),

        "rows_with_issues":
            validation.get(
                "rows_with_issues",
                0
            ),

        "rows_without_issues":
            validation.get(
                "rows_without_issues",
                0
            ),

        "total_issues":
            validation.get(
                "total_issues",
                0
            ),

        "validation_quality":
            validation.get(
                "validation_quality",
                0.0
            ),

        "processing_time":
            0.0

    }


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def dashboard():

    values = dashboard_data()

    return render_template(

        "dashboard.html",

        document=values["document"],

        current_document=
            values["current_document"],

        pages=values["pages"],

        tables=values["tables"],

        rows=values["rows"],

        topics=values["topics"],

        automated_report=
            values["automated_report"],

        report_language=
            values["report_language"],

        wordcloud_exists=
            values["wordcloud_exists"],

        table_rows=
            values["table_rows"],

        rows_with_issues=
            values["rows_with_issues"],

        rows_without_issues=
            values["rows_without_issues"],

        total_issues=
            values["total_issues"],

        validation_quality=
            values["validation_quality"],

        processing_time=
            values["processing_time"],

        results=[],

        query="",

        ai_response="",

        upload_message=None,

        error_message=None

    )


# =========================================================
# SEARCH
# =========================================================

@app.route(
    "/search",
    methods=["GET", "POST"]
)
def search():

    query = request.values.get(
        "query",
        ""
    ).strip()

    values = dashboard_data()

    data = values["data"]

    results = []

    if data and query:

        results = search_document(
            data,
            query
        )

    return render_template(

        "dashboard.html",

        document=values["document"],

        current_document=
            values["current_document"],

        pages=values["pages"],

        tables=values["tables"],

        rows=values["rows"],

        topics=values["topics"],

        automated_report=
            values["automated_report"],

        report_language=
            values["report_language"],

        wordcloud_exists=
            values["wordcloud_exists"],

        table_rows=
            values["table_rows"],

        rows_with_issues=
            values["rows_with_issues"],

        rows_without_issues=
            values["rows_without_issues"],

        total_issues=
            values["total_issues"],

        validation_quality=
            values["validation_quality"],

        processing_time=
            values["processing_time"],

        results=results,

        query=query,

        ai_response="",

        upload_message=None,

        error_message=None

    )


# =========================================================
# ASK AI
# =========================================================

@app.route(
    "/ask-ai",
    methods=["POST"]
)
def ask_ai():

    question = request.form.get(
        "question",
        ""
    ).strip()

    values = dashboard_data()

    response = create_ai_response(
        question,
        values["data"]
    )

    return render_template(

        "dashboard.html",

        document=values["document"],

        current_document=
            values["current_document"],

        pages=values["pages"],

        tables=values["tables"],

        rows=values["rows"],

        topics=values["topics"],

        automated_report=
            values["automated_report"],

        report_language=
            values["report_language"],

        wordcloud_exists=
            values["wordcloud_exists"],

        table_rows=
            values["table_rows"],

        rows_with_issues=
            values["rows_with_issues"],

        rows_without_issues=
            values["rows_without_issues"],

        total_issues=
            values["total_issues"],

        validation_quality=
            values["validation_quality"],

        processing_time=
            values["processing_time"],

        results=[],

        query="",

        ai_response=response,

        upload_message=None,

        error_message=None

    )


# =========================================================
# WORD CLOUD
# =========================================================

@app.route(
    "/wordcloud"
)
def wordcloud():

    if not os.path.exists(
        WORDCLOUD_FILE
    ):

        return (
            "Word Cloud has not been generated yet.",
            404
        )

    return send_file(
        WORDCLOUD_FILE
    )


# =========================================================
# UPLOAD PDF
# =========================================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload_pdf():

    processing_start_time = time.time()

    try:

        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        if "pdf_file" not in request.files:

            raise Exception(
                "No PDF file was selected."
            )

        file = request.files[
            "pdf_file"
        ]

        if file.filename == "":

            raise Exception(
                "Please select a PDF file."
            )

        if not file.filename.lower().endswith(
            ".pdf"
        ):

            raise Exception(
                "Only PDF files are allowed."
            )

        # -------------------------------------------------
        # SAVE PDF
        # -------------------------------------------------

        filename = os.path.basename(
            file.filename
        )

        pdf_path = os.path.join(
            INPUT_FOLDER,
            filename
        )

        file.save(
            pdf_path
        )

        print("\n")
        print("=" * 60)
        print("PDF UPLOADED")
        print("=" * 60)

        print(
            pdf_path
        )

        # -------------------------------------------------
        # PROCESS PDF
        # -------------------------------------------------

        structured_file = process_pdf_pipeline(
            pdf_path
        )

        if not structured_file:

            raise Exception(
                "Processing did not create a structured JSON file."
            )

        if not os.path.exists(
            structured_file
        ):

            raise Exception(
                "Structured JSON file was not found."
            )

        # -------------------------------------------------
        # SAVE CURRENT DOCUMENT
        # -------------------------------------------------

        save_current_json(
            structured_file
        )

        print(
            "Current document:",
            structured_file
        )

        # -------------------------------------------------
        # GENERATE WORD CLOUD
        # -------------------------------------------------

        generate_wordcloud()

        # -------------------------------------------------
        # GENERATE TOPICS
        # -------------------------------------------------

        topics = generate_topics()

        print(
            "Total important topics identified:",
            len(topics)
        )

        # -------------------------------------------------
        # DO NOT GENERATE REPORT HERE
        #
        # User must select English/Hindi and then
        # click Generate Report.
        # -------------------------------------------------

        # -------------------------------------------------
        # LOAD STRUCTURED JSON
        # -------------------------------------------------

        with open(
            structured_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        info = get_document_info(
            data
        )

        processing_time = round(

            time.time()
            -
            processing_start_time,

            2

        )

        validation = get_validation_metrics()

        # -------------------------------------------------
        # RENDER DASHBOARD
        # -------------------------------------------------

        return render_template(

            "dashboard.html",

            document=info,

            current_document=
                os.path.basename(
                    structured_file
                ),

            pages=info.get(
                "pages",
                0
            ),

            tables=info.get(
                "tables",
                0
            ),

            rows=info.get(
                "rows",
                0
            ),

            topics=topics,

            automated_report="",

            report_language=
                get_report_language(),

            wordcloud_exists=
                os.path.exists(
                    WORDCLOUD_FILE
                ),

            table_rows=
                validation.get(
                    "table_rows",
                    0
                ),

            rows_with_issues=
                validation.get(
                    "rows_with_issues",
                    0
                ),

            rows_without_issues=
                validation.get(
                    "rows_without_issues",
                    0
                ),

            total_issues=
                validation.get(
                    "total_issues",
                    0
                ),

            validation_quality=
                validation.get(
                    "validation_quality",
                    0.0
                ),

            processing_time=
                processing_time,

            results=[],

            query="",

            ai_response="",

            upload_message=(
                f"Successfully processed: {filename}"
            ),

            error_message=None

        )

    except Exception as error:

        print("\n")
        print("=" * 60)
        print("COALMIND ERROR")
        print("=" * 60)

        print(
            error
        )

        return render_template(

            "dashboard.html",

            document={},

            current_document=None,

            pages=0,

            tables=0,

            rows=0,

            topics=[],

            automated_report="",

            report_language=
                get_report_language(),

            wordcloud_exists=False,

            table_rows=0,

            rows_with_issues=0,

            rows_without_issues=0,

            total_issues=0,

            validation_quality=0.0,

            processing_time=0.0,

            results=[],

            query="",

            ai_response="",

            upload_message=None,

            error_message=str(
                error
            )

        )


# =========================================================
# GENERATE REPORT
# =========================================================

@app.route(
    "/generate-report",
    methods=["POST"]
)
def generate_report():

    try:

        # -------------------------------------------------
        # GET SELECTED LANGUAGE
        # -------------------------------------------------

        language = request.form.get(
            "language",
            DEFAULT_REPORT_LANGUAGE
        )

        language = str(
            language
        ).strip().lower()

        print("\n")
        print("=" * 60)
        print("REPORT LANGUAGE SELECTION")
        print("=" * 60)

        print(
            "Selected language:",
            language
        )

        # -------------------------------------------------
        # VALIDATE LANGUAGE
        # -------------------------------------------------

        if language not in SUPPORTED_REPORT_LANGUAGES:

            language = DEFAULT_REPORT_LANGUAGE

        # -------------------------------------------------
        # CHECK DOCUMENT
        # -------------------------------------------------

        current_json = get_current_json()

        if not current_json:

            raise Exception(
                "Please upload and process a PDF before generating a report."
            )

        # -------------------------------------------------
        # SAVE LANGUAGE
        # -------------------------------------------------

        save_report_language(
            language
        )

        # -------------------------------------------------
        # GENERATE REPORT
        # -------------------------------------------------

        report_file = generate_automated_report(
            language
        )

        if not report_file:

            raise Exception(
                "Automated report could not be generated."
            )

        if not os.path.exists(
            report_file
        ):

            raise Exception(
                "Generated report file was not found."
            )

        # -------------------------------------------------
        # READ EXACT SELECTED-LANGUAGE REPORT
        # -------------------------------------------------

        report = read_automated_report(
            language
        )

        if not report.strip():

            raise Exception(
                "The generated report file is empty."
            )

        # -------------------------------------------------
        # LOAD DASHBOARD DATA
        # -------------------------------------------------

        values = dashboard_data()

        print()
        print(
            "Report generation completed."
        )

        print(
            "Language:",
            language
        )

        print(
            "Report:",
            report_file
        )

        # -------------------------------------------------
        # RENDER DASHBOARD
        # -------------------------------------------------

        return render_template(

            "dashboard.html",

            document=
                values["document"],

            current_document=
                values["current_document"],

            pages=
                values["pages"],

            tables=
                values["tables"],

            rows=
                values["rows"],

            topics=
                values["topics"],

            automated_report=
                report,

            report_language=
                language,

            wordcloud_exists=
                values["wordcloud_exists"],

            table_rows=
                values["table_rows"],

            rows_with_issues=
                values["rows_with_issues"],

            rows_without_issues=
                values["rows_without_issues"],

            total_issues=
                values["total_issues"],

            validation_quality=
                values["validation_quality"],

            processing_time=
                values["processing_time"],

            results=[],

            query="",

            ai_response="",

            upload_message=(

                "Automated report generated successfully "
                f"in {language.capitalize()}."

            ),

            error_message=None

        )

    except Exception as error:

        print("\n")
        print("=" * 60)
        print("REPORT GENERATION ERROR")
        print("=" * 60)

        print(
            error
        )

        values = dashboard_data()

        return render_template(

            "dashboard.html",

            document=
                values["document"],

            current_document=
                values["current_document"],

            pages=
                values["pages"],

            tables=
                values["tables"],

            rows=
                values["rows"],

            topics=
                values["topics"],

            automated_report=
                values["automated_report"],

            report_language=
                get_report_language(),

            wordcloud_exists=
                values["wordcloud_exists"],

            table_rows=
                values["table_rows"],

            rows_with_issues=
                values["rows_with_issues"],

            rows_without_issues=
                values["rows_without_issues"],

            total_issues=
                values["total_issues"],

            validation_quality=
                values["validation_quality"],

            processing_time=
                values["processing_time"],

            results=[],

            query="",

            ai_response="",

            upload_message=None,

            error_message=(
                "Report generation failed: "
                + str(error)
            )

        )


# =========================================================
# DOWNLOAD AUTOMATED REPORT
# =========================================================

@app.route(
    "/download/report"
)
def download_report():

    # -----------------------------------------------------
    # CURRENT SELECTED LANGUAGE
    # -----------------------------------------------------

    language = get_report_language()

    print()
    print(
        "Downloading report in:",
        language
    )

    # -----------------------------------------------------
    # GET REPORT FILE
    # -----------------------------------------------------

    report_file = get_report_file(
        language
    )

    if not report_file:

        return (
            "No processed document is available.",
            404
        )

    if not os.path.exists(
        report_file
    ):

        return (

            "Automated report has not been generated yet. "
            "Please select a language and generate the report.",

            404

        )

    # -----------------------------------------------------
    # CURRENT DOCUMENT
    # -----------------------------------------------------

    current_json = get_current_json()

    if not current_json:

        return (
            "No current document is available.",
            404
        )

    document_name = os.path.splitext(
        os.path.basename(
            current_json
        )
    )[0]

    # -----------------------------------------------------
    # DOWNLOAD NAME
    # -----------------------------------------------------

    if language == "hindi":

        download_name = (

            document_name
            +
            "_automated_report_hindi.txt"

        )

    else:

        download_name = (

            document_name
            +
            "_automated_report_english.txt"

        )

    return send_file(

        report_file,

        as_attachment=True,

        download_name=download_name

    )


# =========================================================
# PDF PROCESSING PIPELINE
# =========================================================

def process_pdf_pipeline(
    pdf_path
):

    print("\n")
    print("=" * 60)
    print("COALMIND PDF PROCESSING PIPELINE")
    print("=" * 60)

    # =====================================================
    # STEP 1 - OCR
    # =====================================================

    print("\n[1/4] OCR Extraction...")

    try:

        from src.ocr import process_pdf

        ocr_file = process_pdf(
            pdf_path
        )

        if not ocr_file:

            raise Exception(
                "OCR did not create an output file."
            )

        print(
            "OCR completed:",
            ocr_file
        )

    except Exception as error:

        raise Exception(
            f"OCR failed: {error}"
        )

    # =====================================================
    # STEP 2 - TEXT CLEANING
    # =====================================================

    print("\n[2/4] Text Cleaning...")

    try:

        from src.clean_text import process_text_file

        cleaned_file, cleaning_report = (
            process_text_file(
                ocr_file
            )
        )

        if not cleaned_file:

            raise Exception(
                "Cleaning did not create an output file."
            )

        print(
            "Cleaning completed:",
            cleaned_file
        )

    except Exception as error:

        raise Exception(
            f"Text cleaning failed: {error}"
        )

    # =====================================================
    # STEP 3 - OCR VALIDATION
    # =====================================================

    print("\n[3/4] OCR Validation...")

    try:

        from src.ocr_validate import (
            process_text_file as validate_file
        )

        validated_file, validation_report = (
            validate_file(
                cleaned_file
            )
        )

        if not validated_file:

            raise Exception(
                "Validation did not create an output file."
            )

        print(
            "Validation completed:",
            validated_file
        )

    except Exception as error:

        raise Exception(
            f"OCR validation failed: {error}"
        )

    # =====================================================
    # STEP 4 - STRUCTURE EXTRACTION
    # =====================================================

    print("\n[4/4] Structure Extraction...")

    try:

        from src.structure_extractor import (
            process_validated_file
        )

        structured_file = (
            process_validated_file(
                validated_file
            )
        )

        if not structured_file:

            raise Exception(
                "Structure extraction did not create JSON."
            )

        print(
            "Structure extraction completed:",
            structured_file
        )

    except Exception as error:

        raise Exception(
            f"Structure extraction failed: {error}"
        )

    print("\n")
    print("=" * 60)
    print("COALMIND PIPELINE COMPLETED")
    print("=" * 60)

    return structured_file


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 60)
    print("COALMIND DASHBOARD")
    print("=" * 60)

    print(
        "Open:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print("=" * 60)
    print("\n")

    app.run(
        debug=True
    )