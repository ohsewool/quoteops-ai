import { useEffect, useState } from "react";

import { useAuth } from "../auth/AuthProvider.jsx";
import { navigationFor, roleLabel } from "../navigation.js";
import { currentPath, navigate, useLocation } from "../router.jsx";

const demoEnabled = import.meta.env.VITE_DEMO_ENABLED === "true";

export default function WorkspaceLayout({ children }) {
  const { logout, user } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = navigationFor(user.role, { demoEnabled });

  useEffect(() => {
    setMenuOpen(false);
    window.requestAnimationFrame(() => document.querySelector("[data-route-heading]")?.focus());
  }, [location]);

  const goTo = (event, href) => {
    event.preventDefault();
    if (href !== currentPath()) navigate(href);
  };

  return (
    <div className="workspace-shell">
      <a className="skip-link" href="#workspace-main">본문으로 건너뛰기</a>
      <header className="workspace-header">
        <button className="brand" onClick={() => navigate("/app/dashboard")} type="button">QuoteOps AI</button>
        <div className="workspace-account">
          <span>{user.display_name} · {roleLabel(user.role)}</span>
          <button className="icon-button" aria-expanded={menuOpen} aria-label="메뉴 열기" onClick={() => setMenuOpen((open) => !open)} type="button">≡</button>
          <button className="button button-secondary workspace-logout" onClick={() => { logout(); navigate("/"); }} type="button">로그아웃</button>
        </div>
      </header>
      <aside className={`workspace-nav ${menuOpen ? "workspace-nav-open" : ""}`}>
        <nav aria-label="업무 공간 탐색">
          {items.map((item) => (
            <a aria-current={location.split("?")[0] === item.href ? "page" : undefined} href={item.href} key={item.href} onClick={(event) => goTo(event, item.href)}>
              <span>{item.label}</span>
              {item.phase ? <small>{item.phase}</small> : null}
            </a>
          ))}
        </nav>
      </aside>
      <main className="workspace-main" id="workspace-main">{children}</main>
    </div>
  );
}
