import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import Scoreboard from './Scoreboard';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <Scoreboard />
        <ClientAdmin />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
