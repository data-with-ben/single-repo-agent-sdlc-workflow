import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <ClientAdmin />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
