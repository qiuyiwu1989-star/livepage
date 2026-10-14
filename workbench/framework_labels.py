"""Conservative display normalization; these are AI associations, not taxonomy approval."""
import re
ALIASES={
 'AIGD':'AIGD','AIGD 五层':'AIGD','AIGD 五层架构':'AIGD','AIGD五层架构':'AIGD',
 '九格':'九格画布','九格画布':'九格画布',
 '四代思维':'四代思维跃迁','四代思维跃迁':'四代思维跃迁',
 '永乐教育':'永乐教育','永乐教育方法论':'永乐教育',
 '潘云鹤 1982 学派':'潘云鹤 1982 学派','潘云鹤1982学派':'潘云鹤 1982 学派',
 'PF/FS/CS':'PF/FS/CS','PF·FS·CS':'PF/FS/CS','PF/FS/CS 三栏':'PF/FS/CS','PF/FS/CS 三角':'PF/FS/CS',
 'CCC':'CCC 模型','CCC模型':'CCC 模型','CCC 模型':'CCC 模型',
 '六维框架':'六维框架','五大构成':'五大构成','智能体管理学':'智能体管理学',
 '路演双模板':'路演双模板','产品定义方法论':'产品定义方法论','造物云':'造物云','全链路':'全链路',
}
def normalize(value):
 raw=' / '.join(map(str,value)) if isinstance(value,list) else str(value or '').strip()
 if raw in ('','—','null','None'):return [],'unassigned'
 if any(word in raw for word in ('可能','或','不确定','待确认')):return [],'pending'
 text=re.sub(r'（[^）]*）|\([^)]*\)','',raw).strip().replace('PF/FS/CS','PF_FS_CS')
 parts=[x.strip().replace('PF_FS_CS','PF/FS/CS') for x in re.split(r'\s*/\s*|、|\+',text) if x.strip()]
 labels=list(dict.fromkeys(ALIASES[p] for p in parts if p in ALIASES))
 return labels,'pending' if any(p not in ALIASES for p in parts) else 'normalized_ai_candidate'
