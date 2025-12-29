import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { ArrowLeft, Inbox, ChevronRight } from 'lucide-react';

interface CaseRequest {
  id: string;
  case_id: string;
  match_score: number;
  status: string;
  created_at: string;
  client_name: string;
  case: {
    matter_type: string;
    state: string;
    district: string;
    case_summary: string;
  };
}

export default function CaseRequests() {
  const [requests, setRequests] = useState<CaseRequest[]>([]);
  const [filter, setFilter] = useState<'pending' | 'accepted' | 'rejected' | 'all'>('pending');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadRequests();
  }, [filter]);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const response = await advocateApi.getCaseRequests(filter === 'all' ? undefined : filter);
      setRequests(response.data);
    } catch (error) {
      console.error('Failed to load requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs">Pending</span>;
      case 'accepted':
        return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">Accepted</span>;
      case 'rejected':
        return <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">Rejected</span>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center">
          <button
            onClick={() => navigate('/advocate')}
            className="p-2 hover:bg-gray-100 rounded-full mr-4"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="text-xl font-semibold">Case Requests</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Filter tabs */}
        <div className="flex space-x-2 mb-6">
          {(['pending', 'accepted', 'rejected', 'all'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${
                filter === f
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          </div>
        ) : requests.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <Inbox className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No {filter !== 'all' ? filter : ''} requests</p>
          </div>
        ) : (
          <div className="space-y-4">
            {requests.map((request) => (
              <div
                key={request.id}
                className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/advocate/requests/${request.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {request.client_name}
                      </h3>
                      {getStatusBadge(request.status)}
                      <span className="px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-xs font-medium">
                        {request.match_score}% match
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 capitalize mb-2">
                      {request.case?.matter_type} Matter - {request.case?.district},{' '}
                      {request.case?.state}
                    </p>
                    {request.case?.case_summary && (
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {request.case.case_summary}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center space-x-4 ml-4">
                    <span className="text-sm text-gray-400">
                      {new Date(request.created_at).toLocaleDateString()}
                    </span>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
