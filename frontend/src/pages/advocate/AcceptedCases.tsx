import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { ArrowLeft, Briefcase, MessageSquare, ChevronRight } from 'lucide-react';

interface AcceptedCase {
  id: string;
  client_id: string;
  client_name: string;
  conversation_id: string;
  matter_type: string;
  sub_category: string;
  state: string;
  district: string;
  case_summary: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function AcceptedCases() {
  const [cases, setCases] = useState<AcceptedCase[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      const response = await advocateApi.getCases();
      setCases(response.data.cases || []);
    } catch (error) {
      console.error('Failed to load cases:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

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
          <h1 className="text-xl font-semibold">My Cases</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {cases.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <Briefcase className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">No accepted cases yet</p>
            <button
              onClick={() => navigate('/advocate/requests')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              View pending requests
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {cases.map((caseItem) => (
              <div
                key={caseItem.id}
                className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {caseItem.client_name}
                      </h3>
                      <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium capitalize">
                        {caseItem.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 capitalize mb-2">
                      {caseItem.matter_type} Matter - {caseItem.district}, {caseItem.state}
                    </p>
                    {caseItem.case_summary && (
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {caseItem.case_summary}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">
                      Accepted on {new Date(caseItem.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => navigate(`/advocate/cases/${caseItem.id}`)}
                      className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      <MessageSquare className="h-4 w-4" />
                      <span>Chat</span>
                    </button>
                    <button
                      onClick={() => navigate(`/advocate/cases/${caseItem.id}`)}
                      className="p-2 hover:bg-gray-100 rounded-full"
                    >
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </button>
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
