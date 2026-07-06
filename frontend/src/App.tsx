import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import Scoreboard from './Scoreboard';
import MorningProjection from './MorningProjection';
import WeeklyCalendar from './WeeklyCalendar';
import BackendStatus from './BackendStatus';
import Portfolio from './Portfolio';
import Brackets from './Brackets';

function App() {
  return (
    <CurrentUserProvider>
      <main className="app-shell">
        <BackendStatus />
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <Scoreboard />
        <Portfolio />
        <Brackets />
        <MorningProjection />
        <ClientAdmin />
        <WeeklyCalendar />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
