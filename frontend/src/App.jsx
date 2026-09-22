import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Studio from './pages/Studio';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/studio" element={<Studio />} />
    </Routes>
  );
}
