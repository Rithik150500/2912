import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { advocateApi } from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import {
  Scale,
  User,
  Inbox,
  Briefcase,
  Bell,
  LogOut,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';

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
  };
}

export default function AdvocateDashboard() {
  const [pendingRequests, setPendingRequests] = useState<CaseRequest[]>([]);
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    checkProfileAndLoadData();
  }, []);

  const checkProfileAndLoadData = async () => {
    try {
      // Check if profile exists
      await advocateApi.getProfile();
      setHasProfile(true);

      // Load pending requests
      const response = await advocateApi.getCaseRequests('pending');
      setPendingRequests(response.data);
    } catch (error: unknown) {
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 404) {
        setHasProfile(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-primary-600" />
              <h1 className="text-xl font-semibold text-gray-900">Advocate Portal</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">{user?.full_name}</span>
              <button
                onClick={() => navigate('/advocate/profile')}
                className="p-2 text-gray-500 hover:text-gray-700"
                title="My Profile"
              >
                <User className="h-5 w-5" />
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
        {/* Profile setup warning */}
        {hasProfile === false && (
          <div className="mb-8 p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start">
              <AlertCircle className="h-6 w-6 text-yellow-600 mr-3 flex-shrink-0" />
              <div>
                <h3 className="text-lg font-medium text-yellow-800">
                  Complete Your Profile
                </h3>
                <p className="mt-1 text-sm text-yellow-700">
                  Your profile is incomplete. Complete your profile to start receiving case
                  requests from clients.
                </p>
                <button
                  onClick={() => navigate('/advocate/profile')}
                  className="mt-3 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
                >
                  Complete Profile
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <button
            onClick={() => navigate('/advocate/requests')}
            className="flex items-center justify-between p-6 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow"
          >
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Case Requests</h3>
              <p className="text-gray-500 text-sm mt-1">
                {pendingRequests.length} pending request(s)
              </p>
            </div>
            <div className="relative">
              <Inbox className="h-8 w-8 text-primary-600" />
              {pendingRequests.length > 0 && (
                <span className="absolute -top-2 -right-2 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {pendingRequests.length}
                </span>
              )}
            </div>
          </button>

          <button
            onClick={() => navigate('/advocate/cases')}
            className="flex items-center justify-between p-6 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow"
          >
            <div>
              <h3 className="text-lg font-semibold text-gray-900">My Cases</h3>
              <p className="text-gray-500 text-sm mt-1">View accepted cases</p>
            </div>
            <Briefcase className="h-8 w-8 text-gray-400" />
          </button>

          <button
            onClick={() => navigate('/advocate/profile')}
            className="flex items-center justify-between p-6 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow"
          >
            <div>
              <h3 className="text-lg font-semibold text-gray-900">My Profile</h3>
              <p className="text-gray-500 text-sm mt-1">Manage your profile</p>
            </div>
            <User className="h-8 w-8 text-gray-400" />
          </button>
        </div>

        {/* Pending requests */}
        {pendingRequests.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Pending Case Requests</h2>
              <button
                onClick={() => navigate('/advocate/requests')}
                className="text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                View All
              </button>
            </div>
            <ul className="divide-y divide-gray-200">
              {pendingRequests.slice(0, 5).map((request) => (
                <li key={request.id}>
                  <button
                    onClick={() => navigate(`/advocate/requests/${request.id}`)}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
                  >
                    <div className="text-left">
                      <p className="font-medium text-gray-900">{request.client_name}</p>
                      <p className="text-sm text-gray-500 capitalize">
                        {request.case?.matter_type} - {request.case?.district},{' '}
                        {request.case?.state}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                        {request.match_score}% match
                      </span>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}
