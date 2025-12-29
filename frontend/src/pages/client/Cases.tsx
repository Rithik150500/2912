import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { clientApi } from '../../services/api';
import { ArrowLeft, Briefcase, Users, ChevronRight } from 'lucide-react';

interface Case {
  id: string;
  matter_type: string;
  sub_category: string;
  state: string;
  district: string;
  case_summary: string;
  status: string;
  advocate_response: string | null;
  created_at: string;
}

export default function ClientCases() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      const response = await clientApi.getCases();
      setCases(response.data);
    } catch (error) {
      console.error('Failed to load cases:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string, advocateResponse: string | null) => {
    if (status === 'advocate_assigned' || advocateResponse === 'accepted') {
      return (
        <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
          Advocate Assigned
        </span>
      );
    }
    if (status === 'pending_advocate') {
      return (
        <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium">
          Awaiting Advocate
        </span>
      );
    }
    if (status === 'advocate_rejected') {
      return (
        <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
          Select New Advocate
        </span>
      );
    }
    return (
      <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
        In Progress
      </span>
    );
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
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center">
          <button
            onClick={() => navigate('/client')}
            className="p-2 hover:bg-gray-100 rounded-full mr-4"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="text-xl font-semibold">My Cases</h1>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {cases.length === 0 ? (
          <div className="text-center py-12">
            <Briefcase className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">No cases yet</p>
            <button
              onClick={() => navigate('/client')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Start a consultation to create a case
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
                      <h3 className="text-lg font-semibold text-gray-900 capitalize">
                        {caseItem.matter_type || 'Legal'} Matter
                      </h3>
                      {getStatusBadge(caseItem.status, caseItem.advocate_response)}
                    </div>
                    {caseItem.sub_category && (
                      <p className="text-sm text-gray-600 mb-2">{caseItem.sub_category}</p>
                    )}
                    {caseItem.case_summary && (
                      <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                        {caseItem.case_summary}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      {caseItem.state && (
                        <span>
                          {caseItem.district}, {caseItem.state}
                        </span>
                      )}
                      <span>
                        Created {new Date(caseItem.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    {(caseItem.status === 'ai_conversation' ||
                      caseItem.status === 'advocate_rejected') && (
                      <button
                        onClick={() => navigate(`/client/cases/${caseItem.id}/select-advocate`)}
                        className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                      >
                        <Users className="h-4 w-4" />
                        <span>Find Advocate</span>
                      </button>
                    )}
                    <button
                      onClick={() => navigate(`/client/cases/${caseItem.id}`)}
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
