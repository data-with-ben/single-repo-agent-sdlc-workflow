import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import WeeklyCalendar from './WeeklyCalendar';
import BackendStatus from './BackendStatus';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <BackendStatus />
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <ClientAdmin />
        <WeeklyCalendar />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
