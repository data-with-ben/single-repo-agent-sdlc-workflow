import { CurrentUserProvider } from './currentUser';
import UserSwitcher from './UserSwitcher';

function App() {
  return (
    <CurrentUserProvider>
      <main>
        <UserSwitcher />
        <h1>Hello, Fantasy Timesheets</h1>
      </main>
    </CurrentUserProvider>
  );
}

export default App;
