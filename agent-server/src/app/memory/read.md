#### 为什么 MySqlChatMessageHistory 不能做成单例？

1. 绑定了数据库会话（AsyncSession）

在现代 Python 异步 Web 框架（如 FastAPI）中，数据库的 AsyncSession 是每个请求独立的（Request-Scoped）

 - 每个 HTTP 请求进来时，框架会通过依赖注入开启一个新的 AsyncSession
 - 请求结束后，这个 Session 就会被关闭
 - 如果把 MySqlChatMessageHistory 做成单例，它的内部必然会死死绑定某一个旧的 AsyncSession，导致：
 - · 跨请求污染：用户 A 和用户 B 的请求可能会共用同一个 Session，导致数据混乱。
 - · Session 过期报错：上一个请求结束关闭 Session 后，下一个请求再去用就会抛出 Session is closed 异常

2. 绑定了 session_id（会话窗口 ID）

- session_id 是随着每次请求传入的参数决定的每个用户的聊天窗口是动态变化的（用户可能点开“对话 A”，又点开“对话 B”）
- session_id 是随着每次请求传入的参数决定的
- 如果是单例，你就无法在同一个进程里同时处理多个用户在不同窗口聊天的并发请求

#### 总结
应该用“请求作用域（Request-Scoped）”的生命周期：随用随建，用完即毁。因为它的底层依赖 AsyncSession，这样做才能保证线程/协程安全，避免并发冲突

#### 那 AsyncSessionLocal（session 工厂）能做单例吗？

能。它和上面 MySqlChatMessageHistory 的情况正好相反——因为它是「工厂」，不是「会话」。

| 对象 | 能否单例 | 原因 |
|------|---------|------|
| engine（连接池） | 能 | 连接池天生为并发共享设计，安全地给每个 session 分配独立连接 |
| AsyncSessionLocal（session 工厂） | 能 | 无状态模板，只负责 new 出新的 AsyncSession |
| AsyncSession（会话） | 不能 | 持有事务、身份映射、未提交状态，跨请求共享会串数据 |
| MySqlChatMessageHistory | 不能 | 绑定了某个 AsyncSession + session_id |

关键区别：**单例的是「造 session 的模具」（工厂），不是「session 本身」。**

每次 `async with session_factory() as session:` 都会开出一个全新的、独立的 AsyncSession；
底层连接池用锁/队列安全分配连接、用完回收。所以工厂做单例是安全的，真正不能跨请求共享的是 AsyncSession。