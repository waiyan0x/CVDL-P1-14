"""EasyOCR adapter preserving multiline destination text."""
class EasyOCRAdapter:
    confidence_method = 'character_weighted_word_probability'

    def __init__(self, settings):
        import easyocr
        self.reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=str(settings.easyocr_dir),
                                     download_enabled=False, verbose=False)

    def read(self, crop, field):
        if field == 'bus_number':
            height, width = crop.shape[:2]
            lines = self.reader.recognize(crop, horizontal_list=[[0, width, 0, height]], free_list=[], detail=1,
                allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
        else:
            lines = self.reader.readtext(crop, detail=1, paragraph=False, min_size=3, text_threshold=.5,
                                         low_text=.3, canvas_size=1280)
        lines.sort(key=lambda line: (round(line[0][0][1] / 15), line[0][0][0]))
        raw = (' ' if field == 'bus_number' else '\n').join(line[1] for line in lines).strip()
        weight = sum(len(line[1]) for line in lines)
        confidence = sum(len(line[1]) * line[2] for line in lines) / weight if weight else 0
        return raw, float(confidence)
