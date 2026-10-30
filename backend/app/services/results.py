"""Status decisions keep observations separate from reference guesses."""
import re

MESSAGES = {
    'no_eds': 'No EDS display regions detected.',
    'unreadable': 'Display detected, but no readable text passed the OCR threshold.',
    'partial': 'Only part of the display could be read; reference destination is unconfirmed.',
    'unknown_match': 'Text read, but no reference endpoint could be confirmed.',
    'matched': 'Reference endpoint matched; travel direction remains unverified.',
}


def accepted_text(field, threshold):
    confidence = field.get('ocr_confidence')
    return bool(field.get('raw', '').strip()) and confidence is not None and confidence >= threshold


def match_fields(fields, matcher, options):
    number = fields.get('bus_number', {})
    destination = fields.get('destination', {})
    number_read = accepted_text(number, options.ocr_threshold)
    destination_read = accepted_text(destination, options.ocr_threshold)
    service = re.sub(r'\s+', '', number.get('raw', '').upper())
    usable_service = number_read and re.fullmatch(r'[0-9]{1,3}[A-Z]{0,2}', service)
    match = matcher.match(service if usable_service else '', destination.get('raw', '') if destination_read else '', options.similarity)
    if not number_read and not destination_read:
        status = 'unreadable'
    elif not number_read or not destination_read:
        status = 'partial'
    elif match['status'] == 'matched':
        status = 'matched'
    else:
        status = 'unknown_match'
    return status, match


def frame_status(results):
    if not results:
        return 'no_eds'
    for status in ('matched', 'unknown_match', 'partial', 'unreadable'):
        if any(result['status'] == status for result in results):
            return status
    return 'unreadable'
