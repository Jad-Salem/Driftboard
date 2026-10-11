import { AuthPage } from "./components/AuthPage";
import { BoardPage } from "./components/BoardPage";
import { BoardsPage } from "./components/BoardsPage";
import { useAuth } from "./store/auth";
import { useBoard } from "./store/board";

export default function App() {
  const token = useAuth((s) => s.token);
  const currentId = useBoard((s) => s.currentId);
  const error = useBoard((s) => s.error);

  if (!token) return <AuthPage />;
  return (
    <>
      {error && <div className="toast">{error}</div>}
      {currentId === null ? <BoardsPage /> : <BoardPage />}
    </>
  );
}
