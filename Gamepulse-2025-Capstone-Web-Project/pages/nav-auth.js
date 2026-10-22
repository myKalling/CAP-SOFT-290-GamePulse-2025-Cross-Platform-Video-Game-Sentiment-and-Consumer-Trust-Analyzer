import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { auth } from "./firebase-init.js";

onAuthStateChanged(auth, (user) => {
  const link = document.getElementById("auth-link");
  if (!link) return;

  const label = user ? user.displayName || "Account" : "Sign In";
  link.textContent = label;
  link.setAttribute("aria-label", user ? `Account: ${label}` : "Sign In");
});