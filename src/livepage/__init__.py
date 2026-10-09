"""LivePage domain contracts. Not a production application server."""

def validate_segment(segment, duration):
    """Validate an audio reference without promoting an inferred link to fact."""
    start, end = segment['start_seconds'], segment['end_seconds']
    if not 0 <= start < end <= duration:
        raise ValueError('Audio segment must fall within source duration')
    if segment['alignment_method'] == 'semantic_candidate' and segment['alignment_status'] == 'confirmed':
        if not segment.get('confirmation_ref'):
            raise ValueError('Confirmation requires a separate review record')
    return segment
