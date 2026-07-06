import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import BackendStatus from './BackendStatus';
import Scoreboard from './Scoreboard';
import Portfolio from './Portfolio';
import Brackets from './Brackets';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <BackendStatus />
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <Scoreboard />
        <Portfolio />
        <Brackets />
        <ClientAdmin />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
