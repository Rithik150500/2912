import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuthStore } from './store/authStore';

// Auth pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';

// Client pages
import ClientDashboard from './pages/client/Dashboard';
import ClientConversation from './pages/client/Conversation';
import ClientCases from './pages/client/Cases';
import SelectAdvocate from './pages/client/SelectAdvocate';

// Advocate pages
import AdvocateDashboard from './pages/advocate/Dashboard';
import AdvocateProfile from './pages/advocate/Profile';
import CaseRequests from './pages/advocate/CaseRequests';
import CaseRequestDetail from './pages/advocate/CaseRequestDetail';
import AcceptedCases from './pages/advocate/AcceptedCases';
import CaseChat from './pages/advocate/CaseChat';

// Protected route component
function ProtectedRoute({
  children,
  allowedRole,
}: {
  children: React.ReactNode;
  allowedRole?: 'client' | 'advocate';
}) {
  const { isAuthenticated, user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRole && user?.role !== allowedRole) {
    return <Navigate to={user?.role === 'client' ? '/client' : '/advocate'} replace />;
  }

  return <>{children}</>;
}

function App() {
  const { loadUser, isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Client routes */}
      <Route
        path="/client"
        element={
          <ProtectedRoute allowedRole="client">
            <ClientDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/client/conversation/:id"
        element={
          <ProtectedRoute allowedRole="client">
            <ClientConversation />
          </ProtectedRoute>
        }
      />
      <Route
        path="/client/cases"
        element={
          <ProtectedRoute allowedRole="client">
            <ClientCases />
          </ProtectedRoute>
        }
      />
      <Route
        path="/client/cases/:id/select-advocate"
        element={
          <ProtectedRoute allowedRole="client">
            <SelectAdvocate />
          </ProtectedRoute>
        }
      />

      {/* Advocate routes */}
      <Route
        path="/advocate"
        element={
          <ProtectedRoute allowedRole="advocate">
            <AdvocateDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/advocate/profile"
        element={
          <ProtectedRoute allowedRole="advocate">
            <AdvocateProfile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/advocate/requests"
        element={
          <ProtectedRoute allowedRole="advocate">
            <CaseRequests />
          </ProtectedRoute>
        }
      />
      <Route
        path="/advocate/requests/:id"
        element={
          <ProtectedRoute allowedRole="advocate">
            <CaseRequestDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/advocate/cases"
        element={
          <ProtectedRoute allowedRole="advocate">
            <AcceptedCases />
          </ProtectedRoute>
        }
      />
      <Route
        path="/advocate/cases/:id"
        element={
          <ProtectedRoute allowedRole="advocate">
            <CaseChat />
          </ProtectedRoute>
        }
      />

      {/* Default redirect */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to={user?.role === 'client' ? '/client' : '/advocate'} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
