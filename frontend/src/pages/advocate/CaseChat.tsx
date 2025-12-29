import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { ArrowLeft, Send, User, Bot, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  sender_type: 'client' | 'ai' | 'advocate';
  sender_name: string;
  content: string;
  message_type: string;
  created_at: string;
}

interface CaseDetail {
  id: string;
  client_id: string;
  client_name: string;
  client_email: string;
  client_phone: string;
  conversation_id: string;
  matter_type: string;
  sub_category: string;
  state: string;
  district: string;
  case_summary: string;
}

export default function CaseChat() {
  const { id: caseId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadCase();
  }, [caseId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadCase = async () => {
    if (!caseId) return;
    try {
      const response = await advocateApi.getCase(caseId);
      setCaseDetail(response.data.case);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load case:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || sending || !caseId) return;

    const content = newMessage;
    setNewMessage('');
    setSending(true);

    // Optimistically add message
    const tempMessage: Message = {
      id: 'temp-' + Date.now(),
      sender_type: 'advocate',
      sender_name: 'You',
      content,
      message_type: 'text',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMessage]);

    try {
      const response = await advocateApi.sendMessage(caseId, content);
      // Replace temp message with real one
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempMessage.id),
        {
          ...response.data,
          sender_type: 'advocate' as const,
          sender_name: 'You',
          message_type: 'text',
        },
      ]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempMessage.id));
    } finally {
      setSending(false);
    }
  };

  const getSenderIcon = (senderType: string) => {
    switch (senderType) {
      case 'client':
        return <User className="h-5 w-5" />;
      case 'ai':
        return <Bot className="h-5 w-5" />;
      case 'advocate':
        return <User className="h-5 w-5" />;
      default:
        return <User className="h-5 w-5" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!caseDetail) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Case not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-sm flex-shrink-0">
          <div className="px-4 py-4 flex items-center justify-between">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/advocate/cases')}
                className="p-2 hover:bg-gray-100 rounded-full mr-4"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div>
                <h1 className="text-lg font-semibold">{caseDetail.client_name}</h1>
                <p className="text-sm text-gray-500 capitalize">
                  {caseDetail.matter_type} Matter
                </p>
              </div>
            </div>
          </div>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender_type === 'advocate' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] flex ${
                  msg.sender_type === 'advocate' ? 'flex-row-reverse' : 'flex-row'
                }`}
              >
                <div
                  className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                    msg.sender_type === 'advocate'
                      ? 'bg-primary-100 text-primary-600 ml-2'
                      : msg.sender_type === 'client'
                      ? 'bg-blue-100 text-blue-600 mr-2'
                      : 'bg-gray-100 text-gray-600 mr-2'
                  }`}
                >
                  {getSenderIcon(msg.sender_type)}
                </div>
                <div>
                  <p
                    className={`text-xs mb-1 ${
                      msg.sender_type === 'advocate' ? 'text-right' : 'text-left'
                    } text-gray-500`}
                  >
                    {msg.sender_name}
                  </p>
                  <div
                    className={`rounded-lg px-4 py-2 ${
                      msg.sender_type === 'advocate'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white shadow-sm'
                    }`}
                  >
                    {msg.sender_type === 'advocate' ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                  <p
                    className={`text-xs mt-1 ${
                      msg.sender_type === 'advocate' ? 'text-right' : 'text-left'
                    } text-gray-400`}
                  >
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </main>

        {/* Input */}
        <footer className="bg-white border-t flex-shrink-0">
          <form onSubmit={sendMessage} className="p-4">
            <div className="flex items-center space-x-4">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Type your message..."
                disabled={sending}
                className="flex-1 rounded-full border border-gray-300 px-6 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="submit"
                disabled={!newMessage.trim() || sending}
                className="p-3 bg-primary-600 text-white rounded-full hover:bg-primary-700 disabled:opacity-50"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </form>
        </footer>
      </div>

      {/* Case details sidebar */}
      <aside className="hidden lg:block w-80 bg-white border-l overflow-y-auto">
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">Case Details</h2>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500">Client</p>
              <p className="font-medium">{caseDetail.client_name}</p>
              {caseDetail.client_email && (
                <p className="text-sm text-gray-600">{caseDetail.client_email}</p>
              )}
              {caseDetail.client_phone && (
                <p className="text-sm text-gray-600">{caseDetail.client_phone}</p>
              )}
            </div>

            <div>
              <p className="text-sm text-gray-500">Matter Type</p>
              <p className="font-medium capitalize">{caseDetail.matter_type}</p>
            </div>

            {caseDetail.sub_category && (
              <div>
                <p className="text-sm text-gray-500">Sub Category</p>
                <p className="font-medium">{caseDetail.sub_category}</p>
              </div>
            )}

            <div>
              <p className="text-sm text-gray-500">Location</p>
              <p className="font-medium">
                {caseDetail.district}, {caseDetail.state}
              </p>
            </div>

            {caseDetail.case_summary && (
              <div>
                <p className="text-sm text-gray-500">Case Summary</p>
                <p className="text-sm text-gray-700">{caseDetail.case_summary}</p>
              </div>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
