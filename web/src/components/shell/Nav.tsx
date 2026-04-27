"use client";

import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

export default function Nav() {
  return (
    <nav className="nav">
      <div className="nav-l">
        <Logo />
      </div>
      <div className="nav-r">
        <span className="pill">v0.4 · BETA</span>
        <ThemeToggle />
        <button type="button" className="btn btn-primary btn-sm" disabled title="Sign-in coming soon">
          Sign in
        </button>
      </div>
    </nav>
  );
}
