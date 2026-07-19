import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@sv/ui/styles.css";
import "./styles.css";
import { DashboardApp } from "./app";
createRoot(document.getElementById("root")!).render(<StrictMode><DashboardApp /></StrictMode>);
