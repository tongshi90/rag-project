import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatPanel } from './components/ChatPanel';
import { HomePage } from './components/HomePage';
import { SkillListPage } from './components/SkillListPage';
import { SkillFileListPage } from './components/SkillFileListPage';
import { apiService } from './services/api';
import type { Message } from './types';
import type { SkillCard } from './types';
import './index.css';

type PageType = 'home' | 'rag' | 'skill' | 'skill-files';

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('home');
  const [selectedSkill, setSelectedSkill] = useState<SkillCard | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '您好！我是RAG知识库助手。请上传文档，然后我可以帮您回答与文档相关的问题。',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // 先显示loading，不创建AI消息
    setIsLoading(true);

    const assistantMessageId = (Date.now() + 1).toString();
    let firstChunkReceived = false;
    let accumulatedContent = '';

    try {
      await apiService.sendMessageStream(content, (chunk) => {
        accumulatedContent += chunk;

        // 收到第一个chunk时：创建AI消息并隐藏loading
        if (!firstChunkReceived) {
          firstChunkReceived = true;
          setIsLoading(false);
          // 此时才创建AI消息
          const assistantMessage: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: accumulatedContent,
            timestamp: new Date().toISOString(),
          };
          setMessages(prev => [...prev, assistantMessage]);
        } else {
          // 后续chunk：更新已存在的AI消息
          setMessages(prev => prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: accumulatedContent }
              : msg
          ));
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
      // 出错时创建错误消息
      const errorMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '抱歉，发生了错误，请稍后重试。',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  return (
    <div className="app-container">
      {currentPage === 'home' && (
        <HomePage onSelectPage={setCurrentPage} />
      )}

      {currentPage === 'rag' && (
        <div className="rag-page">
          <div className="rag-header">
            <button className="back-button" onClick={() => setCurrentPage('home')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7"></path>
              </svg>
              返回首页
            </button>
            <h1 className="rag-title">RAG 知识库</h1>
          </div>
          <div className="rag-content">
            <Sidebar />
            <div className="main-content">
              <ChatPanel
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
              />
            </div>
          </div>
        </div>
      )}

      {currentPage === 'skill' && (
        <SkillListPage
          onBackToHome={() => setCurrentPage('home')}
          onSelectSkill={(skill) => {
            setSelectedSkill(skill);
            setCurrentPage('skill-files');
          }}
        />
      )}

      {currentPage === 'skill-files' && selectedSkill && (
        <SkillFileListPage
          skill={selectedSkill}
          onBackToSkills={() => setCurrentPage('skill')}
        />
      )}
    </div>
  );
}

export default App;
