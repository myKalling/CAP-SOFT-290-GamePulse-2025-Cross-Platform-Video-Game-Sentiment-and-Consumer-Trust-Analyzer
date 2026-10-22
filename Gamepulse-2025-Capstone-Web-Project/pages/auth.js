import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { auth } from "./firebase-init.js";

const $ = (id) => document.getElementById(id);
let mode = "signup";

function showMessage(text, isError = true) {
  const el = $("message");
  el.textContent = text;
  el.className =
    "text-sm font-bold min-h-5 " + (isError ? "text-red-300" : "text-green-300");
}

function friendlyError(code) {
  const map = {
    "auth/email-already-in-use": "That email already has an account. Try logging in.",
    "auth/invalid-email": "That email address doesn't look right.",
    "auth/weak-password": "Password must be at least 6 characters.",
    "auth/invalid-credential": "Wrong email or password.",
    "auth/user-not-found": "Wrong email or password.",
    "auth/wrong-password": "Wrong email or password.",
    "auth/too-many-requests": "Too many tries. Wait a few minutes and try again.",
    "auth/network-request-failed": "Network problem. Check your connection.",
    "auth/operation-not-allowed": "Email/Password sign-in isn't enabled in Firebase yet.",
    "auth/unauthorized-domain": "This address isn't an authorized domain in Firebase.",
  };
  return map[code] || "Something went wrong. Please try again.";
}

function setMode(next) {
  mode = next;
  const signup = mode === "signup";
  $("tab-signup").setAttribute("aria-pressed", String(signup));
  $("tab-login").setAttribute("aria-pressed", String(!signup));
  $("name-row").classList.toggle("hidden", !signup);
  $("hint").classList.toggle("hidden", !signup);
  $("fname").required = signup;
  $("ps").autocomplete = signup ? "new-password" : "current-password";
  $("page-title").textContent = signup ? "Sign Up" : "Log In";
  $("submit-btn").textContent = signup ? "Create Account" : "Log In";
  showMessage("");
}

function render(user) {
  const signedIn = !!user;
  $("signed-in").classList.toggle("hidden", !signedIn);
  $("signed-out").classList.toggle("hidden", signedIn);
  if (signedIn) {
    $("who").textContent = user.displayName || user.email;
    $("page-title").textContent = "Your Account";
  } else {
    setMode(mode);
  }
}

$("tab-signup").addEventListener("click", () => setMode("signup"));
$("tab-login").addEventListener("click", () => setMode("login"));

$("accountForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("email").value.trim();
  const password = $("ps").value;
  const name = $("fname").value.trim();
  const btn = $("submit-btn");

  btn.disabled = true;
  showMessage("");

  try {
    if (mode === "signup") {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(cred.user, { displayName: name });
      render(cred.user); // refresh so the name shows right away
    } else {
      await signInWithEmailAndPassword(auth, email, password);
    }
    $("accountForm").reset();
  } catch (err) {
    console.error(err);
    showMessage(friendlyError(err.code));
  } finally {
    btn.disabled = false;
  }
});

$("logout-btn").addEventListener("click", () => signOut(auth));

onAuthStateChanged(auth, render);