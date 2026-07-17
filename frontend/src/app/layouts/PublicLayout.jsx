import { navigate, useLocation } from "../router.jsx";

export default function PublicLayout({ children }) {
  const location = useLocation();
  const isLoginPage = location.split("?")[0] === "/login";

  return (
    <div className="public-page">
      <header className="public-header">
        <button className="brand" type="button" onClick={() => navigate("/")}>QuoteOps AI</button>
        <button className="button button-secondary" type="button" onClick={() => navigate(isLoginPage ? "/" : "/login")}>
          {isLoginPage ? "홈으로" : "로그인"}
        </button>
      </header>
      {children}
      <footer className="public-footer">QuoteOps AI V2</footer>
    </div>
  );
}
