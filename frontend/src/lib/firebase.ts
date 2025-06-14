import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyACk-PzmUAFRNtU15q5IW06sExoVT29ijA",
  authDomain: "aimockinterview-1f749.firebaseapp.com",
  projectId: "aimockinterview-1f749",
  storageBucket: "aimockinterview-1f749.appspot.com",
  messagingSenderId: "628518489025",
  appId: "1:628518489025:web:YOUR_APP_ID", // Replace with actual App ID shown in Firebase
  // measurementId: "G-XXXXXXXXXX" // Optional: if using Google Analytics
};


const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider(); 