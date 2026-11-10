import { NavLink, Outlet } from "react-router-dom";

function Layout() {
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
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;