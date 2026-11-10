import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import OpeningEditorPage from "./pages/OpeningEditorPage";
import OpeningsPage from "./pages/OpeningsPage";
import PlaceholderPage from "./pages/PlaceholderPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/openings" element={<OpeningsPage />} />
        <Route path="/openings/:id/edit" element={<OpeningEditorPage />} />
        <Route
          path="/openings/:id/train"
          element={<PlaceholderPage title="Entrenar apertura" />}
        />
        <Route path="/training" element={<PlaceholderPage title="Entrenar" />} />
        <Route path="/stats" element={<PlaceholderPage title="Estadísticas" />} />
        <Route
          path="*"
          element={<PlaceholderPage title="Página no encontrada" />}
        />
      </Route>
    </Routes>
  );
}

export default App;