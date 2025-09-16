import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { authApi } from '../services/api';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const [status, setStatus] = useState<'checking' | 'authorized' | 'unauthorized'>(
    'checking'
  );

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setStatus('unauthorized');
      return;
    }
    authApi
      .me()
      .then(() => setStatus('authorized'))
      .catch(() => {
        localStorage.removeItem('access_token');
        setStatus('unauthorized');
      });
  }, []);

  if (status === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-gray-800"></div>
      </div>
    );
  }

  if (status === 'unauthorized') {
    return <Navigate to="/admin/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
