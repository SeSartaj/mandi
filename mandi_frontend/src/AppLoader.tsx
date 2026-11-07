import { lazy, Suspense } from "react";
const App = lazy(() => import("./App"));
export default function AppLoader() {
  return (
    <Suspense fallback={<div className="empty">Loading Mandi…</div>}>
      <App />
    </Suspense>
  );
}
