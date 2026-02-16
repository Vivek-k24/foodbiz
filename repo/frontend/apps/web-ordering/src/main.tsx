import React from "react";
import { createRoot } from "react-dom/client";

import { MenuPage } from "./pages/MenuPage";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <MenuPage />
  </React.StrictMode>
);
