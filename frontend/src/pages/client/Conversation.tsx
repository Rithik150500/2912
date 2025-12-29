import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { clientApi } from '../../services/api';
import { ArrowLeft, Send, Users, Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  sender_type: 'client' | 'ai' | 'advocate';
  sender_name?: string;
  content: string;
  created_at: string;
}

interface Conversation {
  id: string;
  phase: string;
  case_id?: string;
  messages: Message[];
}

export default function ClientConversation() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversation();
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversation = async () => {
    if (!id) return;
    try {
      const response = await clientApi.getConversation(id);
      setConversation(response.data);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || sending || !id) return;

    const content = message;
    setMessage('');
    setSending(true);

    // Optimistically add user message
    const tempUserMessage: Message = {
      id: 'temp-' + Date.now(),
      sender_type: 'client',
      content,
      created_at: new Date().toISOString(),
    };

    setConversation((prev) =>
      prev
        ? {
            ...prev,
            messages: [...prev.messages, tempUserMessage],
          }
        : null
    );

    try {
      const response = await clientApi.sendMessage(id, content);
      const { user_message, ai_message, recommendations_available } = response.data;

      setConversation((prev) =>
        prev
          ? {
              ...prev,
              messages: [
                ...prev.messages.filter((m) => m.id !== tempUserMessage.id),
                user_message,
                ai_message,
              ],
            }
          : null
      );

      if (recommendations_available) {
        setShowRecommendations(true);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic message on error
      setConversation((prev) =>
        prev
          ? {
              ...prev,
              messages: prev.messages.filter((m) => m.id !== tempUserMessage.id),
            }
          : null
      );
    } finally {
      setSending(false);
    }
  };

  const getSenderIcon = (senderType: string) => {
    switch (senderType) {
      case 'client':
        return <User className="h-6 w-6" />;
      case 'ai':
        return <Bot className="h-6 w-6" />;
      case 'advocate':
        return <Users className="h-6 w-6" />;
      default:
        return <User className="h-6 w-6" />;
    }
  };

  const getSenderName = (senderType: string, name?: string) => {
    switch (senderType) {
      case 'client':
        return 'You';
      case 'ai':
        return 'AI Assistant';
      case 'advocate':
        return name || 'Advocate';
      default:
        return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Conversation not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm flex-shrink-0">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate('/client')}
              className="p-2 hover:bg-gray-100 rounded-full"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold">Legal Consultation</h1>
              <p className="text-sm text-gray-500">
                {conversation.phase === 'advocate_active'
                  ? 'Chatting with your advocate'
                  : 'AI-powered legal assistance'}
              </p>
            </div>
          </div>
          {conversation.case_id && showRecommendations && (
            <button
              onClick={() => navigate(`/client/cases/${conversation.case_id}/select-advocate`)}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Users className="h-4 w-4" />
              <span>Find Advocates</span>
            </button>
          )}
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          {conversation.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender_type === 'client' ? 'justify-end' : 'justify-start'} message-animate`}
            >
              <div
                className={`flex max-w-[80%] ${
                  msg.sender_type === 'client' ? 'flex-row-reverse' : 'flex-row'
                }`}
              >
                <div
                  className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
                    msg.sender_type === 'client'
                      ? 'bg-primary-100 text-primary-600 ml-3'
                      : msg.sender_type === 'ai'
                      ? 'bg-gray-100 text-gray-600 mr-3'
                      : 'bg-green-100 text-green-600 mr-3'
                  }`}
                >
                  {getSenderIcon(msg.sender_type)}
                </div>
                <div>
                  <div
                    className={`text-xs mb-1 ${
                      msg.sender_type === 'client' ? 'text-right' : 'text-left'
                    } text-gray-500`}
                  >
                    {getSenderName(msg.sender_type, msg.sender_name)}
                  </div>
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      msg.sender_type === 'client'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white shadow-sm'
                    }`}
                  >
                    {msg.sender_type === 'client' ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                  <div
                    className={`text-xs mt-1 ${
                      msg.sender_type === 'client' ? 'text-right' : 'text-left'
                    } text-gray-400`}
                  >
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <footer className="bg-white border-t flex-shrink-0">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center space-x-4">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              disabled={sending}
              className="flex-1 rounded-full border border-gray-300 px-6 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={!message.trim() || sending}
              className="p-3 bg-primary-600 text-white rounded-full hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </form>
      </footer>
    </div>
  );
}
