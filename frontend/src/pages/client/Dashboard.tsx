import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { clientApi } from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  MessageSquare,
  Briefcase,
  Bell,
  LogOut,
  Plus,
  ChevronRight,
  Scale,
} from 'lucide-react';

interface Conversation {
  id: string;
  phase: string;
  created_at: string;
  last_message?: {
    content: string;
    created_at: string;
  };
}

export default function ClientDashboard() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await clientApi.getConversations();
      setConversations(response.data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const startNewConversation = async () => {
    try {
      const response = await clientApi.createConversation();
      navigate(`/client/conversation/${response.data.id}`);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-primary-600" />
              <h1 className="text-xl font-semibold text-gray-900">AI Advocate Platform</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {user?.full_name}</span>
              <button
                onClick={() => navigate('/client/cases')}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="My Cases"
              >
                <Briefcase className="h-5 w-5" />
              </button>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="Logout"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <button
            onClick={startNewConversation}
            className="flex items-center justify-between p-6 bg-primary-600 text-white rounded-lg shadow-sm hover:bg-primary-700 transition-colors"
          >
            <div>
              <h3 className="text-lg font-semibold">Start New Consultation</h3>
              <p className="text-primary-100 text-sm mt-1">
                Chat with our AI legal assistant
              </p>
            </div>
            <Plus className="h-8 w-8" />
          </button>

          <button
            onClick={() => navigate('/client/cases')}
            className="flex items-center justify-between p-6 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow"
          >
            <div>
              <h3 className="text-lg font-semibold text-gray-900">My Cases</h3>
              <p className="text-gray-500 text-sm mt-1">
                View and manage your cases
              </p>
            </div>
            <Briefcase className="h-8 w-8 text-gray-400" />
          </button>

          <div className="flex items-center justify-between p-6 bg-white rounded-lg shadow-sm">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Notifications</h3>
              <p className="text-gray-500 text-sm mt-1">
                Stay updated on your cases
              </p>
            </div>
            <Bell className="h-8 w-8 text-gray-400" />
          </div>
        </div>

        {/* Conversations list */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Conversations</h2>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No conversations yet</p>
              <button
                onClick={startNewConversation}
                className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
              >
                Start your first consultation
              </button>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {conversations.map((conv) => (
                <li key={conv.id}>
                  <button
                    onClick={() => navigate(`/client/conversation/${conv.id}`)}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                  >
                    <div className="flex items-center space-x-4">
                      <MessageSquare className="h-10 w-10 text-primary-600 bg-primary-50 rounded-full p-2" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-gray-900">
                          Legal Consultation
                        </p>
                        <p className="text-sm text-gray-500 truncate max-w-md">
                          {conv.last_message?.content || 'No messages yet'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-xs text-gray-400">
                        {new Date(conv.created_at).toLocaleDateString()}
                      </span>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          conv.phase === 'advocate_active'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {conv.phase === 'advocate_active' ? 'With Advocate' : 'AI Chat'}
                      </span>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
