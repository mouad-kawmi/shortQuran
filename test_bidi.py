import arabic_reshaper
from bidi.algorithm import get_display

text = "??????? ???????? ?????????"
reshaper = arabic_reshaper.ArabicReshaper(
    arabic_reshaper.config_for_true_type_font("quran_font.ttf", arabic_reshaper.ENABLE_ALL_LIGATURES)
)
reshaped = reshaper.reshape(text)
bidi_text = get_display(reshaped)

with open('test_bidi.txt', 'w', encoding='utf-8') as f:
    f.write(bidi_text)
