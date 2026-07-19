import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@sv/ui/styles.css";
import "./styles.css";
import { FounderPortal } from "./portal";

createRoot(document.getElementById("root")!).render(<StrictMode><FounderPortal /></StrictMode>);
