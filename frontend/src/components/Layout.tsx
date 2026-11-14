import { NavLink, Outlet, useLocation } from "react-router-dom";

import { EvaluationJobsProvider } from "../contexts/EvaluationJobsContext";

function Layout() {
  const location = useLocation();
  const isTraining = /\/openings\/[^/]+\/train$/.test(location.pathname);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">CO</span>
          <div>
            <h1>Chess Openings</h1>
            <p>Entrenador de aperturas</p>
          </div>
        </div>
        <nav className="app-nav" aria-label="Navegación principal">
          <NavLink to="/" end>
            Inicio
          </NavLink>
          <NavLink to="/openings">Aperturas</NavLink>
          <NavLink to="/training">Entrenar</NavLink>
          <NavLink to="/stats">Estadísticas</NavLink>
        </nav>
      </header>
      <EvaluationJobsProvider>
        <main
          className={isTraining ? "app-main app-main--training" : "app-main"}
        >
          <Outlet />
        </main>
      </EvaluationJobsProvider>
    </div>
  );
}

export default Layout;