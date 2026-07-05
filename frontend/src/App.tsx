import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';
import ClientAdmin from './ClientAdmin';
import MorningProjection from './MorningProjection';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
        <MorningProjection />
        <ClientAdmin />
      </main>
    </CurrentUserProvider>
  );
}

export default App;
