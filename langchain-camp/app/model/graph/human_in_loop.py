"""
LangGraph 人机协同(human-in-the-loop):用 interrupt() 在节点里暂停,等人做决定后恢复。

========== 一、为什么不能直接调 interrupt ==========
- interrupt() 必须在「图的节点函数内部」调用;直接调会报
  RuntimeError: Called get_config outside of a runnable context
- 必须开 checkpointer:暂停时要持久化状态,恢复时才能从断点继续

========== 二、human_in_loop() 是「同步单进程」演示 ==========
审批人就在同一进程里,用 input() 直接读决定,再 Command(resume=...) 恢复。

========== 三、接口异步场景:状态如何切换 ==========
真实系统里,审批人常在另一个进程/终端(Web 接口、另一个服务)。核心机制不变,
因为 interrupt() 暂停时已经把状态写进 checkpointer,只要两端共享
「同一个 checkpointer + 同一个 thread_id」,就能完成状态切换。

状态机(以退款审批为例):

    pending(待审批)
      │  发起端: graph.invoke() 跑到 interrupt 暂停,approved 字段还没填,状态落盘
      ▼
    awaiting_approval(等待人工)
      │  审批端: graph.get_state(config) 读到待审批的 interrupt 值
      ▼
    completed(已完成)
         审批端: graph.invoke(Command(resume=decision), config) 恢复
                 approved 字段被填上,图走到 END

伪代码(两个独立接口,共享同一个持久化 graph):

    # ---- 进程启动时构建一次,所有接口共享 ----
    # 关键:checkpointer 必须持久化(跨进程) -> SqliteSaver / PostgresSaver / RedisSaver
    #      不能用 InMemorySaver(进程内内存,别的接口读不到)
    graph = build_approval_graph(checkpointer=SqliteSaver(...))

    # 接口 A(发起侧): POST /refund
    def create_refund():
        thread_id = "order-001"              # 会话钥匙,要回给审批端
        config = {"configurable": {"thread_id": thread_id}}
        graph.invoke({}, config=config)      # 跑到 interrupt 暂停,状态落盘
        return {"thread_id": thread_id, "status": "pending"}   # 立刻返回,不阻塞等审批

    # 接口 B(审批侧,查待办): GET /pending/{thread_id}
    def get_pending(thread_id):
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(config)
        return [t.interrupts[0].value for t in snapshot.tasks]   # 待审批内容

    # 接口 C(审批侧,恢复): POST /approve  {thread_id, decision}
    def approve(thread_id, decision):
        config = {"configurable": {"thread_id": thread_id}}
        return graph.invoke(Command(resume=decision), config=config)   # approved 被填上

要点:
1. 状态切换的载体是 checkpointer —— interrupt 暂停/恢复全靠它持久化;
2. thread_id 是两端定位「同一个暂停点」的钥匙;
3. 发起端不阻塞等结果,审批端单独 resume;发起端之后可轮询 get_state 或靠回调拿结果。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict):
    approved: str = ""  # 存人机交互的最终结果


def approval_node(state: ApprovalState):
    # interrupt 必须在节点函数内部调用。图会在这里暂停,把 value 抛给外部。
    result = interrupt({"message": "是否批准退款？"})
    # 恢复后,result = 人通过 Command(resume=...) 传进来的值
    return {"approved": result}


def build_approval_graph():
    # 注:同步演示硬编码 InMemorySaver;接口异步场景要把 checkpointer 做成参数,
    #     注入持久化的 SqliteSaver / PostgresSaver / RedisSaver,多个接口才能共享同一份状态。
    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    return builder.compile(checkpointer=InMemorySaver())


def human_in_loop():
    """完整演示(同步版):把上面「接口 A → B → C」三步串在同一个进程里跑。

    对照异步接口:
      本函数第①步 = 接口 A(发起)、第②步 = 接口 B(查待办)、第③④步 = 接口 C(审批恢复)。
    """
    graph = build_approval_graph()
    config = {"configurable": {"thread_id": "order-001"}}

    # ① 发起:跑到 interrupt 暂停,状态被持久化(对应接口 A)
    graph.invoke({}, config=config)

    # ② 查待办:从 checkpointer 读暂停信息(对应接口 B)
    snapshot = graph.get_state(config)
    interrupt_value = snapshot.tasks[0].interrupts[0].value
    print("图已暂停,等待人工审批:", interrupt_value)

    # ③ 模拟人做决定:异步场景里,这一步发生在「另一个进程」的审批接口(接口 C)
    decision = input("你的决定(批准/拒绝): ").strip()

    # ④ 审批恢复:Command(resume=...) 让节点从头重跑,interrupt 返回人给的值(接口 C)
    result = graph.invoke(Command(resume=decision), config=config)
    print("审批结果:", result)
