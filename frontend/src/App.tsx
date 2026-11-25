import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import ImportDashboard from './pages/ImportDashboard';
import ArticlesAdmin from './pages/ArticlesAdmin';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <Router basename="/admin">
      <div className="App">
        <Routes>
          <Route path="/import" element={<ProtectedRoute><ImportDashboard /></ProtectedRoute>} />
          <Route path="/articles" element={<ProtectedRoute><ArticlesAdmin /></ProtectedRoute>} />
          <Route path="/login" element={<AdminLogin />} />
          <Route 
            path="/"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            } 
          />
        </Routes>
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
          }}
        />
      </div>
    </Router>
  );
}

export default App;
