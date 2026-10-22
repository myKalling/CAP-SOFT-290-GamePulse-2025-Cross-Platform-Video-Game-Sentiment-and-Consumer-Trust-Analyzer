import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyDq2ldjrnxajjQDTgqxRGoum-5rq8F4_M8",
  authDomain: "capstone-web-project-d955f.firebaseapp.com",
  projectId: "capstone-web-project-d955f",
  storageBucket: "capstone-web-project-d955f.firebasestorage.app",
  messagingSenderId: "72929103984",
  appId: "1:72929103984:web:bf3d5453ef6dcaf00564b5",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);