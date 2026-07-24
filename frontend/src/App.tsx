import { Routes, Route, Link, useNavigate } from 'react-router-dom';
import { DownloadPage } from './pages/DownloadPage';
import { FilesPage } from './pages/FilesPage';
import './App.css';

function NavBar() {
  const navigate = useNavigate();
  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-brand">File Extractor</Link>
        <ul className="nav-links">
          <li>
            <button onClick={() => navigate('/')}>Скачать данные</button>
          </li>
          <li>
            <button onClick={() => navigate('/files')}>Файлы и расчёты</button>
          </li>
        </ul>
      </div>
    </nav>
  );
}

export function App() {
  return (
    <div className="app">
      <NavBar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<DownloadPage />} />
          <Route path="/files" element={<FilesPage />} />
        </Routes>
      </main>
    </div>
  );
}
