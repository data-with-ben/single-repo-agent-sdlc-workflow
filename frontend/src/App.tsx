import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import BackendStatus from './BackendStatus';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <BackendStatus />
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <ClientAdmin />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
