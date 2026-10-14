"""Read-only processing evidence; imported is never equivalent to queued."""
from collections import Counter

def page_status(page, job=None):
    annotation = page.get('annotation') or {}
    processing = page.get('processing') or {}
    html = page.get('html') or {}
    has_annotation = bool(annotation.get('vlm_summary') or annotation.get('summary'))
    annotation_state = 'candidate' if has_annotation else 'pending'
    html_state = 'draft' if html.get('status') in {'local_exists', 'unverified_remote'} else 'pending'
    # Only a scoped human review with an evidence reference confirms a stage.
    reviews = page.get('stage_reviews') or {}
    for stage in ('annotation', 'html'):
        review = reviews.get(stage) or {}
        if review.get('status') == 'confirmed' and review.get('evidence_ref'):
            if stage == 'annotation' and has_annotation: annotation_state = 'confirmed'
            if stage == 'html' and html_state == 'draft': html_state = 'confirmed'
    task = (job or {}).get('status', 'unregistered')
    if task not in {'queued', 'running', 'failed', 'succeeded', 'blocked'}: task = 'unregistered'
    return {'annotation': annotation_state, 'html': html_state, 'task': task,
            'source_text_available': bool(annotation.get('source_text') or annotation.get('source_visible_text')),
            'complete': annotation_state == 'confirmed' and html_state == 'confirmed'}

def course_summary(decks, pages, jobs=None):
    jobs = jobs or {}
    result = []
    for deck in decks:
        rows = [p for p in pages if p.get('deck_id') == deck['deck_id']]
        states = [page_status(p, jobs.get(p['page_id'])) for p in rows]
        counts = {stage: dict(Counter(s[stage] for s in states)) for stage in ('annotation', 'html', 'task')}
        result.append({'deck_id': deck['deck_id'], 'title': deck.get('title'), 'page_count': len(rows),
                       'source_kind': 'keynote' if deck['deck_id'].startswith('keynote-') else 'pdf' if deck['deck_id'].startswith('pdf-') else 'legacy',
                       'counts': counts, 'complete': sum(s['complete'] for s in states)})
    return result
