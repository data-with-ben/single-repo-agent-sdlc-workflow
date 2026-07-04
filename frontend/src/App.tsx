import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import WeeklyCalendar from './WeeklyCalendar';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <ClientAdmin />
        <WeeklyCalendar />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
