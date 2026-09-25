import os
import shutil
import pymupdf
import pytesseract
import cv2
import numpy as np

from PIL import Image


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or "/usr/bin/tesseract"


# ============================================================
# FOLDERS
# ============================================================

INPUT_FOLDER = r"C:\coalmind\input"
OUTPUT_FOLDER = r"C:\coalmind\output"


# ============================================================
# PREPROCESSING FUNCTIONS
# ============================================================

def check_image_quality(image):
    """
    Check basic image quality using brightness and contrast.

    Returns:
        quality information dictionary
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    mean_brightness = float(
        np.mean(gray)
    )

    contrast = float(
        np.std(gray)
    )

    return {
        "brightness": mean_brightness,
        "contrast": contrast
    }


def denoise_image(image):
    """
    Reduce noise while preserving text edges.
    """

    return cv2.fastNlMeansDenoising(
        image,
        None,
        h=10,
        templateWindowSize=7,
        searchWindowSize=21
    )


def calculate_skew_angle(image):
    """
    Estimate the text skew angle using thresholded text pixels.
    """

    # Invert threshold so text becomes white
    # and background becomes black.
    _, binary = cv2.threshold(
        image,
        0,
        255,
        cv2.THRESH_BINARY_INV
        + cv2.THRESH_OTSU
    )

    coordinates = np.column_stack(
        np.where(binary > 0)
    )

    if len(coordinates) < 100:
        return 0.0

    angle = cv2.minAreaRect(
        coordinates
    )[-1]

    if angle < -45:
        angle = -(90 + angle)

    else:
        angle = -angle

    return angle


def deskew_image(image):
    """
    Correct image skew only when the estimated
    angle is significant.
    """

    angle = calculate_skew_angle(
        image
    )

    # Avoid unnecessary rotation
    if abs(angle) < 0.5:

        return image, 0.0

    height, width = image.shape[:2]

    center = (
        width // 2,
        height // 2
    )

    rotation_matrix = cv2.getRotationMatrix2D(
        center,
        angle,
        1.0
    )

    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated, angle


def threshold_image(image):
    """
    Apply both Otsu and adaptive thresholding.

    Select the version with the stronger text/background
    separation based on image contrast.
    """

    # --------------------------------------------------------
    # Otsu threshold
    # --------------------------------------------------------

    _, otsu = cv2.threshold(
        image,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU
    )

    # --------------------------------------------------------
    # Adaptive threshold
    # --------------------------------------------------------

    adaptive = cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    # --------------------------------------------------------
    # Choose based on foreground pixel ratio
    #
    # This avoids blindly using one method for every page.
    # --------------------------------------------------------

    otsu_white_ratio = (
        np.mean(otsu == 255)
    )

    adaptive_white_ratio = (
        np.mean(adaptive == 255)
    )

    # If Otsu produces a reasonable document-like
    # foreground/background distribution, use it.
    if 0.45 <= otsu_white_ratio <= 0.98:

        return otsu, "Otsu"

    return adaptive, "Adaptive"


# ============================================================
# OCR WITH CONFIDENCE
# ============================================================

def perform_ocr(image):
    """
    Perform Tesseract OCR and calculate average confidence.
    """

    # --------------------------------------------------------
    # OCR text
    # --------------------------------------------------------

    text = pytesseract.image_to_string(
        image,
        lang="eng"
    )

    # --------------------------------------------------------
    # OCR confidence data
    # --------------------------------------------------------

    data = pytesseract.image_to_data(
        image,
        lang="eng",
        output_type=pytesseract.Output.DICT
    )

    confidences = []

    for confidence in data["conf"]:

        try:

            confidence = float(
                confidence
            )

            if confidence >= 0:

                confidences.append(
                    confidence
                )

        except (
            ValueError,
            TypeError
        ):

            continue

    if confidences:

        average_confidence = (
            sum(confidences)
            /
            len(confidences)
        )

    else:

        average_confidence = 0.0

    return (
        text,
        average_confidence
    )


# ============================================================
# PAGE PREPROCESSING
# ============================================================

def preprocess_page(page):
    """
    Complete preprocessing pipeline:

    PDF page
        ↓
    300 DPI rendering
        ↓
    Grayscale
        ↓
    Image quality check
        ↓
    Denoising
        ↓
    Deskew if needed
        ↓
    Otsu / Adaptive threshold
        ↓
    OCR
    """

    # --------------------------------------------------------
    # 1. Render PDF page at 300 DPI
    #
    # 72 DPI is the PDF default.
    # 300 / 72 ≈ 4.17
    # --------------------------------------------------------

    scale = 300 / 72

    matrix = pymupdf.Matrix(
        scale,
        scale
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )

    # --------------------------------------------------------
    # Convert Pixmap → OpenCV image
    # --------------------------------------------------------

    image = np.frombuffer(
        pix.samples,
        dtype=np.uint8
    )

    image = image.reshape(
        pix.height,
        pix.width,
        pix.n
    )

    # PyMuPDF with alpha=False normally gives RGB
    if pix.n == 3:

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR
        )

    # --------------------------------------------------------
    # 2. Grayscale
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # --------------------------------------------------------
    # 3. Image quality check
    # --------------------------------------------------------

    quality = check_image_quality(
        image
    )

    # --------------------------------------------------------
    # 4. Denoise
    # --------------------------------------------------------

    denoised = denoise_image(
        gray
    )

    # --------------------------------------------------------
    # 5. Deskew if needed
    # --------------------------------------------------------

    deskewed, angle = deskew_image(
        denoised
    )

    # --------------------------------------------------------
    # 6. Otsu / Adaptive threshold
    # --------------------------------------------------------

    thresholded, method = (
        threshold_image(
            deskewed
        )
    )

    return (
        thresholded,
        quality,
        angle,
        method
    )


# ============================================================
# EXTRACT TEXT FROM PDF
# ============================================================

def extract_text_from_pdf(pdf_path):
    """
    Extract text from every page of a scanned PDF
    using preprocessing + Tesseract OCR.
    """

    document = pymupdf.open(
        pdf_path
    )

    all_text = []

    print(
        f"\nProcessing: "
        f"{os.path.basename(pdf_path)}"
    )

    print(
        f"Total pages: "
        f"{len(document)}\n"
    )

    for page_number, page in enumerate(
        document,
        start=1
    ):

        print(
            f"Processing page "
            f"{page_number}/{len(document)}..."
        )

        try:

            # ------------------------------------------------
            # PREPROCESSING
            # ------------------------------------------------

            (
                processed_image,
                quality,
                angle,
                threshold_method
            ) = preprocess_page(
                page
            )

            print(
                f"  Image brightness: "
                f"{quality['brightness']:.2f}"
            )

            print(
                f"  Image contrast: "
                f"{quality['contrast']:.2f}"
            )

            print(
                f"  Deskew angle: "
                f"{angle:.2f}°"
            )

            print(
                f"  Thresholding: "
                f"{threshold_method}"
            )

            # ------------------------------------------------
            # OCR
            # ------------------------------------------------

            (
                text,
                confidence
            ) = perform_ocr(
                processed_image
            )

            print(
                f"  OCR confidence: "
                f"{confidence:.2f}%"
            )

            # ------------------------------------------------
            # Store page-wise text
            # ------------------------------------------------

            page_text = (
                f"\n{'=' * 60}\n"
                f"PAGE {page_number}\n"
                f"{'=' * 60}\n\n"
                f"{text.strip()}\n"
            )

            all_text.append(
                page_text
            )

        except Exception as error:

            print(
                f"  OCR error on page "
                f"{page_number}: {error}"
            )

            page_text = (
                f"\n{'=' * 60}\n"
                f"PAGE {page_number}\n"
                f"{'=' * 60}\n\n"
                f"[OCR ERROR: {error}]\n"
            )

            all_text.append(
                page_text
            )

    document.close()

    return "\n".join(
        all_text
    )


# ============================================================
# PROCESS PDF
# ============================================================

def process_pdf(pdf_path):
    """
    Process one PDF and save the OCR result
    as a TXT file.

    Returns:
        Path of the generated TXT file.
    """

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    text = extract_text_from_pdf(
        pdf_path
    )

    filename = os.path.splitext(
        os.path.basename(pdf_path)
    )[0]

    output_path = os.path.join(
        OUTPUT_FOLDER,
        filename + ".txt"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            text
        )

    print(
        "\nOCR completed successfully!"
    )

    print(
        "Output saved to:"
    )

    print(
        output_path
    )

    return output_path


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    pdf_files = [
        file
        for file in os.listdir(
            INPUT_FOLDER
        )
        if file.lower().endswith(
            ".pdf"
        )
    ]

    if not pdf_files:

        print(
            "No PDF found in the input folder."
        )

        return

    for pdf_file in pdf_files:

        pdf_path = os.path.join(
            INPUT_FOLDER,
            pdf_file
        )

        process_pdf(
            pdf_path
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()