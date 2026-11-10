import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import PlaceholderPage from "./pages/PlaceholderPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/openings" element={<PlaceholderPage title="Aperturas" />} />
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