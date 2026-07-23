import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center">
      <h1 className="text-9xl font-bold text-gray-200">404</h1>
      <h2 className="text-3xl font-semibold text-gray-900 mt-4">Page not found</h2>
      <p className="text-gray-500 mt-2 mb-8">Sorry, we couldn't find the page you're looking for.</p>
      <Link to="/" className="text-primary-600 hover:text-primary-500 font-medium underline">
        Go back home
      </Link>
    </div>
  );
}
