"""Q1（派发队列）与 Q2（发送队列）：跨线程传递数据的唯一通道。"""

import queue

# Q1：飞书消息 → 派发线程。
# 元素契约：{"sender": str(用户open_id), "raw": str(原始文本)}
Q1: "queue.Queue[dict]" = queue.Queue()

# Q2：下游发送任务 → 飞书发送线程。
# text 任务元素：{"kind":"text","program":str,"program_id":int,"target":str,"content":str}
# file 任务元素：{"kind":"file","program":str,"program_id":int,"target":str,
#                "file_name":str,"data":bytes,"file_type":str,"duration_ms":int|None}
Q2: "queue.Queue[dict]" = queue.Queue()
