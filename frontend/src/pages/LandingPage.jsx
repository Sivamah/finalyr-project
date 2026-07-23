import { Link } from 'react-router-dom';
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export default function LandingPage() {
  const { user } = useContext(AuthContext);

  const getDashboardLink = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'Admin': return '/admin';
      case 'Driver': return '/driver';
      case 'Customer': return '/customer';
      default: return '/';
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center">
      <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-gray-900 mb-6">
        AI-Powered Unified Mobility <br className="hidden md:block"/>
        <span className="text-primary-600">and Delivery System</span>
      </h1>
      <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl mb-8">
        Experience seamless logistics and ride booking with our Dynamic Feasibility Analysis engine. Let's get moving!
      </p>
      
      <div className="flex space-x-4">
        {user ? (
          <Link to={getDashboardLink()} className="bg-primary-600 text-white hover:bg-primary-700 px-8 py-3 rounded-md text-lg font-medium shadow-sm transition-colors duration-200">
            Go to Dashboard
          </Link>
        ) : (
          <>
            <Link to="/register" className="bg-primary-600 text-white hover:bg-primary-700 px-8 py-3 rounded-md text-lg font-medium shadow-sm transition-colors duration-200">
              Get Started
            </Link>
            <Link to="/login" className="bg-white text-primary-600 hover:bg-gray-50 border border-primary-600 px-8 py-3 rounded-md text-lg font-medium shadow-sm transition-colors duration-200">
              Login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
