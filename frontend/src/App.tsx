import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import Scoreboard from './Scoreboard';
import MorningProjection from './MorningProjection';
import WeeklyCalendar from './WeeklyCalendar';
import BackendStatus from './BackendStatus';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <BackendStatus />
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <Scoreboard />
        <MorningProjection />
        <ClientAdmin />
        <WeeklyCalendar />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
