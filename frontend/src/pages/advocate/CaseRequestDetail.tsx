import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { ArrowLeft, Check, X, User, Bot, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  sender_type: 'client' | 'ai' | 'advocate';
  sender_name: string;
  content: string;
  created_at: string;
}

interface CaseRequestDetail {
  id: string;
  case_id: string;
  match_score: number;
  match_explanation: string;
  status: string;
  created_at: string;
  client_name: string;
  case: {
    matter_type: string;
    sub_category: string;
    state: string;
    district: string;
    court_level: string;
    complexity: string;
    case_summary: string;
  };
  conversation_messages: Message[];
}

export default function CaseRequestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [request, setRequest] = useState<CaseRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<'accept' | 'reject' | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  useEffect(() => {
    loadRequest();
  }, [id]);

  const loadRequest = async () => {
    if (!id) return;
    try {
      const response = await advocateApi.getCaseRequest(id);
      setRequest(response.data);
    } catch (error) {
      console.error('Failed to load request:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!id) return;
    setProcessing('accept');
    try {
      await advocateApi.acceptCaseRequest(id);
      navigate('/advocate/cases', {
        state: { message: 'Case accepted successfully!' },
      });
    } catch (error) {
      console.error('Failed to accept:', error);
      setProcessing(null);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    setProcessing('reject');
    try {
      await advocateApi.rejectCaseRequest(id, rejectReason || undefined);
      navigate('/advocate/requests', {
        state: { message: 'Case request declined.' },
      });
    } catch (error) {
      console.error('Failed to reject:', error);
      setProcessing(null);
    }
  };

  const getSenderIcon = (senderType: string) => {
    switch (senderType) {
      case 'client':
        return <User className="h-5 w-5" />;
      case 'ai':
        return <Bot className="h-5 w-5" />;
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

  if (!request) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Request not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={() => navigate('/advocate/requests')}
              className="p-2 hover:bg-gray-100 rounded-full mr-4"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-xl font-semibold">{request.client_name}'s Case</h1>
              <p className="text-sm text-gray-500">
                {request.match_score}% match score
              </p>
            </div>
          </div>

          {request.status === 'pending' && (
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowRejectModal(true)}
                disabled={processing !== null}
                className="flex items-center space-x-2 px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
              >
                <X className="h-4 w-4" />
                <span>Decline</span>
              </button>
              <button
                onClick={handleAccept}
                disabled={processing !== null}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                <span>{processing === 'accept' ? 'Accepting...' : 'Accept Case'}</span>
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Case details sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm p-6 sticky top-24">
              <h2 className="text-lg font-semibold mb-4">Case Details</h2>

              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Matter Type</p>
                  <p className="font-medium capitalize">{request.case?.matter_type || 'N/A'}</p>
                </div>
                {request.case?.sub_category && (
                  <div>
                    <p className="text-sm text-gray-500">Sub Category</p>
                    <p className="font-medium">{request.case.sub_category}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-gray-500">Location</p>
                  <p className="font-medium">
                    {request.case?.district}, {request.case?.state}
                  </p>
                </div>
                {request.case?.court_level && (
                  <div>
                    <p className="text-sm text-gray-500">Court Level</p>
                    <p className="font-medium capitalize">{request.case.court_level}</p>
                  </div>
                )}
                {request.case?.complexity && (
                  <div>
                    <p className="text-sm text-gray-500">Complexity</p>
                    <p className="font-medium capitalize">{request.case.complexity}</p>
                  </div>
                )}
              </div>

              {request.match_explanation && (
                <div className="mt-6 pt-6 border-t">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Why You're a Match</h3>
                  <div className="space-y-1">
                    {request.match_explanation.split(';').map((reason, idx) => (
                      <p key={idx} className="text-sm text-green-600 flex items-center">
                        <Check className="h-3 w-3 mr-2" />
                        {reason.trim()}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {request.case?.case_summary && (
                <div className="mt-6 pt-6 border-t">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Case Summary</h3>
                  <p className="text-sm text-gray-600">{request.case.case_summary}</p>
                </div>
              )}
            </div>
          </div>

          {/* Conversation history */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-sm">
              <div className="px-6 py-4 border-b flex items-center">
                <MessageSquare className="h-5 w-5 text-primary-600 mr-2" />
                <h2 className="text-lg font-semibold">Client Conversation History</h2>
              </div>

              <div className="p-6 max-h-[600px] overflow-y-auto space-y-4">
                {request.conversation_messages.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">
                    No conversation history available
                  </p>
                ) : (
                  request.conversation_messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${
                        msg.sender_type === 'client' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[80%] flex ${
                          msg.sender_type === 'client' ? 'flex-row-reverse' : 'flex-row'
                        }`}
                      >
                        <div
                          className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                            msg.sender_type === 'client'
                              ? 'bg-blue-100 text-blue-600 ml-2'
                              : 'bg-gray-100 text-gray-600 mr-2'
                          }`}
                        >
                          {getSenderIcon(msg.sender_type)}
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 mb-1">
                            {msg.sender_name}
                          </p>
                          <div
                            className={`rounded-lg px-4 py-2 ${
                              msg.sender_type === 'client'
                                ? 'bg-blue-50 text-gray-800'
                                : 'bg-gray-50 text-gray-800'
                            }`}
                          >
                            {msg.sender_type === 'client' ? (
                              <p className="text-sm">{msg.content}</p>
                            ) : (
                              <div className="prose prose-sm max-w-none">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                              </div>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(msg.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Decline Case Request</h3>
            <p className="text-gray-600 mb-4">
              Please provide a reason for declining (optional):
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Currently at full capacity, Not my area of expertise..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 mb-4"
              rows={3}
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={processing === 'reject'}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {processing === 'reject' ? 'Declining...' : 'Confirm Decline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
