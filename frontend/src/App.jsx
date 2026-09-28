import { Link, NavLink, Route, Routes } from "react-router-dom";
import InstallPrompt from "./components/InstallPrompt";
import About from "./pages/About";
import AddArea from "./pages/AddArea";
import AreaPage from "./pages/AreaPage";
import Home from "./pages/Home";

function Nav() {
  const link = ({ isActive }) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition ${isActive ? "bg-night-700 text-white" : "text-slate-400 hover:text-white"}`;
  return (
    <header className="sticky top-0 z-20 border-b border-night-700/70 bg-night-900/90 backdrop-blur">
      <div className="mx-auto flex max-w-2xl items-center gap-2 px-4 py-3">
        <Link to="/" className="mr-auto flex items-center gap-2 font-bold text-white">
          <img src="/icons/icon-192.png" alt="" className="h-8 w-8 rounded-lg" />
          <span>
            Light<span className="text-glow-400">Dey</span>
          </span>
        </Link>
        <NavLink to="/" end className={link}>
          Home
        </NavLink>
        <NavLink to="/about" className={link}>
          About
        </NavLink>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Nav />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pb-16 pt-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/a/:slug" element={<AreaPage />} />
          <Route path="/add" element={<AddArea />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <InstallPrompt />
      <footer className="border-t border-night-700/70 px-4 py-6 text-center text-xs text-slate-500">
        LightDey · reports come from people like you, not from DisCos ·{" "}
        <Link to="/about" className="underline hover:text-slate-300">
          How it works
        </Link>
      </footer>
    </div>
  );
}
