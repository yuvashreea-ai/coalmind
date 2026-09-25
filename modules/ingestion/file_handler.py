import os
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {
    "pdf",
    "docx",
    "xlsx",
    "xls",
    "csv",
    "png",
    "jpg",
    "jpeg"
}


def allowed_file(filename):
    """Check whether the uploaded file type is supported."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_file(file, upload_folder):
    """Save an uploaded file and return its path and type."""

    if file is None or file.filename == "":
        return None, "No file selected"

    if not allowed_file(file.filename):
        return None, "Unsupported file type"

    filename = secure_filename(file.filename)

    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    file_type = filename.rsplit(".", 1)[1].lower()

    return file_path, file_type