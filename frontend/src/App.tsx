import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MainLayout from './components/layout/MainLayout';

// Initialize the TanStack Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // Prevents unnecessary refetches when swapping tabs
      staleTime: 1000 * 60 * 5,    // Cache data for 5 minutes before background refetching
    },
  },
});

const Dashboard = lazy(() => import('./pages/Dashboard/Dashboard'));
const TradeHistory = lazy(() => import('./pages/TradeHistory/TradeHistory'));

const PageLoader = () => (
  <div style={{ padding: '2rem', color: '#38bdf8' }}>
    Loading workspace view...
  </div>
);

const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<PageLoader />}>
            <Dashboard />
          </Suspense>
        ),
      },
      {
        path: 'trades',
        element: (
          <Suspense fallback={<PageLoader />}>
            <TradeHistory />
          </Suspense>
        ),
      },
    ],
  },
]);

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}