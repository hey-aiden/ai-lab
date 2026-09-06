// 多模态定义与 mock 会话数据。
// 每个模态有独立的会话列表;消息的 `type` 字段为后续接入
// 图片(imageUrl)/语音(audioUrl)等具体模块预留。

export const MODALITIES = [
  { id: 'text', label: '文本对话', icon: '💬' },
  { id: 'image', label: '文生图', icon: '🖼️' },
  { id: 'audio', label: '语音', icon: '🎙️' },
];

export const DEFAULT_MODALITY_ID = MODALITIES[0].id;

let seed = 0;
const uid = (prefix = 'id') => `${prefix}-${Date.now().toString(36)}-${(seed++).toString(36)}`;

const msg = (role, content, type = 'text') => ({
  id: uid('m'),
  role, // 'user' | 'assistant'
  content,
  type,
  createdAt: new Date().toISOString(),
});

// 供 ChatPage 追加消息使用
export const createMessage = msg;

// 发送消息后的占位回复(后续接入具体模型后替换)
export const PLACEHOLDER_REPLY = {
  text: '这是占位回复,后续将接入具体文本模型。',
  image: '这是占位回复,后续将接入文生图模型。',
  audio: '这是占位回复,后续将接入语音模型。',
};

// 按模态分桶的 mock 会话。结构:
// { [modalityId]: { conversations: [{ id, title, createdAt, messages }] } }
export const INITIAL_CONVERSATIONS = {
  text: {
    conversations: [
      {
        id: uid('c'),
        title: '用 React 写一个聊天组件',
        createdAt: new Date().toISOString(),
        messages: [
          msg('user', '我想用 React 写一个支持多模态切换的 AI 聊天页面,有什么结构建议?'),
          msg(
            'assistant',
            '建议把「模态」作为顶层维度:顶部 tab 切换模态,左侧会话列表和中央消息历史都跟随当前模态。这样不同模态的数据天然隔离,后续接入不同模型也互不干扰。'
          ),
        ],
      },
      {
        id: uid('c'),
        title: '解释一下 react-router',
        createdAt: new Date().toISOString(),
        messages: [
          msg('user', 'react-router 的 Routes 和 Route 有什么区别?'),
          msg('assistant', 'Routes 是容器,负责匹配当前 URL 并渲染命中的 Route;Route 定义某条路径要渲染的组件。'),
        ],
      },
    ],
  },
  image: {
    conversations: [
      {
        id: uid('c'),
        title: '生成一张赛博朋克城市',
        createdAt: new Date().toISOString(),
        messages: [
          msg('user', '生成一张夜晚的赛博朋克城市,霓虹灯、雨夜、俯视视角。', 'image'),
          msg('assistant', '(图片生成占位:这里后续会展示文生图结果)', 'image'),
        ],
      },
      {
        id: uid('c'),
        title: '设计一个 logo',
        createdAt: new Date().toISOString(),
        messages: [
          msg('user', '帮我设计一个极简风格的 AI 助手 logo。', 'image'),
          msg('assistant', '(图片生成占位:这里后续会展示 logo 方案)', 'image'),
        ],
      },
    ],
  },
  audio: {
    conversations: [
      {
        id: uid('c'),
        title: '一段英文朗读',
        createdAt: new Date().toISOString(),
        messages: [
          msg('user', '帮我把下面这句话朗读出来。', 'audio'),
          msg('assistant', '(语音占位:这里后续会展示可播放的音频)', 'audio'),
        ],
      },
    ],
  },
};

// 新建会话时使用
export const createEmptyConversation = () => ({
  id: uid('c'),
  title: '新对话',
  createdAt: new Date().toISOString(),
  messages: [],
});
