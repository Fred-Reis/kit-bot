from google.cloud import vision
from google.oauth2 import service_account
from google.cloud.vision_v1 import types

creds = service_account.Credentials.from_service_account_file(
    "/Users/fredericolopes/gcp/vision.json"
)


client = vision.ImageAnnotatorClient(credentials=creds)


def google_ocr(file):

    with open(file, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)  # pylint: disable=no-member

    return response.full_text_annotation.text


def google_ocr_bytes(image_bytes: bytes) -> str:

    response = client.annotate_image(
        {
            "image": {"content": image_bytes},
            "features": [{"type_": types.Feature.Type.DOCUMENT_TEXT_DETECTION}],
            "image_context": {"language_hints": ["pt"]},
        }
    )

    if not response.full_text_annotation:
        return ""

    return response.full_text_annotation.text
