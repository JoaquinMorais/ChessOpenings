import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import OpeningEditorPage from "./pages/OpeningEditorPage";
import OpeningStatsPage from "./pages/OpeningStatsPage";
import OpeningsPage from "./pages/OpeningsPage";
import PlaceholderPage from "./pages/PlaceholderPage";
import StatsIndexPage from "./pages/StatsIndexPage";
import TrainingIndexPage from "./pages/TrainingIndexPage";
import TrainingPage from "./pages/TrainingPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/openings" element={<OpeningsPage />} />
        <Route path="/openings/:id/edit" element={<OpeningEditorPage />} />
        <Route path="/openings/:id/train" element={<TrainingPage />} />
        <Route path="/openings/:id/stats" element={<OpeningStatsPage />} />
        <Route path="/training" element={<TrainingIndexPage />} />
        <Route path="/stats" element={<StatsIndexPage />} />
        <Route
          path="*"
          element={<PlaceholderPage title="Página no encontrada" />}
        />
      </Route>
    </Routes>
  );
}

export default App;