from backend.app.utils.text import clean_display_text


def test_clean_display_text_repairs_common_pdf_mojibake():
    assert clean_display_text("qatlÂ­eÂ­amd â test") == "qatl-e-amd — test"


def test_clean_display_text_preserves_urdu():
    assert clean_display_text("یہ پاکستانی قانون ہے۔") == "یہ پاکستانی قانون ہے۔"
