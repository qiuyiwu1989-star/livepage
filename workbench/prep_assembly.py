"""Map a complete narrative to slide references without dropping oral sections."""

def assembly_plan(doc, deduplicate=True):
    items, seen, pending, repeated, cues = [], set(), [], [], []
    scripts = (doc.get('manuscript') or {}).get('sections', [])
    for index, section in enumerate(doc['outline']['sections']):
        script = scripts[index].get('script','') if index < len(scripts) else ''
        notes = ('【AI草稿，待讲者核对】第'+str(index+1)+'段 '+section['title']+' · '
                 +str(section['minutes'])+'分钟（含互动）。\n'+section.get('purpose','')
                 +'\n过渡：'+section.get('transition','')+'\n'+script
                 +'\n主持提示：'+(scripts[index].get('stage_directions','') if index<len(scripts) else section.get('interaction',''))
                 +'\n来源：'+', '.join(section.get('source_ids',[])))
        ids = []
        for pid in section.get('page_ids',[]):
            if deduplicate and pid in seen:
                repeated.append(dict(page_id=pid,section=section['title']))
                continue
            seen.add(pid);ids.append(pid)
        if ids:
            full = '\n\n'.join(pending+[notes]);pending=[]
            first = len(items)
            for offset,pid in enumerate(ids):
                page_notes = full if offset==0 else ('【同段续页】'+section['title']+' · 本段合计'+str(section['minutes'])+'分钟。完整讲稿见本段首张，按现场节奏继续。')
                items.append(dict(page_id=pid,chapter=section['title'],notes=page_notes))
            cues.append(dict(section_index=index,section=section['title'],entry_index=first,kind='slide'))
        elif items:
            items[-1]['notes'] += '\n\n【继续口述／无新增画面】\n'+notes
            cues.append(dict(section_index=index,section=section['title'],entry_index=len(items)-1,kind='oral'))
        else:
            pending.append(notes)
            cues.append(dict(section_index=index,section=section['title'],entry_index=0,kind='opening_oral'))
    if not items:
        raise ValueError('当前结构没有选用活页；请先按讲稿试讲，或补充适合的页面。')
    if any(len(e['notes'])>20000 for e in items):
        raise ValueError('口述讲稿超过单页备注容量；请先拆分段落或补页，不会静默截断讲稿。')
    review = dict(deduplicated=deduplicate,omitted_repeats=repeated,section_cues=cues,
                  oral_sections=[c['section'] for c in cues if c['kind']!='slide'],
                  note='口述段已按顺序纳入相邻页备注；同段续页不重复整段讲稿。重复引用可在组装中手工添加。')
    return items,review
